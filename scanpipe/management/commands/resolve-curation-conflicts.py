# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scanpipe.models import Project
from scanpipe.models_curation import CurationConflict


class Command(BaseCommand):
    help = "Resolve curation conflicts using an automated strategy."
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--project",
            required=True,
            help="Project name or UUID with conflicts to resolve.",
        )
        parser.add_argument(
            "--strategy",
            choices=[
                "keep_existing",
                "use_imported",
                "highest_confidence",
                "highest_priority",
            ],
            required=True,
            help=(
                "Strategy for resolving conflicts:\n"
                "  keep_existing: Keep existing curations\n"
                "  use_imported: Use imported curations\n"
                "  highest_confidence: Use curation with higher confidence\n"
                "  highest_priority: Use source with higher priority"
            ),
        )
        parser.add_argument(
            "--conflict-type",
            help=(
                "Only resolve conflicts of this type. Options: "
                "origin_type_mismatch, origin_identifier_mismatch, "
                "confidence_difference, multiple_sources, manual_vs_automated"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be resolved without making changes.",
        )
    
    def handle(self, *args, **options):
        project_identifier = options["project"]
        strategy = options["strategy"]
        conflict_type = options["conflict_type"]
        dry_run = options["dry_run"]
        
        # Get project
        try:
            project = Project.objects.get_queryset(self.user).get_project(project_identifier)
        except Project.DoesNotExist:
            raise CommandError(f"Project not found: {project_identifier}")
        
        # Get pending conflicts
        conflicts_qs = CurationConflict.objects.filter(
            project=project,
            resolution_status="pending",
        )
        
        if conflict_type:
            conflicts_qs = conflicts_qs.filter(conflict_type=conflict_type)
        
        conflicts = list(conflicts_qs)
        
        if not conflicts:
            filter_msg = f" of type '{conflict_type}'" if conflict_type else ""
            self.stdout.write(
                self.style.SUCCESS(f"No pending conflicts{filter_msg} found")
            )
            return
        
        self.stdout.write(f"Found {len(conflicts)} pending conflicts")
        self.stdout.write(f"Resolution strategy: {strategy}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        # Resolve conflicts
        resolved = 0
        failed = 0
        
        with transaction.atomic():
            for conflict in conflicts:
                try:
                    result = self._resolve_conflict(conflict, strategy, dry_run)
                    if result:
                        resolved += 1
                        if not dry_run:
                            self.stdout.write(
                                f"  ✓ Resolved: {conflict.resource_path}"
                            )
                        else:
                            self.stdout.write(
                                f"  [DRY RUN] Would resolve: {conflict.resource_path}"
                            )
                    else:
                        failed += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ✗ Cannot resolve: {conflict.resource_path}"
                            )
                        )
                except Exception as e:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Error resolving {conflict.resource_path}: {str(e)}"
                        )
                    )
            
            if dry_run:
                # Rollback in dry run mode
                transaction.set_rollback(True)
        
        # Report results
        self.stdout.write(f"\nResolution Results:")
        if resolved > 0:
            self.stdout.write(
                self.style.SUCCESS(f"  Resolved: {resolved}")
            )
        if failed > 0:
            self.stdout.write(
                self.style.ERROR(f"  Failed: {failed}")
            )
        
        if not dry_run and resolved > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully resolved {resolved} conflicts"
                )
            )
    
    def _resolve_conflict(self, conflict, strategy, dry_run):
        """
        Resolve a single conflict using the specified strategy.
        
        Returns True if resolved, False otherwise.
        """
        if not conflict.existing_origin:
            # Can't resolve without existing origin
            return False
        
        from scanpipe.models import CodeOriginDetermination
        from scanpipe.models_curation import CurationProvenance
        from scanpipe.curation_schema import OriginData
        from django.utils import timezone
        
        imported_data = conflict.imported_origin_data
        if not imported_data:
            return False
        
        if strategy == "keep_existing":
            # Keep existing - just mark conflict as resolved
            if not dry_run:
                conflict.resolve(
                    strategy="keep_existing",
                    resolved_origin=conflict.existing_origin,
                    resolved_by="System",
                    notes="Kept existing curation (automated resolution)",
                )
            return True
        
        elif strategy == "use_imported":
            # Use imported - update existing origin
            if not dry_run:
                self._apply_imported_origin(conflict.existing_origin, imported_data)
                conflict.resolve(
                    strategy="use_imported",
                    resolved_origin=conflict.existing_origin,
                    resolved_by="System",
                    notes="Used imported curation (automated resolution)",
                )
            return True
        
        elif strategy == "highest_confidence":
            # Compare confidence scores
            existing_conf = (
                1.0 if conflict.existing_origin.is_verified
                else conflict.existing_origin.detected_origin_confidence or 0.5
            )
            imported_conf = imported_data.get("confidence", 0.5)
            
            if imported_conf > existing_conf:
                if not dry_run:
                    self._apply_imported_origin(conflict.existing_origin, imported_data)
                    conflict.resolve(
                        strategy="highest_confidence",
                        resolved_origin=conflict.existing_origin,
                        resolved_by="System",
                        notes=f"Used higher confidence curation (imported: {imported_conf} vs existing: {existing_conf})",
                    )
            else:
                if not dry_run:
                    conflict.resolve(
                        strategy="highest_confidence",
                        resolved_origin=conflict.existing_origin,
                        resolved_by="System",
                        notes=f"Kept higher confidence curation (existing: {existing_conf} vs imported: {imported_conf})",
                    )
            return True
        
        elif strategy == "highest_priority":
            # Compare source priorities
            from scanpipe import curation_utils
            local_source = curation_utils.get_local_curation_source()
            imported_source = conflict.imported_source
            
            if imported_source and imported_source.priority > local_source.priority:
                if not dry_run:
                    self._apply_imported_origin(conflict.existing_origin, imported_data)
                    conflict.resolve(
                        strategy="highest_priority",
                        resolved_origin=conflict.existing_origin,
                        resolved_by="System",
                        notes=f"Used higher priority source (imported: {imported_source.priority} vs local: {local_source.priority})",
                    )
            else:
                if not dry_run:
                    conflict.resolve(
                        strategy="highest_priority",
                        resolved_origin=conflict.existing_origin,
                        resolved_by="System",
                        notes="Kept higher priority source",
                    )
            return True
        
        return False
    
    def _apply_imported_origin(self, existing_origin, imported_data):
        """Apply imported origin data to existing origin determination."""
        from scanpipe.models_curation import CurationProvenance
        from django.utils import timezone
        
        # Save previous values for provenance
        previous_value = {
            "origin_type": existing_origin.effective_origin_type,
            "origin_identifier": existing_origin.effective_origin_identifier,
        }
        
        # Update as amendment
        existing_origin.amended_origin_type = imported_data["origin_type"]
        existing_origin.amended_origin_identifier = imported_data["origin_identifier"]
        existing_origin.amended_origin_notes = "Updated from imported curation (automated resolution)"
        existing_origin.amended_by = "System"
        existing_origin.is_verified = imported_data.get("is_verified", False)
        existing_origin.save()
        
        # Create provenance record
        CurationProvenance.objects.create(
            origin_determination=existing_origin,
            action_type="merged",
            actor_name="System",
            action_date=timezone.now(),
            previous_value=previous_value,
            new_value={
                "origin_type": imported_data["origin_type"],
                "origin_identifier": imported_data["origin_identifier"],
            },
            notes="Automated conflict resolution",
        )

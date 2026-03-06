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

from scanpipe.models import Project
from scanpipe import curation_utils


class Command(BaseCommand):
    help = "Import origin curations from an external FederatedCode source."
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--project",
            required=True,
            help="Project name or UUID to import curations into.",
        )
        parser.add_argument(
            "--source-url",
            required=True,
            help=(
                "URL to the curation source. Can be a Git repository "
                "(https://github.com/org/repo.git) or a direct file URL "
                "(https://example.com/curations.json)."
            ),
        )
        parser.add_argument(
            "--source-name",
            default="",
            help="Name for the curation source (for tracking provenance).",
        )
        parser.add_argument(
            "--conflict-strategy",
            choices=[
                "manual_review",
                "keep_existing",
                "use_imported",
                "highest_confidence",
                "highest_priority",
            ],
            default="manual_review",
            help=(
                "Strategy for resolving conflicts:\n"
                "  manual_review: Create conflict records for manual resolution (default)\n"
                "  keep_existing: Keep existing curations, skip imports\n"
                "  use_imported: Replace existing with imported curations\n"
                "  highest_confidence: Use curation with higher confidence score\n"
                "  highest_priority: Use source with higher priority"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without creating/updating records.",
        )
    
    def handle(self, *args, **options):
        project_identifier = options["project"]
        source_url = options["source_url"]
        source_name = options["source_name"] or source_url
        conflict_strategy = options["conflict_strategy"]
        dry_run = options["dry_run"]
        
        # Get project
        try:
            project = Project.objects.get_queryset(self.user).get_project(project_identifier)
        except Project.DoesNotExist:
            raise CommandError(f"Project not found: {project_identifier}")
        
        self.stdout.write(f"Importing curations into project: {project.name}")
        self.stdout.write(f"Source: {source_url}")
        self.stdout.write(f"Conflict strategy: {conflict_strategy}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        # Import curations
        success, stats = curation_utils.import_curations_from_url(
            project=project,
            source_url=source_url,
            source_name=source_name,
            conflict_strategy=conflict_strategy,
            dry_run=dry_run,
        )
        
        if not success:
            error = stats.get("error", "Unknown error")
            if "errors" in stats:
                self.stdout.write(self.style.ERROR("Validation errors:"))
                for err in stats["errors"]:
                    self.stdout.write(f"  - {err}")
            raise CommandError(f"Import failed: {error}")
        
        # Report results
        self.stdout.write("\nImport Results:")
        self.stdout.write(f"  Total curations: {stats.get('total', 0)}")
        self.stdout.write(
            self.style.SUCCESS(f"  Imported: {stats.get('imported', 0)}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"  Updated: {stats.get('updated', 0)}")
        )
        self.stdout.write(f"  Skipped: {stats.get('skipped', 0)}")
        
        if stats.get('conflicts', 0) > 0:
            self.stdout.write(
                self.style.WARNING(f"  Conflicts: {stats['conflicts']}")
            )
            self.stdout.write(
                "\nConflicts created. Review them in the admin interface or use:\n"
                f"  python manage.py resolve-curation-conflicts --project {project.name}"
            )
        
        if stats.get('errors', 0) > 0:
            self.stdout.write(
                self.style.ERROR(f"  Errors: {stats['errors']}")
            )
            if stats.get('error_details'):
                self.stdout.write("\nError details (first 10):")
                for error in stats['error_details'][:10]:
                    self.stdout.write(f"  - {error}")
        
        if not dry_run and (stats.get('imported', 0) > 0 or stats.get('updated', 0) > 0):
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully imported/updated "
                    f"{stats['imported'] + stats['updated']} curations"
                )
            )

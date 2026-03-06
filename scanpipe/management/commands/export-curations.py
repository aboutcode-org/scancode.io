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

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from scanpipe.models import Project
from scanpipe import curation_utils


class Command(BaseCommand):
    help = "Export origin curations from a project to FederatedCode or a local file."
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--project",
            required=True,
            help="Project name or UUID to export curations from.",
        )
        parser.add_argument(
            "--destination",
            choices=["federatedcode", "file"],
            default="federatedcode",
            help="Export destination: federatedcode (Git repo) or file (local).",
        )
        parser.add_argument(
            "--output-path",
            help=(
                "Output file path (only for file destination). "
                "Defaults to <project_work_dir>/curations/origins.json"
            ),
        )
        parser.add_argument(
            "--format",
            choices=["json", "yaml"],
            default="json",
            help="Export format (only for file destination).",
        )
        parser.add_argument(
            "--curator-name",
            default="",
            help="Name of the curator (for provenance).",
        )
        parser.add_argument(
            "--curator-email",
            default="",
            help="Email of the curator (for provenance).",
        )
        parser.add_argument(
            "--all-curations",
            action="store_true",
            help="Export all curations (not just verified ones).",
        )
        parser.add_argument(
            "--include-propagated",
            action="store_true",
            help="Include propagated origins in export.",
        )
        parser.add_argument(
            "--no-provenance",
            action="store_true",
            help="Exclude provenance chain from export.",
        )
    
    def handle(self, *args, **options):
        project_identifier = options["project"]
        destination = options["destination"]
        
        # Get project
        try:
            project = Project.objects.get_queryset(self.user).get_project(project_identifier)
        except Project.DoesNotExist:
            raise CommandError(f"Project not found: {project_identifier}")
        
        self.stdout.write(f"Exporting curations from project: {project.name}")
        
        verified_only = not options["all_curations"]
        include_propagated = options["include_propagated"]
        include_provenance = not options["no_provenance"]
        curator_name = options["curator_name"]
        curator_email = options["curator_email"]
        
        if destination == "federatedcode":
            # Export to FederatedCode Git repository
            success, message = curation_utils.export_curations_to_federatedcode(
                project=project,
                curator_name=curator_name,
                curator_email=curator_email,
                verified_only=verified_only,
                include_propagated=include_propagated,
            )
            
            if success:
                self.stdout.write(self.style.SUCCESS(message))
            else:
                raise CommandError(f"Export failed: {message}")
        
        else:  # file
            # Determine output path
            if options["output_path"]:
                output_path = Path(options["output_path"])
            else:
                output_path = project.project_work_directory / "curations" / "origins.json"
                if options["format"] == "yaml":
                    output_path = output_path.with_suffix(".yaml")
            
            # Export to file
            success, result = curation_utils.export_curations_to_file(
                project=project,
                output_path=output_path,
                format=options["format"],
                verified_only=verified_only,
                include_propagated=include_propagated,
                include_provenance=include_provenance,
                curator_name=curator_name,
                curator_email=curator_email,
            )
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully exported curations to: {result}")
                )
            else:
                raise CommandError(f"Export failed: {result}")

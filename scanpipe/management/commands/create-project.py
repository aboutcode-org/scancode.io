# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.core.management import call_command
from django.core.management.base import BaseCommand

from scanpipe.management.commands import validate_input_files
from scanpipe.management.commands import validate_pipelines
from scanpipe.models import Project


class Command(BaseCommand):
    help = "Create a ScanPipe project."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Project name.")
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            default=list(),
            help=(
                "Pipelines names to add on the project. "
                "The pipelines are added and ran respecting this provided order."
            ),
        )
        parser.add_argument(
            "--input-file",
            action="append",
            dest="inputs_files",
            default=list(),
            help="Input file locations to copy in the input/ work directory.",
        )
        parser.add_argument(
            "--input-url",
            action="append",
            dest="input_urls",
            default=list(),
            help="Input URLs to download in the input/ work directory.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the pipelines right after project creation.",
        )

    def handle(self, *args, **options):
        name = options["name"]
        pipeline_names = options["pipelines"]
        inputs_files = options["inputs_files"]
        input_urls = options["input_urls"]  # TODO
        execute = options["execute"]

        project = Project(name=name)
        try:
            project.full_clean()
        except ValidationError as e:
            raise CommandError("\n".join(e.messages))

        # Run validation before creating the project in the database
        validate_pipelines(pipeline_names)
        validate_input_files(inputs_files)

        if execute and not pipeline_names:
            raise CommandError("The --execute option requires one or more pipelines.")

        project.save()
        msg = f"Project {name} created with work directory {project.work_directory}"
        self.stdout.write(self.style.SUCCESS(msg))

        for pipeline_name in pipeline_names:
            project.add_pipeline(pipeline_name)

        for file_location in inputs_files:
            project.copy_input_from(file_location)

        if execute:
            call_command(
                "execute", project=project, stderr=self.stderr, stdout=self.stdout
            )

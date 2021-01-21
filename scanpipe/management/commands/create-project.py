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

from scanpipe.management.commands import validate_inputs
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
                "Pipelines locations to add on the project. "
                "The pipelines are added and ran respecting this provided order."
            ),
        )
        parser.add_argument(
            "--input",
            action="append",
            dest="inputs",
            default=list(),
            help="Input file locations to copy in the input/ work directory.",
        )
        parser.add_argument(
            "--run",
            action="store_true",
            help="Start running the pipelines right after project creation.",
        )

    def handle(self, *args, **options):
        name = options["name"]
        pipelines = options["pipelines"]
        inputs = options["inputs"]
        run = options["run"]

        project = Project(name=name)
        try:
            project.full_clean()
        except ValidationError as e:
            raise CommandError("\n".join(e.messages))

        # Run validation before creating the project in the database
        validate_pipelines(pipelines)
        validate_inputs(inputs)

        if run and not pipelines:
            raise CommandError("The --run option requires one or more pipelines.")

        project.save()
        msg = f"Project {name} created with work directory {project.work_directory}"
        self.stdout.write(self.style.SUCCESS(msg))

        for pipeline_location in pipelines:
            project.add_pipeline(pipeline_location)

        for input_location in inputs:
            project.copy_input_from(input_location)

        if run:
            call_command("run", project=project, stderr=self.stderr, stdout=self.stdout)

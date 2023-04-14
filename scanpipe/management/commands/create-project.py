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

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import validate_copy_from
from scanpipe.management.commands import validate_input_files
from scanpipe.management.commands import validate_pipelines
from scanpipe.models import Project


class Command(AddInputCommandMixin, BaseCommand):
    help = "Create a ScanPipe project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("name", help="Project name.")
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            default=list(),
            help=(
                "Pipelines names to add to the project."
                "The pipelines are added and executed based on their given order."
            ),
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the pipelines right after the project creation.",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            help=(
                "Add the pipeline run to the tasks queue for execution by a worker "
                "instead of running in the current thread. "
                "Applies only when --execute is provided."
            ),
        )

    def handle(self, *args, **options):
        name = options["name"]
        pipeline_names = options["pipelines"]
        inputs_files = options["inputs_files"]
        input_urls = options["input_urls"]
        copy_from = options["copy_codebase"]
        execute = options["execute"]

        project = Project(name=name)
        try:
            project.full_clean()
        except ValidationError as e:
            raise CommandError("\n".join(e.messages))

        # Run validation before creating the project in the database
        validate_pipelines(pipeline_names)
        validate_input_files(inputs_files)
        validate_copy_from(copy_from)

        if execute and not pipeline_names:
            raise CommandError("The --execute option requires one or more pipelines.")

        project.save()
        msg = f"Project {name} created with work directory {project.work_directory}"
        self.stdout.write(msg, self.style.SUCCESS)

        for pipeline_name in pipeline_names:
            project.add_pipeline(pipeline_name)

        self.project = project
        if inputs_files:
            self.validate_input_files(inputs_files)
            self.handle_input_files(inputs_files)

        if input_urls:
            self.handle_input_urls(input_urls)

        if copy_from:
            self.handle_copy_codebase(copy_from)

        if execute:
            call_command(
                "execute",
                project=project,
                stderr=self.stderr,
                stdout=self.stdout,
                **{"async": options["async"]},
            )

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

from pathlib import Path

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from scanpipe.models import Project
from scanpipe.pipes.fetch import fetch_urls

scanpipe_app_config = apps.get_app_config("scanpipe")


class ProjectCommand(BaseCommand):
    """
    Base class for management commands that take a mandatory --project argument.
    The project is retrieved from the database and stored on the intance as
    `self.project`.
    """

    project = None

    def add_arguments(self, parser):
        parser.add_argument("--project", required=True, help="Project name.")

    def handle(self, *args, **options):
        project_name = options["project"]
        try:
            self.project = Project.objects.get(name=project_name)
        except ObjectDoesNotExist:
            raise CommandError(f"Project {project_name} does not exit")


class RunStatusCommandMixin:
    def get_run_status_code(self, run):
        status = " "
        if run.task_succeeded:
            status = self.style.SUCCESS("SUCCESS")
        elif run.task_exitcode and run.task_exitcode > 0:
            status = self.style.ERROR("FAILURE")
        elif run.task_start_date:
            status = "RUNNING"
        return status


class AddInputCommandMixin:
    def add_arguments(self, parser):
        super().add_arguments(parser)
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

    def handle_input_files(self, inputs_files):
        """
        Copy provided `inputs_files` to the project `input` directory.
        """
        copied = []

        for file_location in inputs_files:
            self.project.copy_input_from(file_location)
            filename = Path(file_location).name
            copied.append(filename)
            self.project.add_input_source(filename, source="uploaded")

        msg = "File(s) copied to the project inputs directory:"
        self.stdout.write(self.style.SUCCESS(msg))
        msg = "\n".join(["- " + filename for filename in copied])
        self.stdout.write(msg)

    @staticmethod
    def validate_input_files(inputs_files):
        """
        Raise an error if one of the provided `inputs_files` is not an existing file.
        """
        for file_location in inputs_files:
            file_path = Path(file_location)
            if not file_path.is_file():
                raise CommandError(f"{file_location} not found or not a file")

    def handle_input_urls(self, input_urls):
        """
        Fetch provided `input_urls` and store to the project `input` directory.
        """
        downloads, errors = fetch_urls(self.project, input_urls)

        if downloads:
            msg = "File(s) downloaded to the project inputs directory:"
            self.stdout.write(self.style.SUCCESS(msg))
            msg = "\n".join(["- " + downloaded.filename for downloaded in downloads])
            self.stdout.write(msg)

        if errors:
            self.stdout.write(self.style.ERROR("Could not fetch URL(s):"))
            msg = "\n".join(["- " + url for url in errors])
            self.stdout.write(self.style.ERROR(msg))


def validate_input_files(file_locations):
    """
    Raise an error if one of the provided `file_locations` is not an existing file.
    """
    for file_location in file_locations:
        file_path = Path(file_location)
        if not file_path.is_file():
            raise CommandError(f"{file_location} not found or not a file")


def validate_pipelines(pipeline_names):
    """
    Raise an error if one of the `pipeline_names` is not available.
    """
    for pipeline_name in pipeline_names:
        if pipeline_name not in scanpipe_app_config.pipelines:
            raise CommandError(
                f"{pipeline_name} is not a valid pipeline. \n"
                f"Available: {', '.join(scanpipe_app_config.pipelines.keys())}"
            )

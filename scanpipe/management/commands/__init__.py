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

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.pipes import count_group_by
from scanpipe.pipes.fetch import fetch_urls

scanpipe_app = apps.get_app_config("scanpipe")


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
        status = run.status
        RunStatus = run.Status

        if status == RunStatus.SUCCESS:
            return self.style.SUCCESS(status.upper())

        elif status in [RunStatus.FAILURE, RunStatus.STOPPED, RunStatus.STALE]:
            return self.style.ERROR(status.upper())

        return status.upper()

    def display_status(self, project, verbosity):
        message = [
            self.style.HTTP_INFO(f"Project: {project.name}"),
        ]

        if verbosity >= 2:
            message.extend(
                [
                    f"Create date: {project.created_date.strftime('%b %d %Y %H:%M')}",
                    f"Work directory: {project.work_directory}",
                ]
            )

        if verbosity >= 3:
            message.append("\nDatabase:")

            for model_class in [CodebaseResource, DiscoveredPackage, ProjectError]:
                queryset = model_class.objects.project(project)
                message.append(f" - {model_class.__name__}: {queryset.count()}")

                if model_class == CodebaseResource:
                    status_summary = count_group_by(queryset, "status")
                    for status, count in status_summary.items():
                        status = status or "(no status)"
                        message.append(f"   - {status}: {count}")

            inputs, missing_inputs = project.inputs_with_source
            if inputs:
                message.append("\nInputs:")
                for input in inputs:
                    message.append(f" - {input.get('name')} ({input.get('source')})")

            runs = project.runs.all()
            if runs:
                message.append("\nPipelines:")
                for run in runs:
                    status_code = self.get_run_status_code(run)
                    msg = f" [{status_code}] {run.pipeline_name}"
                    execution_time = run.execution_time
                    if execution_time:
                        msg += f" (executed in {execution_time} seconds)"
                    message.append(msg)
                    if run.log:
                        for line in run.log.rstrip("\n").split("\n"):
                            message.append(3 * " " + line)

        for line in message:
            self.stdout.write(line)


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
        Copies provided `inputs_files` to the project's `input` directory.
        """
        copied = []

        for file_location in inputs_files:
            self.project.copy_input_from(file_location)
            filename = Path(file_location).name
            copied.append(filename)
            self.project.add_input_source(filename, source="uploaded", save=True)

        msg = "File(s) copied to the project inputs directory:"
        self.stdout.write(self.style.SUCCESS(msg))
        msg = "\n".join(["- " + filename for filename in copied])
        self.stdout.write(msg)

    @staticmethod
    def validate_input_files(inputs_files):
        """
        Raises an error if one of the provided `inputs_files` is not an existing
        file.
        """
        for file_location in inputs_files:
            file_path = Path(file_location)
            if not file_path.is_file():
                raise CommandError(f"{file_location} not found or not a file")

    def handle_input_urls(self, input_urls):
        """
        Fetches provided `input_urls` and stores it in the project's `input`
        directory.
        """
        downloads, errors = fetch_urls(input_urls)

        if downloads:
            self.project.add_downloads(downloads)
            msg = "File(s) downloaded to the project inputs directory:"
            self.stdout.write(self.style.SUCCESS(msg))
            msg = "\n".join(["- " + downloaded.filename for downloaded in downloads])
            self.stdout.write(msg)

        if errors:
            self.stderr.write(self.style.ERROR("Could not fetch URL(s):"))
            msg = "\n".join(["- " + url for url in errors])
            self.stderr.write(self.style.ERROR(msg))


def validate_input_files(file_locations):
    """
    Raises an error if one of the provided `file_locations` is not an existing file.
    """
    for file_location in file_locations:
        file_path = Path(file_location)
        if not file_path.is_file():
            raise CommandError(f"{file_location} not found or not a file")


def validate_pipelines(pipeline_names):
    """
    Raises an error if one of the `pipeline_names` is not available.
    """
    for pipeline_name in pipeline_names:
        if pipeline_name not in scanpipe_app.pipelines:
            raise CommandError(
                f"{pipeline_name} is not a valid pipeline. \n"
                f"Available: {', '.join(scanpipe_app.pipelines.keys())}"
            )

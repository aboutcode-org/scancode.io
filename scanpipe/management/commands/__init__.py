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

import shutil
import traceback
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.template.defaultfilters import pluralize

from scanpipe import tasks
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectMessage
from scanpipe.pipes import count_group_by

scanpipe_app = apps.get_app_config("scanpipe")


class ProjectCommand(BaseCommand):
    """
    Base class for management commands that take a mandatory --project argument.
    The project is retrieved from the database and stored on the instance as
    `self.project`.
    """

    project = None
    verbosity = 1

    def add_arguments(self, parser):
        parser.add_argument("--project", required=True, help="Project name.")

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
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

    def get_run_status_messages(self, project):
        messages = []

        if runs := project.runs.all():
            messages.append("\nPipelines:")
            for run in runs:
                status_code = self.get_run_status_code(run)
                msg = f" [{status_code}] {run.pipeline_name}"
                execution_time = run.execution_time
                if execution_time:
                    msg += f" (executed in {execution_time} seconds)"
                messages.append(msg)
                if run.log:
                    for line in run.log.rstrip("\n").splitlines():
                        messages.append(3 * " " + line)

        return messages

    def get_queryset_objects_messages(self, project):
        messages = []

        for model_class in [CodebaseResource, DiscoveredPackage, ProjectMessage]:
            queryset = model_class.objects.project(project)
            messages.append(f" - {model_class.__name__}: {queryset.count()}")

            if model_class == CodebaseResource:
                status_summary = count_group_by(queryset, "status")
                for status, count in status_summary.items():
                    status = status or "(no status)"
                    messages.append(f"   - {status}: {count}")

        inputs_sources = project.get_inputs_with_source()
        if inputs_sources:
            messages.append("\nInputs:")
            for inputs_source in inputs_sources:
                line = f" - {inputs_source.get('filename', '')} "
                if inputs_source.get("is_uploaded"):
                    line += "[source=uploaded]"
                else:
                    line += f"[download_url={inputs_source.get('download_url')}]"
                if not inputs_source.get("exists"):
                    line += self.style.ERROR(" NOT ON DISK")
                messages.append(line)

        return messages

    def display_status(self, project, verbosity):
        project_label = project.name
        if project.is_archived:
            project_label += " [archived]"

        message = [
            self.style.HTTP_INFO(project_label),
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
            message.extend(self.get_queryset_objects_messages(project))
            message.extend(self.get_run_status_messages(project))

        for line in message:
            self.stdout.write(line)


class PipelineCommandMixin:
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            default=list(),
            help=(
                "Pipelines names to add to the project. "
                "The pipelines are added and executed based on their given order. "
                'Groups can be provided using the "pipeline_name:option1,option2" '
                "syntax."
            ),
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the pipelines right after the project creation.",
        )


class AddInputCommandMixin:
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--input-file",
            action="append",
            dest="input_files",
            default=list(),
            help=(
                "Input file locations to copy in the input/ work directory. "
                'Use the "filename:tag" syntax to tag input files such as '
                '"path/filename:tag"'
            ),
        )
        parser.add_argument(
            "--input-url",
            action="append",
            dest="input_urls",
            default=list(),
            help=(
                "Input URLs to download in the input/ work directory. "
                'Use the "url#tag" syntax to tag downloaded files such as '
                '"https://url.com/filename#tag"'
            ),
        )
        parser.add_argument(
            "--copy-codebase",
            metavar="SOURCE_DIRECTORY",
            dest="copy_codebase",
            help=(
                "Copy the content of the provided source directory into the codebase/ "
                "work directory."
            ),
        )

    @staticmethod
    def extract_tag_from_input_files(input_files):
        """
        Add support for the ":tag" suffix in file location.

        For example: "/path/to/file.zip:tag"
        """
        return extract_tag_from_input_files(input_files=input_files)

    def handle_input_files(self, input_files_data):
        """Copy provided `input_files` to the project's `input` directory."""
        handle_input_files(
            project=self.project, input_files_data=input_files_data, command=self
        )

    @staticmethod
    def validate_input_files(input_files):
        """Raise an error if one of the provided `input_files` entry does not exist."""
        validate_input_files(input_files=input_files)

    def handle_input_urls(self, input_urls):
        """
        Fetch provided `input_urls` and stores it in the project's `input`
        directory.
        """
        handle_input_urls(project=self.project, input_urls=input_urls, command=self)

    def handle_copy_codebase(self, copy_from):
        """Copy `codebase_path` tree to the project's `codebase` directory."""
        handle_copy_codebase(project=self.project, copy_from=copy_from, command=self)


def validate_copy_from(copy_from):
    """Raise an error if `copy_from` is not an available directory"""
    if copy_from:
        copy_from_path = Path(copy_from)
        if not copy_from_path.exists():
            raise CommandError(f"{copy_from} not found")
        if not copy_from_path.is_dir():
            raise CommandError(f"{copy_from} is not a directory")


def extract_group_from_pipelines(pipelines):
    """
    Add support for the ":option1,option2" suffix in pipeline data.

    For example: "map_deploy_to_develop:Java,JavaScript"
    """
    pipelines_data = {}
    for pipeline in pipelines:
        pipeline_name, groups = scanpipe_app.extract_group_from_pipeline(pipeline)
        pipelines_data[pipeline_name] = groups
    return pipelines_data


def validate_pipeline(pipeline_name):
    """Raise an error if the ``pipeline_name`` is not available."""
    if pipeline_name not in scanpipe_app.pipelines:
        raise CommandError(
            f"{pipeline_name} is not a valid pipeline. \n"
            f"Available: {', '.join(scanpipe_app.pipelines.keys())}"
        )


def validate_pipelines(pipelines_data):
    """Raise an error if one of the `pipeline_names` is not available."""
    # Backward compatibility with old pipeline names.
    pipelines_data = {
        scanpipe_app.get_new_pipeline_name(pipeline_name): groups
        for pipeline_name, groups in pipelines_data.items()
    }

    for pipeline_name in pipelines_data.keys():
        validate_pipeline(pipeline_name)

    return pipelines_data


def extract_tag_from_input_file(file_location):
    """
    Parse a file location with optional tag suffix.

    For example: "/path/to/file.zip:tag"
    """
    if ":" in file_location:
        cleaned_location, tag = file_location.split(":", maxsplit=1)
        return cleaned_location, tag
    return file_location, ""


def extract_tag_from_input_files(input_files):
    """Parse multiple file locations with optional tag suffixes."""
    return dict(
        extract_tag_from_input_file(file_location) for file_location in input_files
    )


def validate_input_files(input_files):
    """Raise an error if one of the provided `input_files` entry does not exist."""
    for file_location in input_files:
        file_path = Path(file_location)
        if not file_path.is_file():
            raise CommandError(f"{file_location} not found or not a file")


def validate_project_inputs(pipelines, input_files, copy_from):
    """
    Validate `pipelines`, `input_files`, and `copy_from`, returning a tuple
    of dictionaries containing the pipeline data of `pipelines` and the
    input files data from `input_files.
    """
    pipelines_data = {}
    input_files_data = {}

    if pipelines:
        pipelines_data = extract_group_from_pipelines(pipelines)
        pipelines_data = validate_pipelines(pipelines_data)

    if input_files:
        input_files_data = extract_tag_from_input_files(input_files)
        validate_input_files(input_files=input_files_data.keys())

    if copy_from:
        validate_copy_from(copy_from)

    return pipelines_data, input_files_data


def handle_input_files(project, input_files_data, command=None):
    """Copy provided `input_files` to the project's `input` directory."""
    copied = []

    for file_location, tag in input_files_data.items():
        project.copy_input_from(file_location)
        filename = Path(file_location).name
        copied.append(filename)
        project.add_input_source(
            filename=filename,
            is_uploaded=True,
            tag=tag,
        )

    if command and command.verbosity > 0:
        msg = f"File{pluralize(copied)} copied to the project inputs directory:"
        command.stdout.write(msg, command.style.SUCCESS)
        msg = "\n".join(["- " + filename for filename in copied])
        command.stdout.write(msg)


def handle_input_urls(project, input_urls, command=None):
    """Add provided `input_urls` as input sources of the project."""
    for url in input_urls:
        project.add_input_source(download_url=url)

    if input_urls and command and command.verbosity > 0:
        msg = "URL(s) added as project input sources:"
        command.stdout.write(msg, command.style.SUCCESS)
        command.stdout.write("\n".join([f"- {url}" for url in input_urls]))


def handle_copy_codebase(project, copy_from, command=None):
    """Copy `codebase_path` tree to the project's `codebase` directory."""
    project_codebase = project.codebase_path
    if command and command.verbosity > 0:
        msg = f"{copy_from} content copied in {project_codebase}"
        command.stdout.write(msg, command.style.SUCCESS)
    shutil.copytree(src=copy_from, dst=project_codebase, dirs_exist_ok=True)


def add_project_inputs(
    project, pipelines_data, input_files_data, input_urls, copy_from, command=None
):
    for pipeline_name, selected_groups in pipelines_data.items():
        project.add_pipeline(pipeline_name, selected_groups=selected_groups)

    if input_files_data:
        handle_input_files(
            project=project, input_files_data=input_files_data, command=command
        )

    if input_urls:
        handle_input_urls(project=project, input_urls=input_urls, command=command)

    if copy_from:
        handle_copy_codebase(project=project, copy_from=copy_from, command=command)


def execute_project(project, run_async=False, command=None):  # noqa: C901
    verbosity = getattr(command, "verbosity", 1) if command else 0
    run = project.get_next_run()

    if not run:
        raise CommandError(f"No pipelines to run on project {project}")

    if run_async:
        if not settings.SCANCODEIO_ASYNC:
            msg = "SCANCODEIO_ASYNC=False is not compatible with --async option."
            raise CommandError(msg)

        run.start()
        if verbosity > 0:
            msg = f"{run.pipeline_name} added to the tasks queue for execution."
            command.stdout.write(msg, command.style.SUCCESS)
        return

    if verbosity > 0:
        command.stdout.write(f"Start the {run.pipeline_name} pipeline execution...")

    try:
        tasks.execute_pipeline_task(run.pk)
    except KeyboardInterrupt:
        run.set_task_stopped()
        raise CommandError("Pipeline execution stopped.")
    except Exception:
        traceback_str = traceback.format_exc()
        run.set_task_ended(exitcode=1, output=traceback_str)
        raise CommandError(traceback_str)

    run.refresh_from_db()

    if not run.task_succeeded:
        msg = f"Error during {run.pipeline_name} execution:\n{run.task_output}"
        raise CommandError(msg)
    elif verbosity > 0:
        msg = f"{run.pipeline_name} successfully executed on project {project}"
        command.stdout.write(msg, command.style.SUCCESS)


def create_project(
    name,
    pipelines=None,
    input_files=None,
    input_urls=None,
    copy_from="",
    notes="",
    labels=None,
    execute=False,
    run_async=False,
    create_global_webhook=True,
    command=None,
):
    verbosity = getattr(command, "verbosity", 1)

    if execute and not pipelines:
        raise CommandError("The execute argument requires one or more pipelines.")

    project = Project(name=name)
    if notes:
        project.notes = notes

    try:
        project.full_clean(exclude=["slug"])
    except ValidationError as e:
        raise CommandError("\n".join(e.messages))

    # Run validation before creating the project in the database
    pipelines_data, input_files_data = validate_project_inputs(
        pipelines=pipelines, input_files=input_files, copy_from=copy_from
    )

    save_kwargs = {}
    if not create_global_webhook:
        save_kwargs = {"skip_global_webhook": True}

    project.save(**save_kwargs)

    if labels:
        project.labels.add(*labels)

    if command:
        command.project = project

    if command and verbosity > 0:
        msg = f"Project {name} created with work directory {project.work_directory}"
        command.stdout.write(msg, command.style.SUCCESS)

    add_project_inputs(
        project=project,
        pipelines_data=pipelines_data,
        input_files_data=input_files_data,
        input_urls=input_urls,
        copy_from=copy_from,
        command=command,
    )

    if execute:
        execute_project(project=project, run_async=run_async, command=command)

    return project


class ExecuteProjectCommandMixin:
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--async",
            action="store_true",
            dest="async",
            help=(
                "Add the pipeline run to the tasks queue for execution by a worker "
                "instead of running in the current thread."
            ),
        )

    def execute_project(self, run_async=False):
        execute_project(project=self.project, run_async=run_async, command=self)


class CreateProjectCommandMixin(ExecuteProjectCommandMixin):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--notes",
            help="Optional notes about the project.",
        )
        parser.add_argument(
            "--label",
            action="append",
            dest="labels",
            default=list(),
            help="Optional labels for the project.",
        )
        parser.add_argument(
            "--no-global-webhook",
            action="store_true",
            help=(
                "Skip the creation of the global webhook. "
                "This option is only useful if a global webhook is defined in the "
                "settings."
            ),
        )

    def create_project(
        self,
        name,
        pipelines=None,
        input_files=None,
        input_urls=None,
        copy_from="",
        notes="",
        labels=None,
        execute=False,
        run_async=False,
        create_global_webhook=True,
    ):
        if execute and not pipelines:
            raise CommandError("The --execute option requires one or more pipelines.")

        return create_project(
            name=name,
            pipelines=pipelines,
            input_files=input_files,
            input_urls=input_urls,
            copy_from=copy_from,
            notes=notes,
            labels=labels,
            execute=execute,
            run_async=run_async,
            create_global_webhook=create_global_webhook,
            command=self,
        )

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

import inspect
import json
import logging
import re
import shutil
import uuid
from contextlib import suppress
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from traceback import format_tb

from django.apps import apps
from django.conf import settings
from django.core import checks
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db import transaction
from django.db.models import Count
from django.db.models import Q
from django.db.models import TextField
from django.db.models.functions import Cast
from django.db.models.functions import Lower
from django.dispatch import receiver
from django.forms import model_to_dict
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

import django_rq
import redis
import requests
from commoncode.fileutils import parent_directory
from commoncode.hash import multi_checksums
from packageurl import PackageURL
from packageurl import normalize_qualifiers
from packageurl.contrib.django.models import PackageURLQuerySetMixin
from rest_framework.authtoken.models import Token
from rq.command import send_stop_job_command
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.job import JobStatus

from scancodeio import __version__ as scancodeio_version
from scanpipe import tasks
from scanpipe.packagedb_models import AbstractPackage
from scanpipe.packagedb_models import AbstractResource

logger = logging.getLogger(__name__)
scanpipe_app = apps.get_app_config("scanpipe")


class RunInProgressError(Exception):
    """Run are in progress or queued on this project."""


class UUIDPKModel(models.Model):
    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.uuid)

    @property
    def short_uuid(self):
        return str(self.uuid)[0:8]


class AbstractTaskFieldsModel(models.Model):
    task_id = models.UUIDField(
        blank=True,
        null=True,
        editable=False,
    )
    task_start_date = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )
    task_end_date = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
    )
    task_exitcode = models.IntegerField(
        null=True,
        blank=True,
        editable=False,
    )
    task_output = models.TextField(
        blank=True,
        editable=False,
    )

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        """
        Before deletion of the Run instance, try to stop the task if currently running
        or to remove it from the queue if currently queued.

        Note that projects with queued or running pipeline runs cannot be deleted.
        See the `_raise_if_run_in_progress` method.
        The following if statements should not be triggered unless the `.delete()`
        method is directly call from a instance of this class.
        """
        with suppress(redis.exceptions.ConnectionError, AttributeError):
            if self.status == self.Status.RUNNING:
                self.stop_task()
            elif self.status == self.Status.QUEUED:
                self.delete_task(delete_self=False)

        return super().delete(*args, **kwargs)

    @staticmethod
    def get_job(job_id):
        with suppress(NoSuchJobError):
            return Job.fetch(job_id, connection=django_rq.get_connection())

    @property
    def job(self):
        """
        None if the job could not be found in the queues registries.
        """
        return self.get_job(str(self.task_id))

    @property
    def job_status(self):
        job = self.job
        if job:
            return self.job.get_status()

    @property
    def task_succeeded(self):
        """
        Returns True if the task was successfully executed.
        """
        return self.task_exitcode == 0

    @property
    def task_failed(self):
        """
        Returns True if the task failed.
        """
        return self.task_exitcode and self.task_exitcode > 0

    @property
    def task_stopped(self):
        """
        Returns True if the task was stopped.
        """
        return self.task_exitcode == 99

    @property
    def task_staled(self):
        """
        Returns True if the task staled.
        """
        return self.task_exitcode == 88

    class Status(models.TextChoices):
        """
        List of Run status.
        """

        NOT_STARTED = "not_started"
        QUEUED = "queued"
        RUNNING = "running"
        SUCCESS = "success"
        FAILURE = "failure"
        STOPPED = "stopped"
        STALE = "stale"

    @property
    def status(self):
        """
        Returns the task current status.
        """
        status = self.Status

        if self.task_succeeded:
            return status.SUCCESS

        elif self.task_staled:
            return status.STALE

        elif self.task_stopped:
            return status.STOPPED

        elif self.task_failed:
            return status.FAILURE

        elif self.task_start_date:
            return status.RUNNING

        elif self.task_id:
            return status.QUEUED

        return status.NOT_STARTED

    @property
    def execution_time(self):
        if self.task_staled:
            return

        elif self.task_end_date and self.task_start_date:
            total_seconds = (self.task_end_date - self.task_start_date).total_seconds()
            return int(total_seconds)

    @property
    def execution_time_for_display(self):
        execution_time = self.execution_time
        if execution_time:
            message = f"{execution_time} seconds"
            if execution_time > 3600:
                message += f" ({execution_time / 3600:.1f} hours)"
            elif execution_time > 60:
                message += f" ({execution_time / 60:.1f} minutes)"
            return message

    def reset_task_values(self):
        """
        Resets all task-related fields to their initial null value.
        """
        self.task_id = None
        self.task_start_date = None
        self.task_end_date = None
        self.task_exitcode = None
        self.task_output = ""

    def set_task_started(self, task_id):
        """
        Sets the `task_id` and `task_start_date` fields before executing the task.
        """
        self.task_id = task_id
        self.task_start_date = timezone.now()
        self.save()

    def set_task_ended(self, exitcode, output="", refresh_first=True):
        """
        Sets the task-related fields after the task execution.

        An optional `refresh_first` —enabled by default— forces refreshing
        the instance with the latest data from the database before saving.
        This prevents losing values saved on the instance during the task
        execution.
        """
        if refresh_first:
            self.refresh_from_db()

        self.task_exitcode = exitcode
        self.task_output = output
        self.task_end_date = timezone.now()
        self.save()

    def set_task_queued(self):
        """
        Sets the task as "queued" by updating the `task_id` from None to this instance
        `pk`.
        Uses the QuerySet `update` method instead of `save` to prevent overriding
        any fields that were set but not saved yet in the DB.
        """
        manager = self.__class__.objects
        return manager.filter(pk=self.pk, task_id__isnull=True).update(task_id=self.pk)

    def set_task_staled(self):
        """
        Sets the task as "stale" using a special 88 exitcode value.
        """
        self.set_task_ended(exitcode=88)

    def set_task_stopped(self):
        """
        Sets the task as "stopped" using a special 99 exitcode value.
        """
        self.set_task_ended(exitcode=99)

    def stop_task(self):
        """
        Stops a "running" task.
        """
        if not settings.SCANCODEIO_ASYNC:
            self.set_task_stopped()
            return

        job_status = self.job_status

        if not job_status:
            self.set_task_staled()
            return

        if self.job_status == JobStatus.FAILED:
            self.set_task_ended(
                exitcode=1, output=f"Killed from outside, exc_info={self.job.exc_info}"
            )
            return

        send_stop_job_command(
            connection=django_rq.get_connection(), job_id=str(self.task_id)
        )
        self.set_task_stopped()

    def delete_task(self, delete_self=True):
        """
        Deletes a "not started" or "queued" task.
        """
        if settings.SCANCODEIO_ASYNC and self.task_id:
            job = self.job
            if job:
                self.job.delete()

        if delete_self:
            self.delete()


class ExtraDataFieldMixin(models.Model):
    """
    Adds the `extra_data` field and helper methods.
    """

    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Optional mapping of extra data key/values."),
    )

    def update_extra_data(self, data):
        """
        Updates the `extra_data` field with the provided `data` dict.
        """
        if type(data) != dict:
            raise ValueError("Argument `data` value must be a dict()")

        self.extra_data.update(data)
        self.save()

    class Meta:
        abstract = True


def get_project_work_directory(project):
    """
    Returns the work directory location for a given `project`.
    The `project` name is "slugified" to generate a nicer directory path without
    any whitespace or special characters.
    A short version of the `project` uuid is added as a suffix to ensure
    uniqueness of the work directory location.
    """
    project_workspace_id = f"{slugify(project.name)}-{project.short_uuid}"
    return f"{scanpipe_app.workspace_path}/projects/{project_workspace_id}"


class ProjectQuerySet(models.QuerySet):
    def with_counts(self, *fields):
        """
        Annotate the QuerySet with counts of provided relational `fields`.

        Usage:
            project_queryset.with_counts("codebaseresources", "discoveredpackages")
        """
        annotations = {}
        for field_name in fields:
            annotations[f"{field_name}_count"] = Count(field_name, distinct=True)

        return self.annotate(**annotations)


class Project(UUIDPKModel, ExtraDataFieldMixin, models.Model):
    """
    The Project encapsulates all analysis processing.
    Multiple analysis pipelines can be run on the same project.
    """

    created_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Creation date for this project."),
    )
    name = models.CharField(
        unique=True,
        db_index=True,
        max_length=100,
        help_text=_("Name for this project."),
    )
    WORK_DIRECTORIES = ["input", "output", "codebase", "tmp"]
    work_directory = models.CharField(
        max_length=2048,
        editable=False,
        help_text=_("Project work directory location."),
    )
    input_sources = models.JSONField(default=dict, blank=True, editable=False)
    is_archived = models.BooleanField(
        default=False,
        editable=False,
        help_text=_(
            "Archived projects cannot be modified anymore and are not displayed by "
            "default in project lists. Multiple levels of data cleanup may have "
            "happened during the archive operation."
        ),
    )

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Saves this project instance.
        The workspace directories are set up during project creation.
        """
        if not self.work_directory:
            self.work_directory = get_project_work_directory(project=self)
            self.setup_work_directory()
        super().save(*args, **kwargs)

    def archive(self, remove_input=False, remove_codebase=False, remove_output=False):
        """
        Set the project `is_archived` field to True.

        The `remove_input`, `remove_codebase`, and `remove_output` can be provided
        during the archive operation to delete the related work directories.

        The project cannot be archived if one of its related run is queued or already
        running.
        """
        self._raise_if_run_in_progress()

        if remove_input:
            shutil.rmtree(self.input_path, ignore_errors=True)

        if remove_codebase:
            shutil.rmtree(self.codebase_path, ignore_errors=True)

        if remove_output:
            shutil.rmtree(self.output_path, ignore_errors=True)

        shutil.rmtree(self.tmp_path, ignore_errors=True)
        self.setup_work_directory()

        self.is_archived = True
        self.save()

    def delete(self, *args, **kwargs):
        """
        Deletes the `work_directory` along all project-related data in the database.
        """
        self._raise_if_run_in_progress()

        shutil.rmtree(self.work_directory, ignore_errors=True)
        return super().delete(*args, **kwargs)

    def reset(self, keep_input=True):
        """
        Resets the project by deleting all related database objects and all work
        directories except the input directory—when the `keep_input` option is True.
        """
        self._raise_if_run_in_progress()

        relationships = [
            self.projecterrors,
            self.runs,
            self.discoveredpackages,
            self.codebaseresources,
        ]

        for relation in relationships:
            relation.all().delete()

        work_directories = [
            self.codebase_path,
            self.output_path,
            self.tmp_path,
        ]

        if not keep_input:
            work_directories.append(self.input_path)
            self.input_sources = {}

        self.extra_data = {}
        self.save()

        for path in work_directories:
            shutil.rmtree(path, ignore_errors=True)

        self.setup_work_directory()

    def _raise_if_run_in_progress(self):
        """
        Raises a `RunInProgressError` exception if one of the project related run is
        queued or running.
        """
        if self.runs.queued_or_running().exists():
            raise RunInProgressError(
                "Cannot execute this action until all associated pipeline runs are "
                "completed."
            )

    def setup_work_directory(self):
        """
        Creates all of the work_directory structure and skips if already existing.
        """
        for subdirectory in self.WORK_DIRECTORIES:
            Path(self.work_directory, subdirectory).mkdir(parents=True, exist_ok=True)

    @property
    def work_path(self):
        """
        Returns the `work_directory` as a Path instance.
        """
        return Path(self.work_directory)

    @property
    def input_path(self):
        """
        Returns the `input` directory as a Path instance.
        """
        return Path(self.work_path / "input")

    @property
    def output_path(self):
        """
        Returns the `output` directory as a Path instance.
        """
        return Path(self.work_path / "output")

    @property
    def codebase_path(self):
        """
        Returns the `codebase` directory as a Path instance.
        """
        return Path(self.work_path / "codebase")

    @property
    def tmp_path(self):
        """
        Returns the `tmp` directory as a Path instance.
        """
        return Path(self.work_path / "tmp")

    def clear_tmp_directory(self):
        """
        Deletes the whole content of the tmp/ directory.
        This is called at the end of each pipeline Run, and it doesn't store
        any content that might be needed for further processing in following
        pipeline Run.
        """
        shutil.rmtree(self.tmp_path, ignore_errors=True)
        self.tmp_path.mkdir(exist_ok=True)

    @property
    def input_sources_list(self):
        return [
            {"filename": filename, "source": source}
            for filename, source in self.input_sources.items()
        ]

    def inputs(self, pattern="**/*"):
        """
        Returns all files and directories path of the input/ directory matching
        a given `pattern`.
        The default `**/*` pattern means "this directory and all subdirectories,
        recursively".
        Use the `*` pattern to only list the root content.
        """
        return self.input_path.glob(pattern)

    @property
    def input_files(self):
        """
        Returns a list of files' relative paths in the input/ directory
        recursively.
        """
        return [
            str(path.relative_to(self.input_path))
            for path in self.inputs()
            if path.is_file()
        ]

    @staticmethod
    def get_root_content(directory):
        """
        Returns a list of all files and directories of a given `directory`.
        Only the first level children will be listed.
        """
        return [str(path.relative_to(directory)) for path in directory.glob("*")]

    @property
    def input_root(self):
        """
        Returns a list of all files and directories of the input/ directory.
        Only the first level children will be listed.
        """
        return self.get_root_content(self.input_path)

    @property
    def inputs_with_source(self):
        """
        Returns a list of inputs including the source, type, sha256, and size data.
        Returns the `missing_inputs` defined in the `input_sources` field but not
        available in the input/ directory.
        Only first level children will be listed.
        """
        input_path = self.input_path
        input_sources = dict(self.input_sources)

        inputs = []
        for path in input_path.glob("*"):
            inputs.append(
                {
                    "name": path.name,
                    "is_file": path.is_file(),
                    "size": path.stat().st_size,
                    **multi_checksums(path, ["sha256"]),
                    "source": input_sources.pop(path.name, "not_found"),
                }
            )

        missing_inputs = input_sources
        return inputs, missing_inputs

    @property
    def output_root(self):
        """
        Returns a list of all files and directories of the output/ directory.
        Only first level children will be listed.
        """
        return self.get_root_content(self.output_path)

    def get_output_file_path(self, name, extension):
        """
        Returns a crafted file path in the project output/ directory using
        given `name` and `extension`.
        The current date and time strings are added to the filename.

        This method ensures the proper setup of the work_directory in case of
        a manual wipe and re-creates the missing pieces of the directory structure.
        """
        from scanpipe.pipes import filename_now

        self.setup_work_directory()

        filename = f"{name}-{filename_now()}.{extension}"
        return self.output_path / filename

    def get_latest_output(self, filename):
        """
        Returns the latest output file with the "filename" prefix, for example
        "scancode-<timestamp>.json".
        """
        output_files = sorted(self.output_path.glob(f"*{filename}*.json"))
        if output_files:
            return output_files[-1]

    def walk_codebase_path(self):
        """
        Returns all files and directories path of the codebase/ directory recursively.
        """
        return self.codebase_path.rglob("*")

    @cached_property
    def can_add_input(self):
        """
        Returns True until one pipeline run has started to execute on the project.
        """
        return not self.runs.has_start_date().exists()

    def add_input_source(self, filename, source, save=False):
        """
        Adds given `filename` and `source` to the current project's `input_sources`
        field.
        """
        self.input_sources[filename] = source
        if save:
            self.save()

    def write_input_file(self, file_object):
        """
        Writes the provided `file_object` to the project's input/ directory.
        """
        filename = file_object.name
        file_path = Path(self.input_path / filename)

        with open(file_path, "wb+") as f:
            for chunk in file_object.chunks():
                f.write(chunk)

    def copy_input_from(self, input_location):
        """
        Copies the file at `input_location` to the current project's input/ directory.
        """
        from scanpipe.pipes.input import copy_inputs

        copy_inputs([input_location], self.input_path)

    def move_input_from(self, input_location):
        """
        Moves the file at `input_location` to the current project's input/ directory.
        """
        from scanpipe.pipes.input import move_inputs

        move_inputs([input_location], self.input_path)

    def add_downloads(self, downloads):
        """
        Moves the given `downloads` to the current project's input/ directory and
        adds the `input_source` for each entry.
        """
        for downloaded in downloads:
            self.move_input_from(downloaded.path)
            self.add_input_source(downloaded.filename, downloaded.uri)
        self.save()

    def add_uploads(self, uploads):
        """
        Writes the given `uploads` to the current project's input/ directory and
        adds the `input_source` for each entry.
        """
        for uploaded in uploads:
            self.write_input_file(uploaded)
            self.add_input_source(filename=uploaded.name, source="uploaded")
        self.save()

    def add_pipeline(self, pipeline_name, execute_now=False):
        """
        Creates a new Run instance with the provided `pipeline` on the current
        project.

        If `execute_now` is True, the pipeline task is created.
        on_commit() is used to postpone the task creation after the transaction is
        successfully committed.
        If there isn’t any active transactions, the callback will be executed
        immediately.
        """
        pipeline_class = scanpipe_app.pipelines.get(pipeline_name)
        run = Run.objects.create(
            project=self,
            pipeline_name=pipeline_name,
            description=pipeline_class.get_doc(),
        )
        if execute_now:
            transaction.on_commit(run.execute_task_async)
        return run

    def add_webhook_subscription(self, target_url):
        """
        Creates a new WebhookSubscription instance with the provided `target_url` for
        the current project.
        """
        return WebhookSubscription.objects.create(project=self, target_url=target_url)

    def get_next_run(self):
        """
        Returns the next non-executed Run instance assigned to current project.
        """
        with suppress(ObjectDoesNotExist):
            return self.runs.not_started().earliest("created_date")

    def get_latest_failed_run(self):
        """
        Returns the latest failed Run instance of the current project.
        """
        with suppress(ObjectDoesNotExist):
            return self.runs.failed().latest("created_date")

    def add_error(self, error, model, details=None):
        """
        Creates a "ProjectError" record from the provided `error` Exception for this
        project.
        The `model` attribute can be provided as a string or as a Model class.
        """
        if inspect.isclass(model):
            model = model.__name__

        traceback = ""
        if hasattr(error, "__traceback__"):
            traceback = "".join(format_tb(error.__traceback__))

        return ProjectError.objects.create(
            project=self,
            model=model,
            details=details or {},
            message=str(error),
            traceback=traceback,
        )

    def get_absolute_url(self):
        """
        Returns this project's details URL.
        """
        return reverse("project_detail", args=[self.uuid])

    @cached_property
    def resource_count(self):
        """
        Returns the number of resources related to this project.
        """
        return self.codebaseresources.count()

    @cached_property
    def file_count(self):
        """
        Returns the number of **file** resources related to this project.
        """
        return self.codebaseresources.files().count()

    @cached_property
    def file_in_package_count(self):
        """
        Returns the number of **file** resources **in a package** related to this
        project.
        """
        return self.codebaseresources.files().in_package().count()

    @cached_property
    def file_not_in_package_count(self):
        """
        Returns the number of **file** resources **not in a package** related to this
        project.
        """
        return self.codebaseresources.files().not_in_package().count()

    @cached_property
    def package_count(self):
        """
        Returns the number of packages related to this project.
        """
        return self.discoveredpackages.count()

    @cached_property
    def error_count(self):
        """
        Returns the number of errors related to this project.
        """
        return self.projecterrors.count()

    @cached_property
    def has_single_resource(self):
        """
        Return True if we only have a single CodebaseResource associated to this
        project, False otherwise.
        """
        return self.codebaseresources.count() == 1


class ProjectRelatedQuerySet(models.QuerySet):
    def project(self, project):
        return self.filter(project=project)


class ProjectRelatedModel(models.Model):
    """
    A base model for all models that are related to a Project.
    """

    project = models.ForeignKey(
        Project, related_name="%(class)ss", on_delete=models.CASCADE, editable=False
    )

    objects = ProjectRelatedQuerySet.as_manager()

    class Meta:
        abstract = True

    @classmethod
    def model_fields(cls):
        return [field.name for field in cls._meta.get_fields()]


class ProjectError(UUIDPKModel, ProjectRelatedModel):
    """
    Stores errors and§ exceptions raised during a pipeline run.
    """

    created_date = models.DateTimeField(auto_now_add=True, editable=False)
    model = models.CharField(max_length=100, help_text=_("Name of the model class."))
    details = models.JSONField(
        default=dict, blank=True, help_text=_("Data that caused the error.")
    )
    message = models.TextField(blank=True, help_text=_("Error message."))
    traceback = models.TextField(blank=True, help_text=_("Exception traceback."))

    class Meta:
        ordering = ["created_date"]

    def __str__(self):
        return f"[{self.pk}] {self.model}: {self.message}"


class SaveProjectErrorMixin:
    """
    Uses `SaveProjectErrorMixin` on a model to create a "ProjectError" entry
    from a raised exception during `save()` instead of stopping the analysis process.

    The creation of a "ProjectError" can be skipped providing False for the `save_error`
    argument. In that case, the error is not captured, it is re-raised.
    """

    def save(self, *args, save_error=True, capture_exception=True, **kwargs):
        try:
            super().save(*args, **kwargs)
        except Exception as error:
            if save_error:
                self.add_error(error)
            if not capture_exception:
                raise

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors += [*cls._check_project_field(**kwargs)]
        return errors

    @classmethod
    def _check_project_field(cls, **kwargs):
        """
        Checks if a `project` field is declared on the model.
        """

        fields = [f.name for f in cls._meta.local_fields]
        if "project" not in fields:
            return [
                checks.Error(
                    "'project' field is required when using SaveProjectErrorMixin.",
                    obj=cls,
                    id="scanpipe.models.E001",
                )
            ]

        return []

    def add_error(self, error):
        """
        Creates a "ProjectError" record from a given `error` Exception instance.
        """
        return self.project.add_error(
            error=error,
            model=self.__class__,
            details=model_to_dict(self),
        )

    def add_errors(self, errors):
        """
        Creates "ProjectError" records from a provided `errors` Exception list.
        """
        for error in errors:
            self.add_error(error)


class RunQuerySet(ProjectRelatedQuerySet):
    def not_started(self):
        """
        Not in the execution queue, no `task_id` assigned.
        """
        return self.no_exitcode().no_start_date().filter(task_id__isnull=True)

    def queued(self):
        """
        In the execution queue with a `task_id` assigned but not running yet.
        """
        return self.no_exitcode().no_start_date().filter(task_id__isnull=False)

    def running(self):
        """
        Running the pipeline execution.
        """
        return self.no_exitcode().has_start_date().filter(task_end_date__isnull=True)

    def executed(self):
        """
        Pipeline execution completed, includes both succeed and failed runs.
        """
        return self.filter(task_end_date__isnull=False)

    def succeed(self):
        """
        Pipeline execution completed with success.
        """
        return self.filter(task_exitcode=0)

    def failed(self):
        """
        Pipeline execution completed with failure.
        """
        return self.filter(task_exitcode__gt=0)

    def has_start_date(self):
        """
        Run has a `task_start_date` set. It can be running or executed.
        """
        return self.filter(task_start_date__isnull=False)

    def no_start_date(self):
        """
        Run has no `task_start_date` set.
        """
        return self.filter(task_start_date__isnull=True)

    def no_exitcode(self):
        """
        Run has no `task_exitcode` set.
        """
        return self.filter(task_exitcode__isnull=True)

    def queued_or_running(self):
        """
        Run is queued or currently running.
        """
        return self.filter(task_id__isnull=False, task_end_date__isnull=True)


class Run(UUIDPKModel, ProjectRelatedModel, AbstractTaskFieldsModel):
    """
    The Database representation of a pipeline execution.
    """

    pipeline_name = models.CharField(
        max_length=256,
        help_text=_("Identify a registered Pipeline class."),
    )
    created_date = models.DateTimeField(auto_now_add=True, db_index=True)
    scancodeio_version = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    log = models.TextField(blank=True, editable=False)

    objects = RunQuerySet.as_manager()

    class Meta:
        ordering = ["created_date"]

    def __str__(self):
        return f"{self.pipeline_name}"

    def execute_task_async(self):
        """
        Enqueues the pipeline execution task for an asynchronous execution.
        """
        run_pk = str(self.pk)

        # Bypass entirely the queue system and run the pipeline in the current thread.
        if not settings.SCANCODEIO_ASYNC:
            tasks.execute_pipeline_task(run_pk)
            return

        job = django_rq.enqueue(
            tasks.execute_pipeline_task,
            job_id=run_pk,
            run_pk=run_pk,
            on_failure=tasks.report_failure,
            job_timeout=settings.SCANCODEIO_TASK_TIMEOUT,
        )

        # In async mode, we want to set the status as "queued" **after** the job was
        # properly "enqueued".
        # In case the `django_rq.enqueue()` raise an exception (Redis server error),
        # we want to keep the Run status as "not started" rather than "queued".
        # Note that the Run will then be set as "running" at the start of
        # `execute_pipeline_task()` by calling the `set_task_started()`.
        # There's no need to call the following in synchronous single thread mode as
        # the run will be directly set as "running".
        self.set_task_queued()

        return job

    def sync_with_job(self):
        """
        Synchronise this Run instance with its related RQ Job.

        This is required when a Run gets out of sync with its Job, this can happen
        when the worker or one of its processes is killed, the Run status is not
        properly updated and may stay in a Queued or Running state forever.

        In case the Run is out of sync of its related Job, the Run status will be
        updated accordingly. When the run was in the queue, it will be enqueued again.
        """
        RunStatus = self.Status

        if settings.SCANCODEIO_ASYNC:
            job_status = self.job_status
        else:
            job_status = None

        if not job_status:
            if self.status == RunStatus.QUEUED:
                logger.info(
                    f"No Job found for QUEUED Run={self.task_id}. "
                    f"Enqueueing a new Job in the worker registery."
                )
                self.execute_task_async()

            elif self.status == RunStatus.RUNNING:
                logger.info(
                    f"No Job found for RUNNING Run={self.task_id}. "
                    f"Flagging this Run as STALE."
                )
                self.set_task_staled()

            return

        job_is_out_of_sync = any(
            [
                self.status == RunStatus.RUNNING and job_status != JobStatus.STARTED,
                self.status == RunStatus.QUEUED and job_status != JobStatus.QUEUED,
            ]
        )

        if job_is_out_of_sync:
            if job_status == JobStatus.STOPPED:
                logger.info(
                    f"Job found as {job_status} for RUNNING Run={self.task_id}. "
                    f"Flagging this Run as STOPPED."
                )
                self.set_task_stopped()

            elif job_status == JobStatus.FAILED:
                logger.info(
                    f"Job found as {job_status} for RUNNING Run={self.task_id}. "
                    f"Flagging this Run as FAILED."
                )
                self.set_task_ended(
                    exitcode=1,
                    output=f"Job was moved to the FailedJobRegistry during cleanup",
                )

            else:
                logger.info(
                    f"Job found as {job_status} for RUNNING Run={self.task_id}. "
                    f"Flagging this Run as STALE."
                )
                self.set_task_staled()

    def set_scancodeio_version(self):
        """
        Sets the current ScanCode.io version on the `Run.scancodeio_version` field.
        """
        if self.scancodeio_version:
            msg = f"Field scancodeio_version already set to {self.scancodeio_version}"
            raise ValueError(msg)
        self.scancodeio_version = scancodeio_version

    @property
    def pipeline_class(self):
        """
        Returns this Run pipeline_class.
        """
        return scanpipe_app.pipelines.get(self.pipeline_name)

    def make_pipeline_instance(self):
        """
        Returns a pipelines instance using this Run pipeline_class.
        """
        return self.pipeline_class(self)

    def append_to_log(self, message, save=False):
        """
        Appends the `message` string to the `log` field of this Run instance.
        """
        message = message.strip()
        if any(lf in message for lf in ("\n", "\r")):
            raise ValueError("message cannot contain line returns (either CR or LF).")

        self.log = self.log + message + "\n"
        if save:
            self.save()

    def send_project_subscriptions(self):
        """
        Triggers related project webhook subscriptions.
        """
        for subscription in self.project.webhooksubscriptions.all():
            subscription.send(pipeline_run=self)

    def profile(self, print_results=False):
        """
        Returns computed execution times for each step in the current Run.

        If `print_results` is provided, the results are printed to stdout.
        """
        if not self.task_succeeded:
            return

        pattern = re.compile(r"Step \[(?P<step>.+)] completed in (?P<time>.+) seconds")

        profiler = {}
        for line in self.log.split("\n"):
            match = pattern.search(line)
            if match:
                step, runtime = match.groups()
                profiler[step] = float(runtime)

        if not print_results or not profiler:
            return profiler

        total_runtime = sum(profiler.values())
        padding = max(len(name) for name in profiler.keys()) + 1
        for step, runtime in profiler.items():
            percent = round(runtime * 100 / total_runtime, 1)
            output_str = f"{step:{padding}} {runtime:>3} seconds {percent}%"
            if percent > 50:
                print("\033[41;37m" + output_str + "\033[m")
            else:
                print(output_str)


class CodebaseResourceQuerySet(ProjectRelatedQuerySet):
    def status(self, status=None):
        if status:
            return self.filter(status=status)
        return self.filter(~Q(status=""))

    def no_status(self):
        return self.filter(status="")

    def empty(self):
        return self.filter(Q(size__isnull=True) | Q(size=0))

    def in_package(self):
        return self.filter(discovered_packages__isnull=False)

    def not_in_package(self):
        return self.filter(discovered_packages__isnull=True)

    def files(self):
        return self.filter(type=self.model.Type.FILE)

    def directories(self):
        return self.filter(type=self.model.Type.DIRECTORY)

    def symlinks(self):
        return self.filter(type=self.model.Type.SYMLINK)

    def without_symlinks(self):
        return self.filter(~Q(type=self.model.Type.SYMLINK))

    def has_licenses(self):
        return self.filter(~Q(licenses=[]))

    def has_no_licenses(self):
        return self.filter(licenses=[])

    def has_package_data(self):
        return self.filter(package_data__isnull=False)

    def licenses_categories(self, categories):
        return self.json_list_contains(
            field_name="licenses",
            key="category",
            values=categories,
        )

    def unknown_license(self):
        return self.json_field_contains("license_expressions", "unknown")

    def json_field_contains(self, field_name, value):
        """
        Filters the QuerySet looking for the `value` string in the `field_name` JSON
        field converted into text.
        Empty values are excluded as there's no need to cast those into text.
        """
        return (
            self.filter(~Q(**{field_name: []}))
            .annotate(**{f"{field_name}_as_text": Cast(field_name, TextField())})
            .filter(**{f"{field_name}_as_text__contains": value})
        )

    def json_list_contains(self, field_name, key, values):
        """
        Filters on the JSONField `field_name` that stores a list of dictionaries.

        json_list_contains("licenses", "name", ["MIT License", "Apache License 2.0"])
        """
        lookups = Q()

        for value in values:
            lookups |= Q(**{f"{field_name}__contains": [{key: value}]})

        return self.filter(lookups)


class ScanFieldsModelMixin(models.Model):
    """
    Fields returned by the ScanCode-toolkit scans.
    """

    copyrights = models.JSONField(
        blank=True,
        default=list,
        help_text=_(
            "List of detected copyright statements (and related detection details)."
        ),
    )
    holders = models.JSONField(
        blank=True,
        default=list,
        help_text=_(
            "List of detected copyright holders (and related detection details)."
        ),
    )
    authors = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of detected authors (and related detection details)."),
    )
    licenses = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of license detection details."),
    )
    license_expressions = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of detected license expressions."),
    )
    emails = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of detected emails (and related detection details)."),
    )
    urls = models.JSONField(
        blank=True,
        default=list,
        help_text=_("List of detected URLs (and related detection details)."),
    )

    class Meta:
        abstract = True

    @classmethod
    def scan_fields(cls):
        return [field.name for field in ScanFieldsModelMixin._meta.get_fields()]

    def set_scan_results(self, scan_results, save=False):
        """
        Sets the values of the current instance's scan-related fields using
        `scan_results`.
        """
        scan_fields = self.scan_fields()
        for field_name, value in scan_results.items():
            if value and field_name in scan_fields:
                setattr(self, field_name, value)

        if save:
            self.save()

    def copy_scan_results(self, from_instance, save=False):
        """
        Copies the scan-related fields values from `from_instance`to the current
        instance.
        """
        for field_name in self.scan_fields():
            value_from_instance = getattr(from_instance, field_name)
            setattr(self, field_name, value_from_instance)

        if save:
            self.save()


class CodebaseResource(
    ProjectRelatedModel,
    ScanFieldsModelMixin,
    ExtraDataFieldMixin,
    SaveProjectErrorMixin,
    AbstractResource,
):
    """
    A project Codebase Resources are records of its code files and directories.
    Each record is identified by its path under the project workspace.
    """

    rootfs_path = models.CharField(
        max_length=2000,
        blank=True,
        help_text=_(
            "Path relative to some root filesystem root directory. "
            "Useful when working on disk images, docker images, and VM images."
            'Eg.: "/usr/bin/bash" for a path of "tarball-extract/rootfs/usr/bin/bash"'
        ),
    )
    status = models.CharField(
        blank=True,
        max_length=30,
        help_text=_("Analysis status for this resource."),
    )
    tag = models.CharField(
        blank=True,
        max_length=50,
    )

    class Type(models.TextChoices):
        """
        List of CodebaseResource types.
        """

        FILE = "file"
        DIRECTORY = "directory"
        SYMLINK = "symlink"

    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        help_text=_(
            "Type of this resource as one of: {}".format(", ".join(Type.values))
        ),
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("File or directory name of this resource with its extension."),
    )
    extension = models.CharField(
        max_length=100,
        blank=True,
        help_text=_(
            "File extension for this resource (directories do not have an extension)."
        ),
    )
    programming_language = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Programming language of this resource if this is a code file."),
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text=_(
            "MIME type (aka. media type) for this resource. "
            "See https://en.wikipedia.org/wiki/Media_type"
        ),
    )
    file_type = models.CharField(
        max_length=1024,
        blank=True,
        help_text=_("Descriptive file type for this resource."),
    )
    is_binary = models.BooleanField(default=False)
    is_text = models.BooleanField(default=False)
    is_archive = models.BooleanField(default=False)
    is_key_file = models.BooleanField(default=False)
    is_media = models.BooleanField(default=False)

    class Compliance(models.TextChoices):
        """
        List of compliance alert values.
        """

        OK = "ok"
        WARNING = "warning"
        ERROR = "error"
        MISSING = "missing"

    compliance_alert = models.CharField(
        max_length=10,
        blank=True,
        choices=Compliance.choices,
        editable=False,
        help_text=_(
            "Indicates how the detected licenses in a codebase resource complies with "
            "provided policies."
        ),
    )

    package_data = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of Package data detected from this CodebaseResource"),
    )

    objects = CodebaseResourceQuerySet.as_manager()

    class Meta:
        unique_together = (("project", "path"),)
        ordering = ("project", "path")

    def __str__(self):
        return self.path

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        Stores the `licenses` field on creating this instance from the database value.
        The cached value is then used to detect changes on `save()`.
        """
        new = super().from_db(db, field_names, values)

        if "licenses" in field_names:
            new._loaded_licenses = values[field_names.index("licenses")]

        return new

    def save(self, codebase=None, *args, **kwargs):
        """
        Saves the current resource instance.
        Injects policies—if the feature is enabled—when the `licenses` field value is
        changed.

        `codebase` is not used in this context but required for compatibility
        with the commoncode.resource.Codebase class API.
        """
        if scanpipe_app.policies_enabled:
            loaded_licenses = getattr(self, "loaded_licenses", [])
            if self.licenses != loaded_licenses:
                self.inject_licenses_policy(scanpipe_app.license_policies_index)
                self.compliance_alert = self.compute_compliance_alert()

        super().save(*args, **kwargs)

    def inject_licenses_policy(self, policies_index):
        """
        Injects license policies from the `policies_index` into the `licenses` field.
        """
        for license_data in self.licenses:
            key = license_data.get("key")
            license_data["policy"] = policies_index.get(key, None)

    @property
    def location_path(self):
        """
        Returns the location of the resource as a Path instance.
        """
        # strip the leading / to allow joining this with the codebase_path
        path = Path(str(self.path).strip("/"))
        return self.project.codebase_path / path

    @property
    def location(self):
        """
        Returns the location of the resource as a string.
        """
        return str(self.location_path)

    @property
    def is_file(self):
        """
        Returns True, if the resource is a file.
        """
        return self.type == self.Type.FILE

    @property
    def is_dir(self):
        """
        Returns True, if the resource is a directory.
        """
        return self.type == self.Type.DIRECTORY

    @property
    def is_symlink(self):
        """
        Returns True, if the resource is a symlink.
        """
        return self.type == self.Type.SYMLINK

    def compute_compliance_alert(self):
        """
        Computes and returns the compliance_alert value from the `licenses` policies.
        """
        if not self.licenses:
            return ""

        ok = self.Compliance.OK
        error = self.Compliance.ERROR
        warning = self.Compliance.WARNING
        missing = self.Compliance.MISSING

        alerts = []
        for license_data in self.licenses:
            policy = license_data.get("policy")
            if policy:
                alerts.append(policy.get("compliance_alert") or ok)
            else:
                alerts.append(missing)

        if error in alerts:
            return error
        elif warning in alerts:
            return warning
        elif missing in alerts:
            return missing
        return ok

    @property
    def unique_license_expressions(self):
        """
        Returns the sorted set of unique license_expressions.
        """
        return sorted(set(self.license_expressions))

    def parent_path(self):
        """
        Return the parent path for this CodebaseResource or None.
        """
        return parent_directory(self.path, with_trail=False)

    def has_parent(self):
        """
        Return True if this CodebaseResource has a parent CodebaseResource or
        False otherwise.
        """
        parent_path = self.parent_path()
        if not parent_path:
            return False
        if self.project.codebaseresources.filter(path=parent_path).exists():
            return True
        return False

    def parent(self, codebase=None):
        """
        Return the parent CodebaseResource object for this CodebaseResource or
        None.

        `codebase` is not used in this context but required for compatibility
        with the commoncode.resource.Codebase class API.
        """
        parent_path = self.parent_path()
        return parent_path and self.project.codebaseresources.get(path=parent_path)

    def siblings(self, codebase=None):
        """
        Return a sequence of sibling Resource objects for this Resource
        or an empty sequence.

        `codebase` is not used in this context but required for compatibility
        with the commoncode.resource.Codebase class API.
        """
        if self.has_parent():
            return self.parent(codebase).children(codebase)
        return []

    def descendants(self):
        """
        Returns a QuerySet of descendant CodebaseResource objects using a
        database query on the current CodebaseResource `path`.
        The current CodebaseResource is not included.
        """
        return self.project.codebaseresources.filter(path__startswith=f"{self.path}/")

    def children(self, codebase=None):
        """
        Returns a QuerySet of direct children CodebaseResource objects using a
        database query on the current CodebaseResource `path`.

        Paths are returned in lower-cased sorted path order to reflect the
        behavior of the `commoncode.resource.Resource.children()`
        https://github.com/nexB/commoncode/blob/main/src/commoncode/resource.py

        `codebase` is not used in this context but required for compatibility
        with the commoncode.resource.VirtualCodebase class API.
        """
        exactly_one_sub_directory = "[^/]+$"
        children_regex = rf"^{self.path}/{exactly_one_sub_directory}"
        return (
            self.descendants()
            .filter(path__regex=children_regex)
            .order_by(Lower("path"))
        )

    def walk(self, topdown=True):
        """
        Returns all descendant Resources of the current Resource; does not include self.

        Traverses the tree top-down, depth-first if `topdown` is True; otherwise
        traverses the tree bottom-up.
        """
        for child in self.children().iterator():
            if topdown:
                yield child
            for subchild in child.walk(topdown=topdown):
                yield subchild
            if not topdown:
                yield child

    def get_absolute_url(self):
        return reverse("resource_detail", args=[self.project_id, self.pk])

    def get_raw_url(self):
        """
        Returns the URL to access the RAW content of the resource.
        """
        return reverse("resource_raw", args=[self.project_id, self.pk])

    @property
    def file_content(self):
        """
        Returns the content of the current Resource file using TextCode utilities
        for optimal compatibility.
        """
        from textcode.analysis import numbered_text_lines

        numbered_lines = numbered_text_lines(self.location)
        numbered_lines = self._regroup_numbered_lines(numbered_lines)

        # ScanCode-toolkit is not providing the "\n" suffix when reading binary files.
        # The following is a workaround until the issue is fixed in the toolkit.
        lines = (
            line if line.endswith("\n") else line + "\n" for _, line in numbered_lines
        )

        return "".join(lines)

    @staticmethod
    def _regroup_numbered_lines(numbered_lines):
        """
        Yields (line number, text) given an iterator of (line number, line) where
        all text for the same line number is grouped and returned as a single text.

        This is a workaround ScanCode-toolkit breaking down long lines and creating an
        artificially higher number of lines, see:
        https://github.com/nexB/scancode.io/issues/292#issuecomment-901766139
        """
        for line_number, lines_group in groupby(numbered_lines, key=itemgetter(0)):
            yield line_number, "".join(line for _, line in lines_group)

    def create_and_add_package(self, package_data):
        """
        Creates a DiscoveredPackage instance using the `package_data` and assigns
        it to the current CodebaseResource instance.

        Errors that may happen during the DiscoveredPackage creation are capture
        at this level, rather that in the DiscoveredPackage.create_from_data level,
        so resource data can be injected in the ProjectError record.
        """
        try:
            package = DiscoveredPackage.create_from_data(self.project, package_data)
        except Exception as error:
            self.project.add_error(
                error=error,
                model=DiscoveredPackage,
                details={
                    "codebase_resource_path": self.path,
                    "codebase_resource_pk": self.pk,
                    **package_data,
                },
            )
            return

        if package:
            self.discovered_packages.add(package)
            return package

    @property
    def for_packages(self):
        """
        Returns the list of all discovered packages associated to this resource.
        """
        return [str(package) for package in self.discovered_packages.all()]


class DiscoveredPackageQuerySet(PackageURLQuerySetMixin, ProjectRelatedQuerySet):
    pass


class DiscoveredPackage(
    ProjectRelatedModel,
    ExtraDataFieldMixin,
    SaveProjectErrorMixin,
    AbstractPackage,
):
    """
    A project's Discovered Packages are records of the system and application packages
    discovered in the code under analysis.
    Each record is identified by its Package URL.
    Package URL is a fundamental effort to create informative identifiers for software
    packages, such as Debian, RPM, npm, Maven, or PyPI packages.
    See https://github.com/package-url for more details.
    """

    codebase_resources = models.ManyToManyField(
        "CodebaseResource", related_name="discovered_packages"
    )
    missing_resources = models.JSONField(default=list, blank=True)
    modified_resources = models.JSONField(default=list, blank=True)
    dependencies = models.JSONField(
        default=list,
        blank=True,
        help_text=_("A list of dependencies for this package."),
    )
    package_uid = models.CharField(
        max_length=1024,
        blank=True,
        db_index=True,
        help_text=_("Unique identifier for this package."),
    )

    # `AbstractPackage` model overrides:
    keywords = models.JSONField(default=list, blank=True)
    source_packages = models.JSONField(default=list, blank=True)

    objects = DiscoveredPackageQuerySet.as_manager()

    class Meta:
        ordering = ["uuid"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "package_uid"],
                condition=~Q(package_uid=""),
                name="%(app_label)s_%(class)s_unique_package_uid_within_project",
            ),
        ]

    def __str__(self):
        return self.package_url or str(self.uuid)

    def get_absolute_url(self):
        return reverse("package_detail", args=[self.project_id, self.pk])

    @cached_property
    def resources(self):
        """
        Returns the assigned codebase_resources QuerySet as a list.
        """
        return list(self.codebase_resources.all())

    @property
    def purl(self):
        """
        Returns the Package URL.
        """
        return self.package_url

    @classmethod
    def purl_fields(cls):
        return PackageURL._fields

    @classmethod
    def extract_purl_data(cls, package_data):
        purl_data = {}

        for field_name in cls.purl_fields():
            value = package_data.get(field_name)
            if field_name == "qualifiers":
                value = normalize_qualifiers(value, encode=True)
            purl_data[field_name] = value or ""

        return purl_data

    @classmethod
    def create_from_data(cls, project, package_data):
        """
        Creates and returns a DiscoveredPackage for a `project` from the `package_data`.
        If one of the values of the required fields is not available, a "ProjectError"
        is created instead of a new DiscoveredPackage instance.
        """
        required_fields = ["type", "name"]
        missing_values = [
            field_name
            for field_name in required_fields
            if not package_data.get(field_name)
        ]

        if missing_values:
            message = (
                f"No values for the following required fields: "
                f"{', '.join(missing_values)}"
            )

            project.add_error(error=message, model=cls, details=package_data)
            return

        qualifiers = package_data.get("qualifiers")
        if qualifiers:
            package_data["qualifiers"] = normalize_qualifiers(qualifiers, encode=True)

        cleaned_package_data = {
            field_name: value
            for field_name, value in package_data.items()
            if field_name in DiscoveredPackage.model_fields() and value
        }

        discovered_package = cls(project=project, **cleaned_package_data)
        # Using save_error=False to not capture potential errors at this level but
        # rather in the CodebaseResource.create_and_add_package method so resource data
        # can be injected in the ProjectError record.
        discovered_package.save(save_error=False, capture_exception=False)
        return discovered_package

    def update_from_data(self, package_data, override=False):
        """
        Update this discovered package instance with the provided `package_data`.
        The `save()` is called only if at least one field was modified.
        """
        model_fields = DiscoveredPackage.model_fields()
        updated_fields = []

        for field_name, value in package_data.items():
            skip_reasons = [
                not value,
                field_name not in model_fields,
                field_name in self.purl_fields(),
            ]
            if any(skip_reasons):
                continue

            current_value = getattr(self, field_name, None)
            if not current_value or (current_value != value and override):
                setattr(self, field_name, value)
                updated_fields.append(field_name)

        if updated_fields:
            self.save()

        return updated_fields


class WebhookSubscription(UUIDPKModel, ProjectRelatedModel):
    target_url = models.URLField(_("Target URL"), max_length=1024)
    sent = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return str(self.uuid)

    def send(self, pipeline_run):
        """
        Sends this WebhookSubscription by POSTing an HTTP request on the `target_url`.
        """
        payload = {
            "project": {
                "uuid": self.project.uuid,
                "name": self.project.name,
                "input_sources": self.project.input_sources,
            },
            "run": {
                "uuid": pipeline_run.uuid,
                "pipeline_name": pipeline_run.pipeline_name,
                "status": pipeline_run.status,
                "scancodeio_version": pipeline_run.scancodeio_version,
            },
        }

        logger.info(f"Sending Webhook uuid={self.uuid}.")
        try:
            response = requests.post(
                url=self.target_url,
                data=json.dumps(payload, cls=DjangoJSONEncoder),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except requests.exceptions.RequestException as exception:
            logger.info(exception)
            return

        if response.status_code in (200, 201, 202):
            logger.info(f"Webhook uuid={self.uuid} sent and received.")
            self.sent = True
            self.save()
        else:
            logger.info(f"Webhook uuid={self.uuid} returned a {response.status_code}.")


@receiver(models.signals.post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Creates an API key token on user creation, using the signal system.
    """
    if created:
        Token.objects.create(user_id=instance.pk)

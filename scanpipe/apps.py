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
from importlib.machinery import SourceFileLoader
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import gettext_lazy as _

import saneyaml

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    import importlib_metadata

from scanpipe.pipelines import is_pipeline


class ScanPipeConfig(AppConfig):
    name = "scanpipe"
    verbose_name = _("ScanPipe")

    def __init__(self, app_name, app_module):
        super().__init__(app_name, app_module)

        # Mapping of registered pipeline names to pipeline classes.
        self._pipelines = {}
        self.license_policies_index = {}

        workspace_location = settings.SCANCODEIO_WORKSPACE_LOCATION
        self.workspace_path = Path(workspace_location).expanduser().resolve()

    def ready(self):
        self.load_pipelines()
        self.set_policies()

    def flag_stale_runs(self):
        """
        Flags the "staled" Runs.

        TODO: This is executed when the worker is starting too.
        We may only want to run this when the webserver is started (runserver or
        gunicorn wsgi, warning on multiple gunicorn workers)
        Another issue is that if the job process gets kill, but the server does not
        restart, flag_stale_runs is not called.
        """
        import django_rq
        from django_rq.utils import get_jobs

        run_model = self.get_model("Run")

        for run in run_model.objects.queued_or_running():
            job = get_jobs(queue=django_rq.get_queue(), job_ids=[str(run.pk)])
            # TODO: Check the job status and update when failed
            if not job:
                run.set_task_staled()

    def load_pipelines(self):
        """
        Loads pipelines from the "scancodeio_pipelines" entry point group and from the
        pipelines Python files found at `SCANCODEIO_PIPELINES_DIRS` locations.
        """
        entry_points = importlib_metadata.entry_points()

        # Ignore duplicated entries caused by duplicated paths in `sys.path`.
        pipeline_entry_points = set(entry_points.get("scancodeio_pipelines"))

        for entry_point in sorted(pipeline_entry_points):
            self.register_pipeline(name=entry_point.name, cls=entry_point.load())

        # Register user provided pipelines
        pipelines_dirs = getattr(settings, "SCANCODEIO_PIPELINES_DIRS", [])

        for pipelines_dir in pipelines_dirs:
            pipelines_path = Path(pipelines_dir).expanduser()

            if not pipelines_path.is_dir():
                raise ImproperlyConfigured(
                    f'The provided pipelines directory "{pipelines_dir}" in '
                    f"the SCANCODEIO_PIPELINES_DIRS setting is not available."
                )

            python_files = pipelines_path.rglob("*.py")
            for path in python_files:
                self.register_pipeline_from_file(path)

    def register_pipeline(self, name, cls):
        """
        Registers the provided `name` and `cls` as a valid pipeline.
        """
        if not is_pipeline(cls):
            raise ImproperlyConfigured(
                f'The entry point "{cls}" is not a `Pipeline` subclass.'
            )

        if name in self._pipelines:
            raise ImproperlyConfigured(
                f'The pipeline name "{name}" is already registered.'
            )

        self._pipelines[name] = cls

    def register_pipeline_from_file(self, path):
        """
        Searches for a pipeline subclass in a given file `path` and registers it
        after being found.
        """
        module_name = inspect.getmodulename(path)
        module = SourceFileLoader(module_name, str(path)).load_module()

        def is_local_module_pipeline(obj):
            return is_pipeline(obj) and obj.__module__ == module_name

        pipeline_classes = inspect.getmembers(module, is_local_module_pipeline)

        if len(pipeline_classes) > 1:
            raise ImproperlyConfigured(
                f"Only one Pipeline class allowed per pipeline file: {path}."
            )

        elif pipeline_classes:
            pipeline_class = pipeline_classes[0][1]
            self.register_pipeline(name=module_name, cls=pipeline_class)

    @property
    def pipelines(self):
        return dict(self._pipelines)

    def get_pipeline_choices(self, include_blank=True):
        """
        Returns a `choices` list of tuple suitable for a Django ChoiceField.
        """
        choices = list(BLANK_CHOICE_DASH) if include_blank else []
        choices.extend([(name, name) for name in self.pipelines.keys()])
        return choices

    def set_policies(self):
        """
        Computes and sets the `license_policies` on the app instance.

        If the policies file is available but formatted properly or doesn't
        include the proper content, we want to raise an exception while the app
        is loading to warn sysadmins about the issue.
        """
        policies_file_location = getattr(settings, "SCANCODEIO_POLICIES_FILE", None)
        if policies_file_location:
            policies_file = Path(policies_file_location).expanduser()
            if policies_file.exists():
                policies = saneyaml.load(policies_file.read_text())
                license_policies = policies.get("license_policies", [])
                self.license_policies_index = self.get_policies_index(
                    policies_list=license_policies,
                    key="license_key",
                )

    @staticmethod
    def get_policies_index(policies_list, key):
        """
        Returns an inverted index by `key` of the `policies_list`.
        """
        return {policy.get(key): policy for policy in policies_list}

    @property
    def policies_enabled(self):
        """
        Returns True if the policies were provided and loaded properly.
        """
        return bool(self.license_policies_index)

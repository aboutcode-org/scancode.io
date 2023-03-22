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
import logging
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import gettext_lazy as _

import saneyaml

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    import importlib_metadata

from scanpipe.pipelines import is_pipeline

logger = logging.getLogger(__name__)
style = color_style()


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
        logger.debug(f"Read environment variables from {settings.ENV_FILE}")
        self.load_pipelines()
        self.set_policies()

        # In SYNC mode, the Run instances cleanup is triggered on app.ready()
        # only when the app is started through "runserver".
        # This cleanup is required if the a running pipeline process gets killed and
        # since KeyboardInterrupt cannot be captured to properly update the Run instance
        # before its running process death.
        # In ASYNC mode, the cleanup is handled by the "ScanCodeIOWorker" worker.
        if not settings.SCANCODEIO_ASYNC and "runserver" in sys.argv:
            self.sync_runs_and_jobs()

    def load_pipelines(self):
        """
        Load pipelines from the "scancodeio_pipelines" entry point group and from the
        pipelines Python files found at `SCANCODEIO_PIPELINES_DIRS` locations.
        """
        entry_points = importlib_metadata.entry_points()

        # Ignore duplicated entries caused by duplicated paths in `sys.path`.
        pipeline_entry_points = set(entry_points.get("scancodeio_pipelines"))

        for entry_point in sorted(pipeline_entry_points):
            self.register_pipeline(name=entry_point.name, cls=entry_point.load())

        pipelines_dirs = getattr(settings, "SCANCODEIO_PIPELINES_DIRS", [])
        logger.debug(f"Load user provided pipelines from {pipelines_dirs}")

        for pipelines_dir in pipelines_dirs:
            pipelines_path = Path(pipelines_dir).expanduser()

            if not pipelines_path.is_dir():
                raise ImproperlyConfigured(
                    f'The provided pipelines directory "{pipelines_dir}" in '
                    f"the SCANCODEIO_PIPELINES_DIRS setting is not available."
                )

            # Recursively yield all existing .py files from `pipelines_path`
            python_files = pipelines_path.rglob("*.py")
            for path in python_files:
                logger.debug(f"Look for pipeline class in file {path}")
                self.register_pipeline_from_file(path)

    def register_pipeline(self, name, cls):
        """Register the provided `name` and `cls` as a valid pipeline."""
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
        Search for a pipeline subclass in a given file `path` and registers it
        after being found.
        """
        module_name = inspect.getmodulename(path)
        module = SourceFileLoader(module_name, str(path)).load_module()

        def is_local_module_pipeline(obj):
            return is_pipeline(obj) and obj.__module__ == module_name

        pipeline_classes = inspect.getmembers(module, is_local_module_pipeline)

        if len(pipeline_classes) > 1:
            raise ImproperlyConfigured(
                f"Only one pipeline class allowed per pipeline file: {path}."
            )

        elif pipeline_classes:
            pipeline_class = pipeline_classes[0][1]
            msg = f"Register pipeline {module_name}.{pipeline_class.__name__}"
            logger.debug(style.SUCCESS(msg))
            self.register_pipeline(name=module_name, cls=pipeline_class)

        else:
            logger.debug(style.WARNING(f"No pipeline class found in {path}"))

    @property
    def pipelines(self):
        return dict(self._pipelines)

    def get_pipeline_choices(self, include_blank=True):
        """Return a `choices` list of tuple suitable for a Django ChoiceField."""
        choices = list(BLANK_CHOICE_DASH) if include_blank else []
        choices.extend([(name, name) for name in self.pipelines.keys()])
        return choices

    def set_policies(self):
        """
        Compute and sets the `license_policies` on the app instance.

        If the policies file is available but formatted properly or doesn't
        include the proper content, we want to raise an exception while the app
        is loading to warn sysadmins about the issue.
        """
        policies_file_location = getattr(settings, "SCANCODEIO_POLICIES_FILE", None)

        if policies_file_location:
            policies_file = Path(policies_file_location).expanduser()

            if policies_file.exists():
                logger.debug(style.SUCCESS(f"Load policies from {policies_file}"))
                policies = saneyaml.load(policies_file.read_text())
                license_policies = policies.get("license_policies", [])
                self.license_policies_index = self.get_policies_index(
                    policies_list=license_policies,
                    key="license_key",
                )

            else:
                logger.debug(style.WARNING("Policies file not found."))

    @staticmethod
    def get_policies_index(policies_list, key):
        """Return an inverted index by `key` of the `policies_list`."""
        return {policy.get(key): policy for policy in policies_list}

    @property
    def policies_enabled(self):
        """Return True if the policies were provided and loaded properly."""
        return bool(self.license_policies_index)

    def sync_runs_and_jobs(self):
        """Synchronize QUEUED and RUNNING Run with their related Jobs."""
        logger.info("Synchronizing QUEUED and RUNNING Run with their related Jobs...")

        run_model = self.get_model("Run")
        queued_or_running = run_model.objects.queued_or_running()

        if queued_or_running:
            logger.info(f"{len(queued_or_running)} Run to synchronize:")
            for run in queued_or_running:
                run.sync_with_job()
        else:
            logger.info("No Run to synchronize.")

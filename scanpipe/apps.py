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

import importlib.util
import inspect
import logging
import sys
import warnings
from importlib.machinery import SourceFileLoader
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import color_style
from django.db.models import BLANK_CHOICE_DASH
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from licensedcode.models import load_licenses

from scanpipe.policies import load_policies_file

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
        self.policies = {}

        workspace_location = settings.SCANCODEIO_WORKSPACE_LOCATION
        self.workspace_path = Path(workspace_location).expanduser().resolve()

    def ready(self):
        logger.debug(f"Read environment variables from {settings.ENV_FILE}")
        self.load_pipelines()
        self.set_policies()

        # In SYNC mode, the Run instances cleanup is triggered on app.ready()
        # only when the app is started through "runserver".
        # This cleanup is required if a running pipeline process gets killed and
        # since KeyboardInterrupt cannot be captured to properly update the Run instance
        # before its running process death.
        # In ASYNC mode, the cleanup is handled by the "ScanCodeIOWorker" worker.
        if not settings.SCANCODEIO_ASYNC and "runserver" in sys.argv:
            warnings.filterwarnings(
                "ignore",
                message="Accessing the database during app initialization",
                category=RuntimeWarning,
                module="django",
            )
            self.sync_runs_and_jobs()

    def load_pipelines(self):
        """
        Load pipelines from the "scancodeio_pipelines" entry point group and from the
        pipelines Python files found at `SCANCODEIO_PIPELINES_DIRS` locations.
        """
        entry_points = importlib_metadata.entry_points()
        pipeline_entry_points = set(entry_points.select(group="scancodeio_pipelines"))

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

        loader = SourceFileLoader(module_name, str(path))
        spec = importlib.util.spec_from_loader(module_name, loader)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            raise ImportError(f"Could not load module from path: {path}")

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

    def get_pipeline_choices(self, include_blank=True, include_addon=True):
        """Return a `choices` list of tuple suitable for a Django ChoiceField."""
        pipeline_names = (
            name
            for name, cls in self.pipelines.items()
            if include_addon or not cls.is_addon
        )
        choices = list(BLANK_CHOICE_DASH) if include_blank else []
        choices.extend([(name, name) for name in pipeline_names])
        return choices

    @staticmethod
    def get_new_pipeline_name(pipeline_name):
        """Backward compatibility with old pipeline names."""
        pipeline_old_names_mapping = {
            "docker": "analyze_docker_image",
            "root_filesystems": "analyze_root_filesystem_or_vm_image",
            "docker_windows": "analyze_windows_docker_image",
            "inspect_manifest": "inspect_packages",
            "deploy_to_develop": "map_deploy_to_develop",
            "scan_package": "scan_single_package",
            "scan_codebase_packages": "inspect_packages",
            "collect_pygments_symbols": "collect_symbols_pygments",
            "collect_source_strings": "collect_strings_gettext",
            "collect_symbols": "collect_symbols_ctags",
            "collect_tree_sitter_symbols": "collect_symbols_tree_sitter",
        }
        if new_name := pipeline_old_names_mapping.get(pipeline_name):
            warnings.warn(
                f"Pipeline name {pipeline_name} is deprecated and will be "
                f"removed in a future release. Use {new_name} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return new_name
        return pipeline_name

    @staticmethod
    def extract_group_from_pipeline(pipeline):
        pipeline_name = pipeline
        groups = None

        if ":" in pipeline:
            pipeline_name, value = pipeline.split(":", maxsplit=1)
            groups = value.split(",") if value else []

        return pipeline_name, groups

    def get_scancode_licenses(self):
        """
        Load licenses-related information from the ScanCode-toolkit ``licensedcode``
        data and return a mapping of ``key`` to ``license`` objects.
        """
        return load_licenses()

    scancode_licenses = cached_property(get_scancode_licenses)

    def set_policies(self):
        """
        Set the global app policies on the app instance.

        If the policies file is available but not formatted properly or doesn't
        include the proper content, we want to raise an exception while the app
        is loading to warn system admins about the issue.
        """
        policies_file_setting = getattr(settings, "SCANCODEIO_POLICIES_FILE", None)
        if not policies_file_setting:
            return

        policies_file = Path(policies_file_setting).expanduser()
        if policies_file.exists():
            policies = load_policies_file(policies_file)
            logger.debug(style.SUCCESS(f"Loaded policies from {policies_file}"))
            self.policies = policies
        else:
            logger.debug(style.WARNING("Policies file not found."))

    def sync_runs_and_jobs(self):
        """Synchronize ``QUEUED`` and ``RUNNING`` Run with their related Jobs."""
        logger.info("Synchronizing QUEUED and RUNNING Run with their related Jobs...")

        run_model = self.get_model("Run")
        queued_or_running = run_model.objects.queued_or_running()

        if queued_or_running:
            logger.info(f"{len(queued_or_running)} Run to synchronize:")
            for run in queued_or_running:
                run.sync_with_job()
        else:
            logger.info("No Run to synchronize.")

    @property
    def site_url(self):
        if site_url := settings.SCANCODEIO_SITE_URL:
            return site_url.rstrip("/")

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

    def ready(self):
        self.load_pipelines()
        self.set_policies()

    def load_pipelines(self):
        """
        Load Pipelines from the "scancodeio_pipelines" entry point group and from the
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
            pipelines_path = Path(pipelines_dir)

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
        Register the provided `name` and `cls` as a valid pipeline.
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
        Search for a Pipeline subclass in the provided file `path` and register it
        when found.
        """
        module_name = path.stem
        module = SourceFileLoader(module_name, str(path)).load_module()
        pipeline_classes = inspect.getmembers(module, is_pipeline)

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
        Return a `choices` list of tuple suitable for a Django ChoiceField.
        """
        choices = list(BLANK_CHOICE_DASH) if include_blank else []
        choices.extend([(name, name) for name in self.pipelines.keys()])
        return choices

    def set_policies(self):
        """
        Compute and set the `license_policies` on the app instance.

        If a policies file is available but not under the proper format, or not
        including the proper content, we want to let an exception to be raised
        during the app loading to warn the sysadmin about the issue.
        """
        policies_file_location = getattr(settings, "SCANCODEIO_POLICIES_FILE", None)
        if policies_file_location:
            policies_file = Path(policies_file_location)
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
        Return an inverted index by `key` of the `policies_list`.
        """
        return {policy.get(key): policy for policy in policies_list}

    @property
    def policies_enabled(self):
        """
        Return True if the policies where provided and properly loaded.
        """
        return bool(self.license_policies_index)

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

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    import importlib_metadata

from scanpipe.pipelines import is_pipeline


class ScanPipeConfig(AppConfig):
    name = "scanpipe"
    verbose_name = _("ScanPipe")
    pipelines = {}

    def ready(self):
        self.load_pipelines()

    def load_pipelines(self):
        """
        Load Pipelines from the "scancodeio_pipelines" entry point group.
        """
        entry_points = importlib_metadata.entry_points()

        # Ignore duplicated entries caused by duplicated paths in `sys.path`.
        pipeline_entry_points = set(entry_points.get("scancodeio_pipelines"))

        for entry_point in pipeline_entry_points:
            pipeline_class = entry_point.load()
            self.register_pipeline(entry_point.name, pipeline_class)

    def register_pipeline(self, name, class_):
        """
        Register the provided `name` and `class_` as a valid pipeline.
        """
        if not is_pipeline(class_):
            raise ImproperlyConfigured(
                f'The entry point "{class_}" is not a `Pipeline` subclass.'
            )

        if name in self.pipelines:
            raise ImproperlyConfigured(
                f'The pipeline name "{name}" is already registered.'
            )

        self.pipelines[name] = class_

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

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ScanPipeConfig(AppConfig):
    name = "scanpipe"
    verbose_name = _("ScanPipe")
    pipelines = []

    def ready(self):
        """
        Load available Pipelines.
        """
        project_root = Path(__file__).parent.parent.absolute()
        pipelines_dir = project_root / "scanpipe" / "pipelines"
        dot_py_suffix = ".py"

        for child in pipelines_dir.iterdir():
            if child.name.endswith(dot_py_suffix) and not child.name.startswith("_"):
                location = str(child.relative_to(project_root))
                name = child.name[: -len(dot_py_suffix)]
                self.pipelines.append((location, name))

    def is_valid(self, pipeline):
        """
        Return True if the pipeline is valid and available.
        """
        if pipeline in [location for location, name in self.pipelines]:
            return True
        return False

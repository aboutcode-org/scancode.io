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

"""Collect and score npm package health information."""

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import npm_health


class NpmHealth(Pipeline):
    """Collect reusable npm package health metrics for one project PURL."""

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/"


    def validate_project_purl(self):
        """Validate and parse the project's versioned npm PURL."""
        self.package = npm_health.validate_npm_package_url(self.project.purl)

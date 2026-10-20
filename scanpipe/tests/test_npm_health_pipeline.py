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

"""Tests for the npm-health pipeline definition."""

from django.test import SimpleTestCase

from scanpipe.pipelines.npm_health import NpmHealth


class NpmHealthPipelineTest(SimpleTestCase):
    def test_pipeline_flags_and_results_url(self):
        self.assertFalse(NpmHealth.download_inputs)
        self.assertTrue(NpmHealth.is_addon)
        self.assertEqual("/project/{slug}/", NpmHealth.results_url)

    def test_pipeline_steps(self):
        self.assertEqual(
            [
                "validate_project_purl",
                "load_cached_snapshot",
                "fetch_package_metadata",
                "collect_package_metrics",
                "compute_package_health_score",
                "build_result_snapshot",
                "persist_results",
            ],
            [step.__name__ for step in NpmHealth.steps()],
        )

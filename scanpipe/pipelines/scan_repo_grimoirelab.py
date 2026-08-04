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

import subprocess
from datetime import date

from scancodeio.settings import GRIMOIRELAB_BINARY_FILE_PATTERN
from scancodeio.settings import GRIMOIRELAB_CODE_FILE_PATTERN
from scancodeio.settings import GRIMOIRELAB_DEVELOPER_CATEGORIES_THRESHOLDS
from scancodeio.settings import GRIMOIRELAB_ELEPHANT_THRESHOLD
from scancodeio.settings import GRIMOIRELAB_FROM_DATE
from scancodeio.settings import GRIMOIRELAB_METRICS_EXECUTABLE
from scancodeio.settings import GRIMOIRELAB_OPENSEARCH_INDEX
from scancodeio.settings import GRIMOIRELAB_OPENSEARCH_PASSWORD
from scancodeio.settings import GRIMOIRELAB_OPENSEARCH_URL
from scancodeio.settings import GRIMOIRELAB_OPENSEARCH_USERNAME
from scancodeio.settings import GRIMOIRELAB_PASSWORD
from scancodeio.settings import GRIMOIRELAB_PONY_THRESHOLD
from scancodeio.settings import GRIMOIRELAB_REPOSITORY_TIMEOUT
from scancodeio.settings import GRIMOIRELAB_URL
from scancodeio.settings import GRIMOIRELAB_USERNAME
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import run_command_safely


class ScanRepoGrimoirelab(Pipeline):
    """Run a GrimoireLab scan to extract repository metrics and health score."""

    results_url = "/project/{slug}/resources/?extra_data=grimoire_data"

    @classmethod
    def steps(cls):
        return (cls.collect_and_store_grimoire_metric,)

    def collect_and_store_grimoire_metric(self):
        for input_source in self.project.input_sources:
            repo_url = input_source["download_url"]
            metrics_output_path = self.project.get_output_file_path("metrics", "json")
            grimoirelab_to_date = date.today().isoformat()

            command_args = [
                GRIMOIRELAB_METRICS_EXECUTABLE,
                repo_url,
                "--grimoirelab-url",
                GRIMOIRELAB_URL,
                "--grimoirelab-user",
                GRIMOIRELAB_USERNAME,
                "--grimoirelab-password",
                GRIMOIRELAB_PASSWORD,
                "--opensearch-url",
                GRIMOIRELAB_OPENSEARCH_URL,
                "--opensearch-index",
                GRIMOIRELAB_OPENSEARCH_INDEX,
                "--opensearch-user",
                GRIMOIRELAB_OPENSEARCH_USERNAME,
                "--opensearch-password",
                GRIMOIRELAB_OPENSEARCH_PASSWORD,
                "--from-date",
                GRIMOIRELAB_FROM_DATE,
                "--to-date",
                grimoirelab_to_date,
                "--repository-timeout",
                GRIMOIRELAB_REPOSITORY_TIMEOUT,
                "--code-file-pattern",
                GRIMOIRELAB_CODE_FILE_PATTERN,
                "--binary-file-pattern",
                GRIMOIRELAB_BINARY_FILE_PATTERN,
                "--pony-threshold",
                GRIMOIRELAB_PONY_THRESHOLD,
                "--elephant-threshold",
                GRIMOIRELAB_ELEPHANT_THRESHOLD,
                "--dev-categories-thresholds",
                *GRIMOIRELAB_DEVELOPER_CATEGORIES_THRESHOLDS,
                "--output",
                str(metrics_output_path),
            ]

            try:
                run_command_safely(command_args=command_args)
                self.log(f"Metrics successfully saved to {metrics_output_path}")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"grimoirelab-metrics pipeline failed {e.returncode} for {repo_url}"
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError("grimoirelab-metrics pipeline timed out")

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

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import repo_health
from scanpipe.pipes.repo_health import GRIMOIRELAB_ECOSYSTEM
from scanpipe.pipes.repo_health import GRIMOIRELAB_METRICS_EXECUTABLE
from scanpipe.pipes.repo_health import GRIMOIRELAB_OPENSEARCH_INDEX
from scanpipe.pipes.repo_health import GRIMOIRELAB_OPENSEARCH_PASSWORD
from scanpipe.pipes.repo_health import GRIMOIRELAB_OPENSEARCH_URL
from scanpipe.pipes.repo_health import GRIMOIRELAB_OPENSEARCH_USERNAME
from scanpipe.pipes.repo_health import GRIMOIRELAB_PASSWORD
from scanpipe.pipes.repo_health import GRIMOIRELAB_PROJECT
from scanpipe.pipes.repo_health import GRIMOIRELAB_URL
from scanpipe.pipes.repo_health import GRIMOIRELAB_USERNAME


class ScanRepoHealth(Pipeline):
    """Run a Repo Health scan to extract repository metrics and health score."""

    results_url = "/project/{slug}/resources/?extra_data=grimoire_data"
    download_inputs = False

    @classmethod
    def steps(cls):
        return (
            cls.get_repo_url_input,
            cls.collect_and_store_grimoire_metric,
            cls.format_metrics_output,
        )

    @classmethod
    def get_availability(cls):
        if not (
            GRIMOIRELAB_METRICS_EXECUTABLE
            and GRIMOIRELAB_OPENSEARCH_INDEX
            and GRIMOIRELAB_OPENSEARCH_PASSWORD
            and GRIMOIRELAB_OPENSEARCH_URL
            and GRIMOIRELAB_OPENSEARCH_USERNAME
            and GRIMOIRELAB_PASSWORD
            and GRIMOIRELAB_URL
            and GRIMOIRELAB_USERNAME
            and GRIMOIRELAB_ECOSYSTEM
            and GRIMOIRELAB_PROJECT
        ):
            return "Grimoirelab is not configured."

    def get_repo_url_input(self):
        """Validate and extract the repository URL from the project's input sources"""
        self.repo_url = repo_health.get_repo_url_input(project=self.project)

    def collect_and_store_grimoire_metric(self):
        """
        Run the grimoirelab-metrics command against the input source.
        Save the generated metrics JSON to the project output directory.
        """
        self.metrics_output_path = repo_health.collect_and_store_grimoire_metric(
            project=self.project, repo_url=self.repo_url, logger=self.log
        )

    def format_metrics_output(self):
        """
        Format the GrimoireLab metrics output by extracting the repository URL,
        score, and metrics from the generated JSON and overwriting it with a
        simplified structure, and updating the project's extra data.
        """
        repo_health.format_metrics_output(
            project=self.project, metrics_output_path=self.metrics_output_path
        )

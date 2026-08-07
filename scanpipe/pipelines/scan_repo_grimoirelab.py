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
import json
import subprocess
import urllib.parse

from django.conf import settings

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import run_command_safely

GRIMOIRELAB_METRICS_EXECUTABLE = getattr(settings, "GRIMOIRELAB_METRICS_EXECUTABLE", "")
GRIMOIRELAB_OPENSEARCH_INDEX = getattr(settings, "GRIMOIRELAB_OPENSEARCH_INDEX", "")
GRIMOIRELAB_OPENSEARCH_PASSWORD = getattr(
    settings, "GRIMOIRELAB_OPENSEARCH_PASSWORD", ""
)
GRIMOIRELAB_OPENSEARCH_URL = getattr(settings, "GRIMOIRELAB_OPENSEARCH_URL", "")
GRIMOIRELAB_OPENSEARCH_USERNAME = getattr(
    settings, "GRIMOIRELAB_OPENSEARCH_USERNAME", ""
)
GRIMOIRELAB_PASSWORD = getattr(settings, "GRIMOIRELAB_PASSWORD", "")
GRIMOIRELAB_URL = getattr(settings, "GRIMOIRELAB_URL", "")
GRIMOIRELAB_USERNAME = getattr(settings, "GRIMOIRELAB_USERNAME", "")


class ScanRepoGrimoirelab(Pipeline):
    """Run a GrimoireLab scan to extract repository metrics and health score."""

    results_url = "/project/{slug}/resources/?extra_data=grimoire_data"
    download_inputs = False

    @classmethod
    def steps(cls):
        return (
            cls.collect_and_store_grimoire_metric,
            cls.format_metrics_output,
        )

    def collect_and_store_grimoire_metric(self):
        """
        Run the grimoirelab-metrics command against the input source.
        Save the generated metrics JSON to the project output directory.
        """
        if len(self.project.input_sources) != 1:
            raise ValueError("Expected exactly one input source")

        repo_url = self.project.input_sources[0]["download_url"]
        if not is_valid_vcs_url(repo_url):
            raise ValueError(
                "Invalid input source: the pipeline accepts only a valid repository URL"
            )

        repo_url = repo_url.replace("git://", "https://")
        self.metrics_output_path = self.project.get_output_file_path("metrics", "json")
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
            "--output",
            str(self.metrics_output_path),
        ]

        try:
            run_command_safely(command_args=command_args)
            self.log("GrimoireLab metrics pipeline completed successfully")
        except subprocess.SubprocessError:
            raise RuntimeError("Grimoirelab-metrics pipeline failed")
        except FileNotFoundError:
            raise FileNotFoundError(
                "Grimoirelab-metrics not found. "
                "Please ensure grimoirelab-metrics is correctly configured."
            )

    def format_metrics_output(self):
        """
        Format the GrimoireLab metrics output by extracting the repository URL,
        score, and metrics from the generated JSON and overwriting it with a
        simplified structure.
        """
        with open(self.metrics_output_path) as f:
            data = json.load(f)

        package = list(data["packages"].values())[0]

        repository = package["repository"]
        score = package["score"]
        metrics = package["metrics"]

        result = {
            "repository": repository,
            "npm_health_score": score,
            "metrics": metrics,
        }

        with open(self.metrics_output_path, "w") as f:
            json.dump(result, f)


def is_valid_vcs_url(url):
    """Determine whether the URL is a valid VCS repository URL."""
    if not isinstance(url, str) or not url:
        return False

    if any(char.isspace() for char in url):
        return False

    forbidden_chars = ["|", ";", "&", "`", "$(", ">", "<", "&&", "||"]
    if any(char in url for char in forbidden_chars):
        return False

    parsed = urllib.parse.urlparse(url)
    valid_schemes = {"https", "http", "git"}
    if parsed.scheme in valid_schemes and parsed.netloc:
        return True

    return False

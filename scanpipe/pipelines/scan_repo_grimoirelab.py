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
from scancodeio.settings import GRIMOIRELAB_TO_DATE
from scancodeio.settings import GRIMOIRELAB_URL
from scancodeio.settings import GRIMOIRELAB_USERNAME
from scanpipe.pipelines import Pipeline
from scanpipe.pipelines.metrics_model import npmModel


class ScanGrimoirelab(Pipeline):
    results_url = "/project/{slug}/resources/?extra_data=grimoire_data"

    @classmethod
    def steps(cls):
        return (
            cls.collect_grimoire_metric,
            cls.compute_and_store_metric_score,
        )

    def collect_grimoire_metric(self):
        metrics_output_path = self.project.get_output_file_path("metrics", "json")
        repo_url = "https://github.com/aboutcode-org/fetchcode.git"

        cmd = [
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
            GRIMOIRELAB_TO_DATE,
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
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            self.log(f"Metrics successfully saved to {metrics_output_path}")
            with open(metrics_output_path) as f:
                self.metrics = json.load(f)

        except subprocess.CalledProcessError as e:
            self.log(f"failed with exit code {e.returncode}")
            raise
        except FileNotFoundError:
            self.log(
                "Error: 'grimoirelab-metrics' command not found. Is it installed and on your PATH?"
            )
            raise

    def compute_and_store_metric_score(self):
        model = npmModel()
        probability = model.calculate_score(self.metrics)
        status = "Healthy" if probability >= 0.5 else "Unhealthy"

        self.log(f"Repository Health: {status}, Probability: {probability:.2%}")
        score_data = {
            "status": status,
            "probability": probability,
            "metrics": self.metrics,
        }

        score_output_path = self.project.get_output_file_path("results", "json")
        with open(score_output_path, "w") as f:
            json.dump(score_data, f, indent=2)

        return score_data

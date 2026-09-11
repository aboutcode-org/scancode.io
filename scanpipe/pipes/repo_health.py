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
from os import environ

from scanpipe.pipes import run_command_safely

GRIMOIRELAB_METRICS_EXECUTABLE = environ.get("GRIMOIRELAB_METRICS_EXECUTABLE", "")
GRIMOIRELAB_OPENSEARCH_INDEX = environ.get("GRIMOIRELAB_OPENSEARCH_INDEX", "")
GRIMOIRELAB_OPENSEARCH_PASSWORD = environ.get("GRIMOIRELAB_OPENSEARCH_PASSWORD", "")
GRIMOIRELAB_OPENSEARCH_URL = environ.get("GRIMOIRELAB_OPENSEARCH_URL", "")
GRIMOIRELAB_OPENSEARCH_USERNAME = environ.get("GRIMOIRELAB_OPENSEARCH_USERNAME", "")
GRIMOIRELAB_PASSWORD = environ.get("GRIMOIRELAB_PASSWORD", "")
GRIMOIRELAB_URL = environ.get("GRIMOIRELAB_URL", "")
GRIMOIRELAB_USERNAME = environ.get("GRIMOIRELAB_USERNAME", "")
GRIMOIRELAB_ECOSYSTEM = environ.get("GRIMOIRELAB_ECOSYSTEM", "")
GRIMOIRELAB_PROJECT = environ.get("GRIMOIRELAB_PROJECT", "")


def get_repo_url_input(project):
    """Validate and extract the repository URL from the project's input sources"""
    if len(project.input_sources) != 1:
        raise ValueError("Expected exactly one input source")

    repo_url = project.input_sources[0]["download_url"]
    if not is_valid_vcs_url(repo_url):
        raise ValueError(
            "Invalid input source: the pipeline accepts only a valid repository URL"
        )

    repo_url = repo_url.replace("git://", "https://")
    if not repo_url.endswith(".git"):
        repo_url += ".git"

    return repo_url


def collect_and_store_grimoire_metric(project, repo_url, logger=None):
    """
    Run the grimoirelab-metrics command against the input source.
    Save the generated metrics JSON to the project output directory.
    """
    metrics_output_path = project.get_output_file_path("metrics", "json")
    command_args = [
        GRIMOIRELAB_METRICS_EXECUTABLE,
        repo_url,
        "--grimoirelab-url",
        GRIMOIRELAB_URL,
        "--grimoirelab-user",
        GRIMOIRELAB_USERNAME,
        "--grimoirelab-password",
        GRIMOIRELAB_PASSWORD,
        "--grimoirelab-ecosystem",
        GRIMOIRELAB_ECOSYSTEM,
        "--grimoirelab-project",
        GRIMOIRELAB_PROJECT,
        "--opensearch-url",
        GRIMOIRELAB_OPENSEARCH_URL,
        "--opensearch-index",
        GRIMOIRELAB_OPENSEARCH_INDEX,
        "--opensearch-user",
        GRIMOIRELAB_OPENSEARCH_USERNAME,
        "--opensearch-password",
        GRIMOIRELAB_OPENSEARCH_PASSWORD,
        "--output",
        str(metrics_output_path),
    ]

    try:
        run_command_safely(command_args=command_args)
        logger("GrimoireLab metrics pipeline completed successfully")
        return metrics_output_path
    except subprocess.SubprocessError:
        raise RuntimeError("Grimoirelab-metrics client failure")
    except FileNotFoundError:
        raise FileNotFoundError(
            "Grimoirelab-metrics not found. "
            "Please ensure grimoirelab-metrics is correctly configured."
        )


def format_metrics_output(project, metrics_output_path):
    """
    Format the GrimoireLab metrics output by extracting the repository URL,
    score, and metrics from the generated JSON and overwriting it with a
    simplified structure, and updating the project's extra data.
    """
    if not metrics_output_path.exists():
        raise FileNotFoundError(
            "GrimoireLab client did not return a valid metrics JSON file"
        )

    with open(metrics_output_path) as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Invalid metrics JSON: Expected a JSON object.")

    package_data = data.get("packages")
    if not package_data or not isinstance(package_data, dict):
        raise ValueError(
            "Invalid metrics JSON: Missing or malformed 'packages' section."
        )

    packages = list(package_data.values())
    if not packages:
        raise ValueError("Invalid metrics JSON: 'packages' contains no data.")

    target_package = packages[0]
    repository = target_package.get("repository")
    score = target_package.get("score")
    metrics = target_package.get("metrics")

    if repository is None or score is None or metrics is None:
        raise ValueError(
            f"Invalid metrics JSON. missing or null field(s): "
            f"repository: {repository}, score: {score}, metrics: {metrics}"
        )

    result = {
        "repository": repository,
        "score": score,
        "metrics": metrics,
    }

    with open(metrics_output_path, "w") as f:
        json.dump(result, f)

    project.update_extra_data(result)


def is_valid_vcs_url(url):
    """Determine whether the URL string has the expected syntax of a VCS repository."""
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

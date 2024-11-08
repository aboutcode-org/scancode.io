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


import logging
import shutil
import tempfile
import textwrap
from pathlib import Path
from urllib.parse import urljoin

import requests
from git import Repo
from packageurl import PackageURL

from aboutcode import hashid
from scancodeio import VERSION
from scancodeio import settings
from scanpipe.pipes.output import JSONResultsGenerator

logger = logging.getLogger(__name__)


def is_configured():
    """Return True if the required FederatedCode settings have been set."""
    if all(
        [
            settings.FEDERATEDCODE_GIT_ACCOUNT_URL,
            settings.FEDERATEDCODE_GIT_SERVICE_TOKEN,
            settings.FEDERATEDCODE_GIT_SERVICE_EMAIL,
            settings.FEDERATEDCODE_GIT_SERVICE_NAME,
        ]
    ):
        return True
    return False


def is_available():
    """Return True if the configured Git account is available."""
    if not is_configured():
        return False

    try:
        response = requests.head(settings.FEDERATEDCODE_GIT_ACCOUNT_URL, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as request_exception:
        logger.debug(f"FederatedCode is_available() error: {request_exception}")
        return False

    return response.status_code == requests.codes.ok


def get_package_repository(project_purl, logger=None):
    """Return the Git repository URL and scan path for a given package."""
    project_package_url = PackageURL.from_string(project_purl)

    git_account_url = f'{settings.FEDERATEDCODE_GIT_ACCOUNT_URL.rstrip("/")}/'
    package_base_dir = hashid.get_package_base_dir(purl=project_purl)
    package_repo_name = package_base_dir.parts[0]

    package_scan_path = (
        package_base_dir / project_package_url.version / "scancodeio.json"
    )
    package_git_repo_url = urljoin(git_account_url, f"{package_repo_name}.git")

    return package_git_repo_url, package_scan_path


def check_federatedcode_eligibility(project):
    """
    Check if the project fulfills the following criteria for
    pushing the project result to FederatedCode.

    Criteria:
        - FederatedCode is configured and available.
        - All pipelines have completed successfully.
        - Source is a download_url.
        - Must have ``project_purl`` with version.
    """
    if not is_configured():
        raise Exception("FederatedCode is not configured.")

    if not is_available():
        raise Exception("FederatedCode Git account is not available.")

    all_executed_pipeline_successful = all(
        run.task_succeeded for run in project.runs.executed()
    )

    source_is_download_url = any(
        source.download_url for source in project.inputsources.all()
    )

    if not all_executed_pipeline_successful:
        raise Exception("Make sure all the pipelines has completed successfully.")

    if not source_is_download_url:
        raise Exception("Project input should be download_url.")

    if not project.purl:
        raise Exception("Missing Project PURL.")

    project_package_url = PackageURL.from_string(project.purl)

    if not project_package_url.version:
        raise Exception("Missing version in Project PURL.")


def clone_repository(repo_url, logger=None):
    """Clone repository to local_path."""
    local_dir = tempfile.mkdtemp()

    authenticated_repo_url = repo_url.replace(
        "https://",
        f"https://{settings.FEDERATEDCODE_GIT_SERVICE_TOKEN}@",
    )
    repo = Repo.clone_from(url=authenticated_repo_url, to_path=local_dir, depth=1)

    repo.config_writer(config_level="repository").set_value(
        "user", "name", settings.FEDERATEDCODE_GIT_SERVICE_NAME
    ).release()

    repo.config_writer(config_level="repository").set_value(
        "user", "email", settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    ).release()

    return repo


def add_scan_result(project, repo, package_scan_file, logger=None):
    """Add package scan result to the local Git repository."""
    relative_scan_file_path = Path(*package_scan_file.parts[1:])

    write_to = Path(repo.working_dir) / relative_scan_file_path

    write_to.parent.mkdir(parents=True, exist_ok=True)
    results_generator = JSONResultsGenerator(project)
    with open(write_to, encoding="utf-8", mode="w") as file:
        for chunk in results_generator:
            file.write(chunk)

    return relative_scan_file_path


def commit_and_push_changes(
    repo, file_to_commit, purl, remote_name="origin", logger=None
):
    """Commit and push changes to remote repository."""
    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL

    change_type = "Add" if file_to_commit in repo.untracked_files else "Update"
    commit_message = f"""\
    {change_type} scan result for {purl}

    Tool: pkg:github/aboutcode-org/scancode.io@v{VERSION}
    Reference: https://{settings.ALLOWED_HOSTS[0]}/

    Signed-off-by: {author_name} <{author_email}>
    """

    default_branch = repo.active_branch.name

    repo.index.add([file_to_commit])
    repo.index.commit(textwrap.dedent(commit_message))
    repo.git.push(remote_name, default_branch, "--no-verify")


def delete_local_clone(repo):
    """Remove local clone."""
    shutil.rmtree(repo.working_dir)

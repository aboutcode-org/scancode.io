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
from urllib.parse import urlparse

from django.conf import settings

import requests
import saneyaml
from git import GitCommandError
from git import Repo
from packageurl import PackageURL

from aboutcode import hashid
from scancodeio import VERSION
from scanpipe.pipes.output import JSONResultsGenerator

logger = logging.getLogger(__name__)


def url_exists(url, timeout=5):
    """
    Check if the given `url` is reachable by doing head request.
    Return True if response status is 200, else False.
    """
    try:
        response = requests.head(url, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as request_exception:
        logger.debug(f"Error while checking {url}: {request_exception}")
        return False

    return response.status_code == requests.codes.ok


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


def create_federatedcode_working_dir():
    """Create temporary working dir for cloning federatedcode repositories."""
    return Path(tempfile.mkdtemp())


def is_available():
    """Return True if the configured Git account is available."""
    if not is_configured():
        return False

    return url_exists(settings.FEDERATEDCODE_GIT_ACCOUNT_URL)


def get_package_repository(project_purl, logger=None):
    """Return the Git repository URL and scan path for a given package."""
    project_package_url = PackageURL.from_string(project_purl)

    git_account_url = f"{settings.FEDERATEDCODE_GIT_ACCOUNT_URL}/"
    package_base_dir = hashid.get_package_base_dir(purl=project_purl)
    package_repo_name = package_base_dir.parts[0]

    package_scan_path = (
        package_base_dir / project_package_url.version / "scancodeio.json"
    )
    package_git_repo_url = urljoin(git_account_url, f"{package_repo_name}.git")

    return package_repo_name, package_git_repo_url, package_scan_path


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


def check_federatedcode_configured_and_available(logger=None):
    """
    Check if the criteria for pushing the results to FederatedCode
    is satisfied.

    Criteria:
        - FederatedCode is configured and available.
    """
    if not is_configured():
        raise Exception("FederatedCode is not configured.")

    if not is_available():
        raise Exception("FederatedCode Git account is not available.")

    if logger:
        logger("Federatedcode repositories are configured and available.")


def clone_repository(repo_url, clone_path, logger, shallow_clone=True):
    """Clone repository to clone_path."""
    logger(f"Cloning repository {repo_url}")

    authenticated_repo_url = repo_url.replace(
        "https://",
        f"https://{settings.FEDERATEDCODE_GIT_SERVICE_TOKEN}@",
    )
    clone_args = {
        "url": authenticated_repo_url,
        "to_path": clone_path,
    }
    if shallow_clone:
        clone_args["depth"] = 1

    repo = Repo.clone_from(**clone_args)
    repo.config_writer(config_level="repository").set_value(
        "user", "name", settings.FEDERATEDCODE_GIT_SERVICE_NAME
    ).release()
    repo.config_writer(config_level="repository").set_value(
        "user", "email", settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    ).release()

    return repo


def get_github_org(url):
    """Return org username from GitHub account URL."""
    github_account_url = urlparse(url)
    path_after_domain = github_account_url.path.lstrip("/")
    org_name = path_after_domain.split("/")[0]
    return org_name


def create_repository(repo_name, clone_path, logger, shallow_clone=True):
    """
    Create and initialize remote FederatedCode `repo_name` repository,
    perform local checkout, and return it.
    """
    account_url = f"{settings.FEDERATEDCODE_GIT_ACCOUNT_URL}/"
    repo_url = urljoin(account_url, repo_name)

    headers = {
        "Authorization": f"token {settings.FEDERATEDCODE_GIT_SERVICE_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    data = {
        "name": repo_name,
        "private": False,
        "auto_init": True,
        "CC-BY-4.0": "cc-by-4.0",
    }
    org_name = get_github_org(account_url)
    create_repo_api = f"https://api.github.com/orgs/{org_name}/repos"
    response = requests.post(
        create_repo_api,
        headers=headers,
        json=data,
        timeout=5,
    )
    response.raise_for_status()
    return clone_repository(
        repo_url=repo_url,
        clone_path=clone_path,
        shallow_clone=shallow_clone,
        logger=logger,
    )


def get_or_create_repository(repo_name, working_path, logger, shallow_clone=True):
    """
    Return local checkout of the FederatedCode `repo_name` repository.

    - If local checkout for `repo_name` already exists in `working_path`, return it.
    - If no local checkout exists but the remote repository `repo_name` exists,
        clone it locally and return the checkout.
    - If the remote repository does not exist, create and initialize `repo_name`
        repository, perform local checkout, and return it.
    """
    account_url = f"{settings.FEDERATEDCODE_GIT_ACCOUNT_URL}/"
    repo_url = urljoin(account_url, repo_name)
    clone_path = working_path / repo_name

    if clone_path.exists():
        return False, Repo(clone_path)
    if url_exists(repo_url):
        return False, clone_repository(
            repo_url=repo_url,
            clone_path=clone_path,
            logger=logger,
            shallow_clone=shallow_clone,
        )

    return True, create_repository(
        repo_name=repo_name,
        clone_path=clone_path,
        logger=logger,
        shallow_clone=shallow_clone,
    )


def add_scan_result(project, repo, package_scan_file, logger=None):
    """Add package scan result to the local Git repository."""
    relative_scan_file_path = Path(*package_scan_file.parts[1:])

    write_to = Path(repo.working_dir) / relative_scan_file_path

    write_to.parent.mkdir(parents=True, exist_ok=True)
    results_generator = JSONResultsGenerator(project)
    with open(write_to, encoding="utf-8", mode="w") as file:
        file.writelines(results_generator)

    return relative_scan_file_path


def push_changes(repo, remote_name="origin", branch_name=""):
    """Push changes to remote repository."""
    if not branch_name:
        branch_name = repo.active_branch.name
    repo.git.push(remote_name, branch_name, "--no-verify")


def commit_and_push_changes(
    repo,
    files_to_commit,
    commit_message=None,
    purls=None,
    remote_name="origin",
    logger=None,
):
    """
    Commit and push changes to remote repository.
    Returns True if changes are successfully pushed, False otherwise.
    """
    try:
        commit_changes(repo, files_to_commit, commit_message, purls, logger)
        push_changes(repo, remote_name)
    except GitCommandError as e:
        if "nothing to commit" in e.stdout.lower():
            logger("Nothing to commit, working tree clean.")
        else:
            logger(f"Error while committing change: {e}")
        return False
    return True


def commit_changes(
    repo,
    files_to_commit,
    commit_message=None,
    purls=None,
    mine_type="packageURL",
    tool_name="pkg:github/aboutcode-org/scancode.io",
    tool_version=VERSION,
    logger=None,
):
    """Commit changes in files to a remote repository."""
    if not files_to_commit:
        return

    if not commit_message:
        author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
        author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL

        purls = "\n".join(purls)
        commit_message = f"""\
        Add {mine_type} results for:
        {purls}

        Tool: {tool_name}@v{tool_version}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """

    repo.index.add(files_to_commit)
    repo.git.commit(
        m=textwrap.dedent(commit_message),
        allow_empty=False,
        no_verify=True,
    )


def delete_local_clone(repo):
    """Remove local clone."""
    shutil.rmtree(repo.working_dir)


def write_data_as_yaml(base_path, file_path, data):
    """
    Write the ``data`` as YAML to the ``file_path`` in the ``base_path`` root directory.
    Create directories in the path as needed.
    """
    write_to = Path(base_path) / Path(file_path)
    write_to.parent.mkdir(parents=True, exist_ok=True)
    with open(write_to, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))

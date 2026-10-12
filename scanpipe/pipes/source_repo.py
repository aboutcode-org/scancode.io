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
import os
from urllib.parse import urlparse

import requests
from packageurl.contrib import url2purl
from packageurl.contrib.purl2url import get_repo_download_url_by_package_type

from scanpipe.pipes import fetch
from scanpipe.pipes.utils import count_total_files

logger = logging.getLogger(__name__)

# Version tag prefixes to try, in order.
VERSION_TAG_PREFIXES = ["", "v", "V", "release-", "RELEASE-", "v-", "V-"]


def get_src_repo_download_url(repository_url, version):
    """Return a 2-tuple ``(download_url, warning)``."""
    if not repository_url:
        return None, "No source repository URL found in Cargo.toml."

    download_url = get_download_url(repository_url, version)
    if not download_url:
        return None, (
            "Not able to determine the source repository download URL from Cargo.toml."
        )

    return download_url, None


def download_src_repo(download_url):
    """Download the source repository archive and return its local path."""
    try:
        return fetch.fetch_url(url=download_url).path
    except (ValueError, requests.RequestException):
        logger.warning("Failed to download source repository: %s", download_url)
        return None


def get_download_url(homepage_url, version):
    """Return the source repository archive download URL for ``homepage_url``."""
    purl = url2purl.get_purl(homepage_url)

    if not purl:
        github_page_url = github_pages_to_repo(homepage_url)
        if github_page_url:
            purl = url2purl.get_purl(github_page_url)

    if not purl or purl.type not in ("github", "gitlab", "bitbucket"):
        return None

    # There is an issue where the version may have a different prefix.
    # For example, version can have the following prefixes:
    # ["v", "V", "release-", "RELEASE-", "v-", "V-"]
    clarified_version = clarify_version_tag(
        purl.type, purl.namespace, purl.name, version
    )
    if clarified_version:
        version = clarified_version

    return get_repo_download_url_by_package_type(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
        version=version,
    )


def clarify_version_tag(repo_type, namespace, name, version):
    """Use github/gitlab API to verify the version tag."""
    headers = {}
    if repo_type == "github":
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        url_base = f"https://api.github.com/repos/{namespace}/{name}/git/refs/tags/{{}}"
    elif repo_type == "gitlab":
        gitlab_token = os.environ.get("GITLAB_TOKEN")
        if gitlab_token:
            headers["PRIVATE-TOKEN"] = gitlab_token
        ns = namespace or ""
        project_path = f"{ns}/{name}".strip("/").replace("/", "%2F")
        url_base = (
            f"https://gitlab.com/api/v4/projects/{project_path}/repository/tags/{{}}"
        )
    else:
        return None

    for prefix in VERSION_TAG_PREFIXES:
        potential_tag = f"{prefix}{version}"
        url = url_base.format(potential_tag)

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException:
            continue
        if response.status_code == 200:
            return potential_tag
        if response.status_code in (403, 429):
            logger.warning(
                "Rate limited by %s API while checking tag %s.",
                repo_type,
                potential_tag,
            )
            return None

    return None


def github_pages_to_repo(url):
    """
    Try to map a GitHub Pages URL (https://{org}.github.io/{name}/)
    to its corresponding GitHub repository (https://github.com/{org}/{name}).
    Returns the repo URL if it exists, otherwise None.
    """
    parsed = urlparse(url)
    host = parsed.netloc
    parts = parsed.path.strip("/").split("/")

    # Only handle {org}.github.io/{name} pattern
    if not host.endswith(".github.io") or len(parts) < 1:
        return None

    org = host.replace(".github.io", "")
    name = parts[0]

    repo = f"https://github.com/{org}/{name}"

    # Verify existence via GitHub API
    api_url = f"https://api.github.com/repos/{org}/{name}"
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            return repo
    except requests.RequestException:
        return None

    return None


def update_comparison_summary(
    project,
    purl,
    devel_codebase_dir,
    src_repo_url,
    package_name,
    package_version,
    matched_count,
    mismatches,
):
    total_num_files = count_total_files(devel_codebase_dir)

    package = project.discoveredpackages.filter(
        name=package_name, version=package_version
    ).first()

    if package:
        summary_dict = {
            "input_source": str(purl),
            "compare_source_repository_url": str(src_repo_url),
            "total_matching_files": matched_count,
            "total_files_in_source_crate": total_num_files,
            "mismatches": mismatches,
        }
        package.update_extra_data({"comparison_summary": summary_dict})
    else:
        project.add_warning(
            description=(
                f"Could not find a discovered package matching {package_name} "
                f"{package_version} to attach the summary."
            ),
            model="source_repo",
        )

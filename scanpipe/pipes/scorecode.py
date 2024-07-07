# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

import logging
from collections import namedtuple
from urllib.parse import urlparse

from django.conf import settings

import requests
from ossf_scorecard.scorecard import GetScorecard

label = "ScoreCode"
logger = logging.getLogger(__name__)
session = requests.Session()


# Only SCORECARD_URL can be provided through setting
SCORECARD_API_URL = None
SCORECARD_URL = settings.SCORECARD_URL
if SCORECARD_URL:
    SCORECARD_API_URL = f'{SCORECARD_URL.rstrip("/")}/projects/'


def is_configured():
    """Return True if the required Scorecard settings have been set."""
    if SCORECARD_API_URL:
        return True
    return False


def is_available():
    """Return True if the configured Scorecard server is available."""
    if not is_configured():
        return False

    try:
        response = session.head(SCORECARD_API_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as request_exception:
        logger.debug(f"{label} is_available() error: {request_exception}")
        return False

    return response.status_code == requests.codes.ok


def fetch_scorecard_info(packages, logger):
    """
    Extract platform, org, and repo from a given GitHub or GitLab URL.

    Args
    ----
        url (str): The URL to parse.

    Returns
    -------
        RepoData: Named tuple containing 'platform', 'org', and 'repo' if the URL is
        valid, else None.

    """
    for package in packages:
        url = package.vcs_url
        repo_data = extract_repo_info(url)

        if repo_data:

            scorecard_data = GetScorecard(
                platform=repo_data.platform, org=repo_data.org, repo=repo_data.repo
            )

            logger.info(f"Fetching scorecard data for package: {scorecard_data}")


def extract_repo_info(url):
    """
    Extract platform, org, and repo from a given GitHub or GitLab URL.

    Args:
        url (str): The URL to parse.

    Returns
    -------
        RepoData: Named tuple containing 'platform', 'org', and 'repo' if the URL is
        valid, else None.

    """
    RepoData = namedtuple("RepoData", ["platform", "org", "repo"])

    parsed_url = urlparse(url)
    hostname = parsed_url.hostname

    if not hostname:
        return None

    if "github.com" in hostname:
        platform = "github"
    elif "gitlab.com" in hostname:
        platform = "gitlab"
    else:
        return None

    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) < 2:
        return None

    org = path_parts[0]
    repo = path_parts[1]

    return RepoData(platform=platform, org=org, repo=repo)

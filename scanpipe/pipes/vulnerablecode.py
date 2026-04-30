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

from django.conf import settings

import requests

label = "VulnerableCode"
logger = logging.getLogger(__name__)
session = requests.Session()


# Only VULNERABLECODE_URL can be provided through setting
VULNERABLECODE_API_URL = None
VULNERABLECODE_URL = settings.VULNERABLECODE_URL
if VULNERABLECODE_URL:
    VULNERABLECODE_API_URL = f"{VULNERABLECODE_URL.rstrip('/')}/api/v3"

# Basic Authentication
VULNERABLECODE_USER = settings.VULNERABLECODE_USER
VULNERABLECODE_PASSWORD = settings.VULNERABLECODE_PASSWORD
basic_auth_enabled = VULNERABLECODE_USER and VULNERABLECODE_PASSWORD
if basic_auth_enabled:
    session.auth = (VULNERABLECODE_USER, VULNERABLECODE_PASSWORD)

# Authentication with single API key
VULNERABLECODE_API_KEY = settings.VULNERABLECODE_API_KEY
if VULNERABLECODE_API_KEY:
    session.headers.update({"Authorization": f"Token {VULNERABLECODE_API_KEY}"})


def is_configured():
    """Return True if the required VulnerableCode settings have been set."""
    if VULNERABLECODE_API_URL:
        return True
    return False


def is_available():
    """Return True if the configured VulnerableCode server is available."""
    if not is_configured():
        return False

    try:
        response = session.head(VULNERABLECODE_API_URL, allow_redirects=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as request_exception:
        logger.debug(f"{label} is_available() error: {request_exception}")
        return False

    return response.status_code == requests.codes.ok


def chunked(iterable, chunk_size):
    """
    Break an `iterable` into lists of `chunk_size` length.

    >>> list(chunked([1, 2, 3, 4, 5], 2))
    [[1, 2], [3, 4], [5]]
    >>> list(chunked([1, 2, 3, 4, 5], 3))
    [[1, 2, 3], [4, 5]]
    """
    for index in range(0, len(iterable), chunk_size):
        end = index + chunk_size
        yield iterable[index:end]


def get_purls(packages):
    """Return the PURLs for the given list of `packages`."""
    return [package_url for package in packages if (package_url := package.package_url)]


def request_post(
    url,
    data,
    timeout=None,
):
    """Send a POST request with `data` as JSON to `url` and return the response."""
    try:
        response = session.post(url, json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"{label} [Exception] {exception}")


def bulk_search_by_purl(
    purls,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """Bulk search of vulnerabilities using the provided list of `purls`."""
    url = f"{api_url.rstrip('/')}/packages"

    data = {
        "purls": purls,
        "details": True,
    }

    logger.debug(f"VulnerableCode: url={url} purls_count={len(purls)}")
    return request_post(url, data, timeout)


def filter_vulnerabilities(vulnerabilities, ignore_set):
    """Filter out vulnerabilities based on a list of ignored IDs and aliases."""
    return [
        vulnerability
        for vulnerability in vulnerabilities
        if vulnerability.get("advisory_id") not in ignore_set
        and not any(alias in ignore_set for alias in vulnerability.get("aliases", []))
    ]


def fetch_vulnerabilities(
    packages, chunk_size=1000, logger=logger.info, ignore_set=None
):
    """
    Fetch and store vulnerabilities for each provided `packages`.
    The PURLs are used for the lookups in batch of `chunk_size` per request.
    """
    vulnerabilities_by_purl = {}

    for purls_batch in chunked(get_purls(packages), chunk_size):
        # Add support for pagination
        #  {'count': 17, 'next': None, 'previous': None, 'results': [....]
        response_data = bulk_search_by_purl(purls_batch)
        for vulnerability_data in response_data["results"]:
            purl = vulnerability_data["purl"]
            vulnerabilities_by_purl[purl] = vulnerability_data

    unsaved_objects = []
    for package in packages:
        if package_data := vulnerabilities_by_purl.get(package.package_url):
            affected_by = package_data.get("affected_by_vulnerabilities", [])

            if ignore_set and affected_by:
                affected_by = filter_vulnerabilities(affected_by, ignore_set)

            if affected_by:
                package.affected_by_vulnerabilities = affected_by
                unsaved_objects.append(package)

    if unsaved_objects:
        model_class = unsaved_objects[0].__class__
        model_class.objects.bulk_update(
            objs=unsaved_objects,
            fields=["affected_by_vulnerabilities"],
            batch_size=1000,
        )
        logger(
            f"{len(unsaved_objects)} {model_class._meta.verbose_name_plural} updated "
            f"with vulnerability data."
        )

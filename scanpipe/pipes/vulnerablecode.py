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
    VULNERABLECODE_API_URL = f"{VULNERABLECODE_URL}/api/"

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
        response = session.head(VULNERABLECODE_API_URL)
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


def request_get(
    url,
    payload=None,
    timeout=None,
):
    """Wrap the HTTP request calls on the API."""
    if not url:
        return

    params = {"format": "json"}
    if payload:
        params.update(payload)

    logger.debug(f"{label}: url={url} params={params}")
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"{label} [Exception] {exception}")


def request_post(
    url,
    data,
    timeout=None,
):
    try:
        response = session.post(url, json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"{label} [Exception] {exception}")


def _get_vulnerabilities(
    url,
    field_name,
    field_value,
    timeout=None,
):
    """Get the list of vulnerabilities."""
    payload = {field_name: field_value}

    response = request_get(url=url, payload=payload, timeout=timeout)
    if response and response.get("count"):
        results = response["results"]
        return results


def get_vulnerabilities_by_purl(
    purl,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """Get the list of vulnerabilities providing a package `purl`."""
    return _get_vulnerabilities(
        url=f"{api_url}packages/",
        field_name="purl",
        field_value=purl,
        timeout=timeout,
    )


def get_vulnerabilities_by_cpe(
    cpe,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """Get the list of vulnerabilities providing a package or component `cpe`."""
    return _get_vulnerabilities(
        url=f"{api_url}cpes/",
        field_name="cpe",
        field_value=cpe,
        timeout=timeout,
    )


def bulk_search_by_purl(
    purls,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """Bulk search of vulnerabilities using the provided list of `purls`."""
    url = f"{api_url}packages/bulk_search"

    data = {
        "purls": purls,
        "vulnerabilities_only": True,
    }

    logger.debug(f"VulnerableCode: url={url} purls_count={len(purls)}")
    return request_post(url, data, timeout)


def bulk_search_by_cpes(
    cpes,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """Bulk search of vulnerabilities using the provided list of `cpes`."""
    url = f"{api_url}cpes/bulk_search"

    data = {
        "cpes": cpes,
    }

    logger.debug(f"VulnerableCode: url={url} cpes_count={len(cpes)}")
    return request_post(url, data, timeout)


def filter_vulnerabilities(vulnerabilities, ignore_set):
    """Filter out vulnerabilities based on a list of ignored IDs and aliases."""
    return [
        vulnerability
        for vulnerability in vulnerabilities
        if vulnerability.get("vulnerability_id") not in ignore_set
        and not any(alias in ignore_set for alias in vulnerability.get("aliases", []))
    ]


def fetch_vulnerabilities(
    packages, chunk_size=1000, logger=logger.info, ignore_set=None
):
    """
    Fetch and store vulnerabilities for each provided ``packages``.
    The PURLs are used for the lookups in batch of ``chunk_size`` per request.
    """
    vulnerabilities_by_purl = {}

    for purls_batch in chunked(get_purls(packages), chunk_size):
        response_data = bulk_search_by_purl(purls_batch)
        for vulnerability_data in response_data:
            vulnerabilities_by_purl[vulnerability_data["purl"]] = vulnerability_data

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

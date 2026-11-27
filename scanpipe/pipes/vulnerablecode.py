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
from collections import defaultdict

from django.conf import settings

import requests
from packageurl import PackageURL

from scanpipe.pipes import fetch

label = "VulnerableCode"
logger = logging.getLogger(__name__)
session = requests.Session()


# Only VULNERABLECODE_URL can be provided through setting
VULNERABLECODE_API_URL = None
VULNERABLECODE_URL = getattr(settings, "VULNERABLECODE_URL", "")
if VULNERABLECODE_URL:
    VULNERABLECODE_API_URL = f"{VULNERABLECODE_URL.rstrip('/')}/api/v3"

# Basic Authentication
VULNERABLECODE_USER = getattr(settings, "VULNERABLECODE_USER", "")
VULNERABLECODE_PASSWORD = getattr(settings, "VULNERABLECODE_PASSWORD", "")
basic_auth_enabled = VULNERABLECODE_USER and VULNERABLECODE_PASSWORD
if basic_auth_enabled:
    session.auth = (VULNERABLECODE_USER, VULNERABLECODE_PASSWORD)

# Authentication with single API key
VULNERABLECODE_API_KEY = getattr(settings, "VULNERABLECODE_API_KEY", "")
if VULNERABLECODE_API_KEY:
    session.headers.update({"Authorization": f"Token {VULNERABLECODE_API_KEY}"})

VULNERABLECODE_USER_AGENT = getattr(
    settings, "VULNERABLECODE_USER_AGENT", "VCIO_API_AGENT"
)
session.headers.update({"User-Agent": VULNERABLECODE_USER_AGENT})


# Package types where the package names are case-insensitive.
CASE_INSENSITIVE_NAME_TYPES = ("nuget",)


class VulnerableCodeError(Exception):
    """VulnerableCode returned an unexpected or incomplete response."""


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


def get_plain_purl(purl):
    """Return the `purl` string without its qualifiers and subpath."""
    package_url = PackageURL.from_string(purl)
    plain_package_url = PackageURL(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
    )
    return plain_package_url.to_string()


def get_purl_lookup_key(plain_purl):
    """
    Return the key of the `plain_purl` to match the PURLs of a VulnerableCode
    response: the names of the `CASE_INSENSITIVE_NAME_TYPES` packages are lowercased.
    """
    package_url = PackageURL.from_string(plain_purl)
    if package_url.type not in CASE_INSENSITIVE_NAME_TYPES:
        return plain_purl

    lowercase_name_package_url = package_url._replace(name=package_url.name.lower())
    return lowercase_name_package_url.to_string()


def get_packages_by_plain_purl(packages):
    """Return the `packages` that have a PURL, grouped by plain PURL."""
    packages_by_plain_purl = defaultdict(list)
    for package in packages:
        if package_url := package.package_url:
            packages_by_plain_purl[get_plain_purl(package_url)].append(package)
    return dict(packages_by_plain_purl)


def request_json(
    method,
    url,
    data=None,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """
    Send a `method` request with `data` as JSON to `url` and return the response.
    Only the URLs under `api_url` are requested, as the session carries credentials.
    """
    if not url.startswith(f"{api_url.rstrip('/')}/"):
        raise VulnerableCodeError(f"URL outside of the VulnerableCode API: {url}")

    response = session.request(method, url, json=data, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_all_results(
    method,
    url,
    data=None,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """
    Return the results of every page of the paginated response from `url`.
    The `next` pages are requested with the same `method` and `data`.
    """
    page_data = request_json(method, url, data, timeout, api_url)
    expected_count = page_data["count"]
    all_results = page_data["results"]

    # A page holds at least one result: the count bounds the number of requests.
    remaining_page_requests = expected_count
    while page_data["next"] and remaining_page_requests:
        next_url = fetch.get_api_link(page_data["next"], api_url)
        page_data = request_json(method, next_url, data, timeout, api_url)
        all_results.extend(page_data["results"])
        remaining_page_requests -= 1

    if page_data["next"] or len(all_results) != expected_count:
        raise VulnerableCodeError(
            f"Incomplete response from {url}: "
            f"{len(all_results)} results out of {expected_count}."
        )

    return all_results


def bulk_search_by_purl(
    purls,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """
    Bulk search of vulnerabilities using the provided list of `purls`.
    Return the matched packages of all pages, qualifiers and subpath are ignored.
    """
    url = f"{api_url.rstrip('/')}/packages"

    data = {
        "purls": purls,
        "details": True,
        "reachability": True,
        "ignore_qualifiers_subpath": True,
    }

    logger.debug(f"VulnerableCode: url={url} purls_count={len(purls)}")
    return get_all_results("POST", url, data, timeout, api_url)


def get_affected_by_vulnerabilities(
    package_data,
    timeout=None,
    api_url=VULNERABLECODE_API_URL,
):
    """
    Return the vulnerabilities affecting the `package_data` package.
    They are fetched from the `affected_by_vulnerabilities_url` when not provided
    inline, for packages affected by many vulnerabilities.
    """
    affected_by = package_data.get("affected_by_vulnerabilities")
    if affected_by is not None:
        return affected_by

    if affected_by_url := package_data.get("affected_by_vulnerabilities_url"):
        affected_by_url = fetch.get_api_link(affected_by_url, api_url)
        return get_all_results("GET", affected_by_url, timeout=timeout, api_url=api_url)

    raise VulnerableCodeError(f"No vulnerability data for {package_data['purl']}")


def get_vulnerabilities_by_plain_purl(plain_purls, chunk_size):
    """
    Return the vulnerabilities of each matched plain PURL from `plain_purls`, by
    `get_purl_lookup_key` of the plain PURL.
    The vulnerabilities of all the qualifiers and subpath variants of a plain PURL
    are merged, without duplicates.
    """
    vulnerabilities_by_plain_purl = defaultdict(dict)

    for purls_batch in chunked(plain_purls, chunk_size):
        requested_lookup_keys = {
            get_purl_lookup_key(plain_purl) for plain_purl in purls_batch
        }
        for package_data in bulk_search_by_purl(purls_batch):
            lookup_key = get_purl_lookup_key(get_plain_purl(package_data["purl"]))
            if lookup_key not in requested_lookup_keys:
                raise VulnerableCodeError(f"Unexpected PURL: {package_data['purl']}")

            vulnerabilities_by_uid = vulnerabilities_by_plain_purl[lookup_key]
            for vulnerability in get_affected_by_vulnerabilities(package_data):
                advisory_uid = vulnerability["advisory_uid"]
                vulnerabilities_by_uid.setdefault(advisory_uid, vulnerability)

    return {
        plain_purl: list(vulnerabilities_by_uid.values())
        for plain_purl, vulnerabilities_by_uid in vulnerabilities_by_plain_purl.items()
    }


def filter_vulnerabilities(vulnerabilities, ignore_set):
    """Filter out vulnerabilities based on a list of ignored IDs and aliases."""
    return [
        vulnerability
        for vulnerability in vulnerabilities
        if vulnerability.get("advisory_uid") not in ignore_set
        and vulnerability.get("advisory_id") not in ignore_set
        and not any(alias in ignore_set for alias in vulnerability.get("aliases", []))
    ]


def fetch_vulnerabilities(
    packages, chunk_size=1000, logger=logger.info, ignore_set=None
):
    """
    Fetch and store vulnerabilities for each provided `packages`.
    The PURLs, without qualifiers and subpath, are used for the lookups in batch of
    `chunk_size` per request.
    The vulnerabilities of every matched package are replaced, including with an
    empty list, only once all the lookups succeeded.
    """
    packages_by_plain_purl = get_packages_by_plain_purl(packages)
    vulnerabilities_by_plain_purl = get_vulnerabilities_by_plain_purl(
        plain_purls=list(packages_by_plain_purl),
        chunk_size=chunk_size,
    )

    unsaved_objects = []
    for plain_purl, plain_purl_packages in packages_by_plain_purl.items():
        affected_by = vulnerabilities_by_plain_purl.get(get_purl_lookup_key(plain_purl))
        if affected_by is None:
            continue

        if ignore_set:
            affected_by = filter_vulnerabilities(affected_by, ignore_set)

        for package in plain_purl_packages:
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

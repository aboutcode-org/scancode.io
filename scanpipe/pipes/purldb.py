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

from collections import defaultdict
import json
import logging
import time

from django.conf import settings

import requests
from packageurl import PackageURL
from univers.version_range import RANGE_CLASS_BY_SCHEMES
from univers.version_range import InvalidVersionRange

from scanpipe.pipes import flag
from scanpipe.pipes import LoopProgress

label = "PurlDB"
logger = logging.getLogger(__name__)
session = requests.Session()


# Only PURLDB_URL can be provided through setting
PURLDB_API_URL = None
PURLDB_URL = settings.PURLDB_URL
if PURLDB_URL:
    PURLDB_API_URL = f'{PURLDB_URL.rstrip("/")}/api/'

# Basic Authentication
PURLDB_USER = settings.PURLDB_USER
PURLDB_PASSWORD = settings.PURLDB_PASSWORD
basic_auth_enabled = PURLDB_USER and PURLDB_PASSWORD
if basic_auth_enabled:
    session.auth = (PURLDB_USER, PURLDB_PASSWORD)

# Authentication with single API key
PURLDB_API_KEY = settings.PURLDB_API_KEY
if PURLDB_API_KEY:
    session.headers.update({"Authorization": f"Token {PURLDB_API_KEY}"})

DEFAULT_TIMEOUT = 60


def is_configured():
    """Return True if the required PurlDB settings have been set."""
    if PURLDB_API_URL:
        return True
    return False


def is_available():
    """Return True if the configured PurlDB server is available."""
    if not is_configured():
        return False

    try:
        response = session.head(PURLDB_API_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as request_exception:
        logger.debug(f"{label} is_available() error: {request_exception}")
        return False

    return response.status_code == requests.codes.ok


def request_get(url, payload=None, timeout=DEFAULT_TIMEOUT):
    """Wrap the HTTP request calls on the API."""
    if not url:
        return

    params = {}
    if "format=json" not in url:
        params.update({"format": "json"})
    if payload:
        params.update(payload)

    logger.debug(f"{label}: url={url} params={params}")
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"{label} [Exception] {exception}")


def request_post(url, data, headers=None, files=None, timeout=DEFAULT_TIMEOUT):
    try:
        response = session.post(url, data=data, timeout=timeout, headers=headers, files=files)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"{label} [Exception] {exception}")


def collect_response_results(response, data, timeout=DEFAULT_TIMEOUT):
    """Return all results from a purldb API response."""
    results = []
    if response and response.get("count"):
        results.extend(response["results"])
        next_page = response.get("next")
        while next_page:
            response = request_post(url=next_page, data=data, timeout=timeout)
            if response and response.get("count"):
                results.extend(response["results"])
                next_page = response.get("next")
    return results


def match_packages(
    sha1_list,
    enhance_package_data=False,
    timeout=DEFAULT_TIMEOUT,
    api_url=PURLDB_API_URL,
):
    """
    Match a list of SHA1 in the PurlDB for package-type files.

    If `enhance_package_data` is True, then purldb will enhance Package data for
    matched Packages, if possible.
    """
    data = {
        "sha1": sha1_list,
        "enhance_package_data": enhance_package_data,
    }
    response = request_post(
        url=f"{api_url}packages/filter_by_checksums/", data=data, timeout=timeout
    )

    packages = collect_response_results(response, data=data, timeout=timeout)
    return packages


def match_resources(sha1_list, timeout=DEFAULT_TIMEOUT, api_url=PURLDB_API_URL):
    """Match a list of SHA1 in the PurlDB for resource files."""
    data = {"sha1": sha1_list}
    response = request_post(
        url=f"{api_url}resources/filter_by_checksums/", data=data, timeout=timeout
    )

    resources = collect_response_results(response, data=data, timeout=timeout)
    return resources


def match_directory(fingerprint, timeout=DEFAULT_TIMEOUT, api_url=PURLDB_API_URL):
    """
    Match directory content fingerprint in the PurlDB for a single directory
    resource.
    """
    payload = {"fingerprint": fingerprint}
    response = request_get(
        url=f"{api_url}approximate_directory_content_index/match/",
        payload=payload,
        timeout=timeout,
    )

    if response and len(response) > 0:
        return response


def submit_purls(packages, timeout=DEFAULT_TIMEOUT, api_url=PURLDB_API_URL):
    """
    Submit list of dict where each dict has either resolved PURL i.e. PURL with
    version or version-less PURL along with vers range to PurlDB for indexing.
    """
    payload = {"packages": packages}
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload)

    response = request_post(
        url=f"{api_url}packages/index_packages/",
        data=data,
        timeout=timeout,
        headers=headers,
    )

    return response


def feed_purldb(packages, chunk_size, logger=logger.info):
    """Feed PurlDB with list of PURLs for indexing."""
    if not is_available():
        raise Exception("PurlDB is not available.")

    if not packages:
        logger("No PURLs found. Skipping.")
        return

    package_batches = [
        packages[i : i + chunk_size] for i in range(0, len(packages), chunk_size)
    ]

    batches_count = len(package_batches)
    queued_packages_count = 0
    unqueued_packages_count = 0
    unsupported_packages_count = 0
    unsupported_vers_count = 0

    progress = LoopProgress(batches_count, logger)

    for batch in progress.iter(package_batches):
        if response := submit_purls(packages=batch):
            queued_packages_count += response.get("queued_packages_count", 0)
            unqueued_packages_count += response.get("unqueued_packages_count", 0)
            unsupported_packages_count += response.get("unsupported_packages_count", 0)
            unsupported_vers_count += response.get("unsupported_vers_count", 0)

    if queued_packages_count > 0:
        logger(
            f"Successfully queued {queued_packages_count:,d} "
            f"PURLs for indexing in PurlDB"
        )

    if unqueued_packages_count > 0:
        logger(
            f"{unqueued_packages_count:,d} PURLs were already "
            f"present in PurlDB index queue"
        )

    if unsupported_packages_count > 0:
        logger(f"Couldn't index {unsupported_packages_count:,d} unsupported PURLs")

    if unsupported_vers_count > 0:
        logger(f"Couldn't index {unsupported_vers_count:,d} unsupported vers")


def get_unique_resolved_purls(project):
    """Return PURLs from project's resolved DiscoveredDependencies."""
    packages_resolved = project.discovereddependencies.filter(is_resolved=True)

    distinct_results = packages_resolved.values("type", "namespace", "name", "version")

    distinct_combinations = {tuple(item.values()) for item in distinct_results}
    return {str(PackageURL(*values)) for values in distinct_combinations}


def get_unique_unresolved_purls(project):
    """Return PURLs from project's unresolved DiscoveredDependencies."""
    packages_unresolved = project.discovereddependencies.filter(
        is_resolved=False
    ).exclude(extracted_requirement="*")

    distinct_unresolved_results = packages_unresolved.values(
        "type", "namespace", "name", "extracted_requirement"
    )

    distinct_unresolved = {tuple(item.values()) for item in distinct_unresolved_results}

    packages = set()
    for item in distinct_unresolved:
        pkg_type, namespace, name, extracted_requirement = item
        if range_class := RANGE_CLASS_BY_SCHEMES.get(pkg_type):
            try:
                vers = range_class.from_native(extracted_requirement)
            except InvalidVersionRange:
                continue

            if not vers.constraints:
                continue

            purl = PackageURL(type=pkg_type, namespace=namespace, name=name)
            packages.add((str(purl), str(vers)))

    return packages


def populate_purldb_with_discovered_packages(project, logger=logger.info):
    """Add DiscoveredPackage to PurlDB."""
    discoveredpackages = project.discoveredpackages.all()
    packages = [{"purl": pkg.purl} for pkg in discoveredpackages]

    logger(f"Populating PurlDB with {len(packages):,d} PURLs from DiscoveredPackage")
    feed_purldb(
        packages=packages,
        chunk_size=100,
        logger=logger,
    )


def populate_purldb_with_discovered_dependencies(project, logger=logger.info):
    """Add DiscoveredDependency to PurlDB."""
    packages = [{"purl": purl} for purl in get_unique_resolved_purls(project)]

    logger(
        f"Populating PurlDB with {len(packages):,d} " "PURLs from DiscoveredDependency"
    )
    feed_purldb(
        packages=packages,
        chunk_size=100,
        logger=logger,
    )

    unresolved_packages = get_unique_unresolved_purls(project)
    unresolved_packages = [
        {"purl": purl, "vers": vers} for purl, vers in unresolved_packages
    ]

    logger(
        f"Populating PurlDB with {len(unresolved_packages):,d}"
        " unresolved PURLs from DiscoveredDependency"
    )
    feed_purldb(
        packages=unresolved_packages,
        chunk_size=10,
        logger=logger,
    )


def send_project_json_to_matchcode(project_json_location, timeout=DEFAULT_TIMEOUT, api_url=PURLDB_API_URL):
    """
    Given a path to a ScanCode.io Project JSON output, `project_json_location`,
    send the contents of the JSON file to PurlDB for matching.
    """
    project_json_contents = open(project_json_location, "rb")
    files = {"upload_file": project_json_contents}

    response = request_post(
        url=f"{api_url}matching/",
        data={},
        timeout=timeout,
        files=files,
    )

    return response


def match_to_purldb(project):
    """
    Given a `project` where `scan_output_location` has been set, send the scan
    of the project to PurlDB for matching. When available, process match results
    by DiscoveredPackges from the matched package data.
    """
    from scanpipe.pipes.d2d import create_package_from_purldb_data

    # send scan to purldb
    response = send_project_json_to_matchcode(project.scan_output_location)
    run_url = response["runs"][0]["url"]
    url = response.get("url")
    results_url = url + "results/"

    # poll and see if the match run is ready
    while True:
        response = request_get(run_url)
        if response:
            status = response["status"]
            if status == "success":
                break
        time.sleep(10)

    # get match results
    match_results = request_get(results_url)

    # map match results
    matched_packages = match_results.get('packages', [])
    resource_results = match_results.get('files', [])
    resource_paths_by_package_uids = defaultdict(list)
    for matched_package in matched_packages:
        package_uid = matched_package['package_uid']
        for resource in resource_results:
            if package_uid in resource.get('for_packages', []):
                resource_paths_by_package_uids[package_uid].append(resource['path'])

    # Map package matches
    for matched_package in matched_packages:
        package_uid = matched_package['package_uid']
        resource_paths = resource_paths_by_package_uids[package_uid]
        resources = project.codebaseresources.filter(path__in=resource_paths)

        # Create package matches
        create_package_from_purldb_data(
            project,
            resources=resources,
            package_data=matched_package,
            status=flag.MATCHED_TO_PURLDB_PACKAGE,
        )

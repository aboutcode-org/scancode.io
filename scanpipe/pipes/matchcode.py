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
from collections import defaultdict

from django.conf import settings

import requests
from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints

from scanpipe.pipes import codebase
from scanpipe.pipes import flag
from scanpipe.pipes import poll_until_success
from scanpipe.pipes.output import to_json


class MatchCodeIOException(Exception):
    pass


label = "MatchCode"
logger = logging.getLogger(__name__)
session = requests.Session()

# Only MATCHCODEIO_URL can be provided through setting
MATCHCODEIO_API_URL = None
MATCHCODEIO_URL = settings.MATCHCODEIO_URL
if MATCHCODEIO_URL:
    MATCHCODEIO_API_URL = f'{MATCHCODEIO_URL.rstrip("/")}/api/'

# Basic Authentication
MATCHCODEIO_USER = settings.MATCHCODEIO_USER
MATCHCODEIO_PASSWORD = settings.MATCHCODEIO_PASSWORD
basic_auth_enabled = MATCHCODEIO_USER and MATCHCODEIO_PASSWORD
if basic_auth_enabled:
    session.auth = (MATCHCODEIO_USER, MATCHCODEIO_PASSWORD)

# Authentication with single API key
MATCHCODEIO_API_KEY = settings.MATCHCODEIO_API_KEY
if MATCHCODEIO_API_KEY:
    session.headers.update({"Authorization": f"Token {MATCHCODEIO_API_KEY}"})

DEFAULT_TIMEOUT = 60


def is_configured():
    """Return True if the required MatchCode.io settings have been set."""
    if MATCHCODEIO_API_URL:
        return True
    return False


def is_available():
    """Return True if the configured MatchCode.io server is available."""
    if not is_configured():
        return False

    try:
        response = session.head(MATCHCODEIO_API_URL)
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


def request_post(url, data=None, headers=None, files=None, timeout=DEFAULT_TIMEOUT):
    try:
        response = session.post(
            url, data=data, timeout=timeout, headers=headers, files=files
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"{label} [Exception] {exception}")


def save_directory_fingerprints(project, virtual_codebase, to_codebase_only=False):
    """
    Save directory fingerprints from directory Resources in `virtual_codebase`
    to the directory CodebaseResources from `project` that have the same path.

    If `to_codebase_only` is True, then we are only saving the directory
    fingerprints for directories from the to/ codebase of a d2d project.
    """
    # Bulk update Directories with new fingerprints.
    # Code adapted from
    # scanpipe.migrations.0031_scancode_toolkit_v32_data_updates
    queryset = project.codebaseresources.directories()
    if to_codebase_only:
        queryset = queryset.to_codebase()

    object_count = queryset.count()
    logger.info(f"\nUpdating directory fingerprints for {object_count:,} directories.")
    chunk_size = 2000
    iterator = queryset.iterator(chunk_size=chunk_size)

    unsaved_objects = []
    has_virtual_root_prefix = virtual_codebase.root.path == "virtual_root"
    for index, directory in enumerate(iterator, start=1):
        if has_virtual_root_prefix:
            vc_path = f"virtual_root/{directory.path}"
        else:
            vc_path = directory.path

        vc_directory = virtual_codebase.get_resource(vc_path)
        if not vc_directory:
            # Generally, `virtual_codebase` should contain the Resources and
            # Directories that we care to create fingerprints for.
            # If `directory` is not in `virtual_codebase`, we can skip it.
            continue

        extra_data_keys = [
            "directory_content",
            "directory_structure",
        ]
        for key in extra_data_keys:
            value = vc_directory.extra_data.get(key, "")
            directory.extra_data[key] = value

        unsaved_objects.append(directory)

        if not (index % chunk_size) and unsaved_objects:
            logger.info(f"  {index:,} / {object_count:,} directories processed")

    logger.info("Updating directory DB objects...")
    project.codebaseresources.bulk_update(
        objs=unsaved_objects,
        fields=["extra_data"],
        batch_size=1000,
    )


def fingerprint_codebase_directories(project, to_codebase_only=False):
    """
    Compute directory fingerprints for the directories of the to/ codebase from
    `project`.

    These directory fingerprints are used for matching purposes on matchcode.
    """
    resources = project.codebaseresources.all()
    if to_codebase_only:
        resources = resources.to_codebase()
    virtual_codebase = codebase.get_basic_virtual_codebase(resources)
    virtual_codebase = compute_codebase_directory_fingerprints(virtual_codebase)
    save_directory_fingerprints(
        project, virtual_codebase, to_codebase_only=to_codebase_only
    )


def send_project_json_to_matchcode(
    project, timeout=DEFAULT_TIMEOUT, api_url=MATCHCODEIO_API_URL
):
    """
    Given a `project`, create a JSON scan of the `project` CodebaseResources and
    send it to MatchCode.io for matching. Return a tuple containing strings of the url
    to the particular match run and the url to the match results.
    """
    scan_output_location = to_json(project)
    with open(scan_output_location, "rb") as f:
        files = {"upload_file": f}
        response = request_post(
            url=f"{api_url}matching/",
            timeout=timeout,
            files=files,
        )
    run_url = response["runs"][0]["url"]
    return run_url


def get_run_url_status(run_url, **kwargs):
    """
    Given a `run_url`, which is a URL to a ScanCode.io Project run, return its
    status, otherwise return None.
    """
    response = request_get(run_url)
    if response:
        status = response["status"]
        return status


def poll_run_url_status(run_url, sleep=10):
    """
    Given a URL to a scancode.io run instance, `run_url`, return True when the
    run instance has completed successfully.

    Raise a MatchCodeIOException when the run instance has failed, stopped, or gone
    stale.
    """
    if poll_until_success(check=get_run_url_status, sleep=sleep, run_url=run_url):
        return True

    response = request_get(run_url)
    if response:
        log = response["log"]
        msg = f"Matching run has stopped:\n\n{log}"
        raise MatchCodeIOException(msg)


def get_match_results(run_url):
    """
    Given the `run_url` for a pipeline running the matchcode matching pipeline,
    return the match results for that run.
    """
    response = request_get(run_url)
    project_url = response["project"]
    # `project_url` can have params, such as "?format=json"
    if "?" in project_url:
        project_url, _ = project_url.split("?")
    project_url = project_url.rstrip("/")
    results_url = project_url + "/results/"
    return request_get(results_url)


def map_match_results(match_results):
    """
    Given `match_results`, which is a mapping of ScanCode.io codebase results,
    return a defaultdict(list) where the keys are the package_uid of matched
    packages and the value is a list containing the paths of Resources
    associated with the package_uid.
    """
    resource_results = match_results.get("files", [])
    resource_paths_by_package_uids = defaultdict(list)
    for resource in resource_results:
        for_packages = resource.get("for_packages", [])
        for package_uid in for_packages:
            resource_paths_by_package_uids[package_uid].append(resource["path"])
    return resource_paths_by_package_uids


def create_packages_from_match_results(project, match_results):
    """
    Given `match_results`, which is a mapping of ScanCode.io codebase results,
    use the Package data from it to create DiscoveredPackages for `project` and
    associate the proper Resources of `project` to the DiscoveredPackages.
    """
    from scanpipe.pipes.d2d import create_package_from_purldb_data

    resource_paths_by_package_uids = map_match_results(match_results)
    matched_packages = match_results.get("packages", [])
    for matched_package in matched_packages:
        package_uid = matched_package["package_uid"]
        resource_paths = resource_paths_by_package_uids[package_uid]
        resources = project.codebaseresources.filter(path__in=resource_paths)
        create_package_from_purldb_data(
            project,
            resources=resources,
            package_data=matched_package,
            status=flag.MATCHED_TO_PURLDB_PACKAGE,
        )

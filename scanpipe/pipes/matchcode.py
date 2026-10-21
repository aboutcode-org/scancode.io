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
import logging
from collections import defaultdict
from functools import partial
from pathlib import Path

from django.conf import settings

import requests
from licensedcode.spans import Span
from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints
from matchcode_toolkit.fingerprinting import get_file_fingerprint_hashes
from matchcode_toolkit.fingerprinting import get_line_by_pos
from matchcode_toolkit.fingerprinting import get_stemmed_file_fingerprint_hashes
from matchcode_toolkit.stemming import TS_LANGUAGE_CONF
from scancode import Scanner
from summarycode.classify import LEGAL_STARTS_ENDS

from scanpipe.models import OriginMatch
from scanpipe.pipes import codebase
from scanpipe.pipes import create_origin_matches
from scanpipe.pipes import flag
from scanpipe.pipes import poll_until_success
from scanpipe.pipes.output import to_json
from scanpipe.pipes.scancode import _scan_resource
from scanpipe.pipes.scancode import scan_resources


class MatchCodeIOException(Exception):
    pass


label = "MatchCode"
logger = logging.getLogger(__name__)
session = requests.Session()

# Only MATCHCODEIO_URL can be provided through setting
MATCHCODEIO_API_URL = None
MATCHCODEIO_URL = getattr(settings, "MATCHCODEIO_URL", "")
if MATCHCODEIO_URL:
    MATCHCODEIO_API_URL = f"{MATCHCODEIO_URL}/api/"

# Basic Authentication
MATCHCODEIO_USER = getattr(settings, "MATCHCODEIO_USER", "")
MATCHCODEIO_PASSWORD = getattr(settings, "MATCHCODEIO_PASSWORD", "")
basic_auth_enabled = MATCHCODEIO_USER and MATCHCODEIO_PASSWORD
if basic_auth_enabled:
    session.auth = (MATCHCODEIO_USER, MATCHCODEIO_PASSWORD)

# Authentication with single API key
MATCHCODEIO_API_KEY = getattr(settings, "MATCHCODEIO_API_KEY", "")
if MATCHCODEIO_API_KEY:
    session.headers.update({"Authorization": f"Token {MATCHCODEIO_API_KEY}"})

DEFAULT_TIMEOUT = 60

TOOL_NAME = "matchcode"

MATCH_TYPE_BY_STATUS = {
    flag.MATCHED_TO_PURLDB_PACKAGE: OriginMatch.MatchType.PACKAGE,
    flag.MATCHED_TO_PURLDB_RESOURCE: OriginMatch.MatchType.FILE,
    flag.MATCHED_TO_PURLDB_DIRECTORY: OriginMatch.MatchType.DIRECTORY,
    flag.APPROXIMATE_MATCHED_TO_PURLDB_RESOURCE: OriginMatch.MatchType.APPROXIMATE,
}


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
    """Send a GET request to `url` with optional `payload` and return the response."""
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
    """Send a POST request with `data` to `url` and return the response."""
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
    Compute directory fingerprints for the directories from `project`.

    These directory fingerprints are used for matching purposes on matchcode.

    If `to_codebase_only` is True, the only directories from the `to/` codebase
    are computed.
    """
    resources = project.codebaseresources.all()
    if to_codebase_only:
        resources = resources.to_codebase()

    if not resources.directories():
        return

    virtual_codebase = codebase.get_basic_virtual_codebase(resources)
    virtual_codebase = compute_codebase_directory_fingerprints(virtual_codebase)
    save_directory_fingerprints(
        project, virtual_codebase, to_codebase_only=to_codebase_only
    )


def fingerprint_codebase_resource(location, with_threading=True, **kwargs):
    """
    Compute fingerprints for the resource at `location` using the
    scancode-toolkit direct API.

    Return a dictionary of scan `results` and a list of `errors`.
    """
    scanners = [
        Scanner("fingerprints", get_file_fingerprint_hashes),
    ]
    return _scan_resource(location, scanners, with_threading=with_threading)


def save_resource_fingerprints(resource, scan_results, scan_errors=None):
    """
    Save computed fingerprints from `scan_results` to `resource.extra_data`.
    Create project errors if any occurred during the scan.
    """
    resource.extra_data.update(scan_results)
    resource.save()

    if scan_errors:
        resource.add_errors(scan_errors)
        resource.update(status=flag.SCANNED_WITH_ERROR)


def fingerprint_codebase_resources(
    project, resource_qs=None, progress_logger=None, to_codebase_only=False
):
    """
    Compute fingerprints for the resources from `project`.

    These resource fingerprints are used for matching purposes on matchcode.

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the SCANCODEIO_PROCESSES setting.

    If `to_codebase_only` is True, the only resources from the `to/` codebase
    are computed.
    """
    # Checking for None to make the distinction with an empty resource_qs queryset
    if resource_qs is None:
        resource_qs = project.codebaseresources.filter(is_text=True)

    if to_codebase_only:
        resource_qs = resource_qs.to_codebase()

    scan_resources(
        resource_qs=resource_qs,
        scan_func=fingerprint_codebase_resource,
        save_func=save_resource_fingerprints,
        progress_logger=progress_logger,
    )


def fingerprint_stemmed_codebase_resource(location, with_threading=True, **kwargs):
    """
    Compute stemmed code fingerprints for the resource at `location` using the
    scancode-toolkit direct API.

    Return a dictionary of scan `results` and a list of `errors`.
    """
    scanners = [
        Scanner("stemmed_fingerprints", get_stemmed_file_fingerprint_hashes),
    ]
    return _scan_resource(location, scanners, with_threading=with_threading)


def fingerprint_stemmed_codebase_resources(
    project, resource_qs=None, progress_logger=None, to_codebase_only=False
):
    """
    Compute stemmed code fingerprints for the resources from `project`.

    These resource fingerprints are used for matching purposes on matchcode.

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the SCANCODEIO_PROCESSES setting.

    If `to_codebase_only` is True, the only resources from the `to/` codebase
    are computed.
    """
    # Checking for None to make the distinction with an empty resource_qs queryset
    if resource_qs is None:
        resource_qs = project.codebaseresources.filter(
            programming_language__in=TS_LANGUAGE_CONF.keys()
        )

    if to_codebase_only:
        resource_qs = resource_qs.to_codebase()

    scan_resources(
        resource_qs=resource_qs,
        scan_func=fingerprint_stemmed_codebase_resource,
        save_func=save_resource_fingerprints,
        progress_logger=progress_logger,
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

    if not response:
        raise MatchCodeIOException("Invalid response from MatchCode.io")

    match_url = response["url"]
    run_url = response["runs"][0]["url"]
    return match_url, run_url


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


def create_match_results_url(match_url):
    """
    Given the `match_url` for a project running the matchcode matching pipeline,
    return the match results URL from `match_url`.
    """
    # `project_url` can have params, such as "?format=json"
    if "?" in match_url:
        match_url, _ = match_url.split("?")
    match_url = match_url.rstrip("/")
    match_url = match_url + "/results/"
    return match_url


def get_match_results(match_url):
    """
    Given the `match_url` for a project running the matchcode matching pipeline,
    return the match results.
    """
    match_results_url = create_match_results_url(match_url)
    return request_get(match_results_url)


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
    match_resources = match_results.get("files", [])
    for match_resource in match_resources:
        if match_resource["type"] != "file":
            continue
        match_resource_extra_data = match_resource["extra_data"]
        if match_resource_extra_data:
            resource = project.codebaseresources.get(path=match_resource["path"])
            # compute line_by_pos for displaying matches in CodebaseResource detail view
            line_by_pos = get_resource_line_by_pos(resource)
            match_resource_extra_data["line_by_pos"] = line_by_pos
            resource.update_extra_data(match_resource_extra_data)


def match_codebase(project):
    """
    Fingerprint the ``project`` codebase, send it to MatchCode.io, wait for the
    matching run to complete, and return the match results.
    """
    fingerprint_codebase_resources(project)
    fingerprint_codebase_directories(project)
    match_url, run_url = send_project_json_to_matchcode(project)
    poll_run_url_status(run_url)

    match_results = get_match_results(match_url)
    if not match_results:
        raise MatchCodeIOException("Cannot fetch the match results from MatchCode.io")
    return match_results


def save_match_results(project, match_results):
    """Write the raw ``match_results`` in the ``project`` output/ directory."""
    output_location = project.get_output_file_path("matchcode", "json")
    output_location.write_text(json.dumps(match_results, indent=2))


def get_resource_line_by_pos(resource):
    """Return the mapping of token positions to line numbers of a ``resource``."""
    return get_line_by_pos(resource.location_path.read_text())


def get_snippet_line_ranges(match_detections, line_by_pos):
    """
    Return a (start_line, end_line) tuple for each span of the matched token
    positions ``match_detections``, using the ``line_by_pos`` mapping.
    """
    return [
        (line_by_pos[span.start], line_by_pos[span.end])
        for span in Span(match_detections).subspans()
    ]


def get_line_coverage(line_ranges, line_by_pos):
    """
    Return the percentage of the code lines covered by the (start_line, end_line)
    ``line_ranges``, the code lines being the lines with tokens in ``line_by_pos``.
    This matches the SCANOSS similarity: the percentage of the file matched.
    """
    code_lines = set(line_by_pos.values())
    covered_lines = {
        line
        for start_line, end_line in line_ranges
        for line in range(start_line, end_line + 1)
    }
    return round(100 * len(covered_lines & code_lines) / len(code_lines))


def is_legal_file_path(path):
    """Return True if ``path`` is a legal file, such as a license or a notice."""
    file_path = Path(path.lower())
    return (
        file_path.name.startswith(LEGAL_STARTS_ENDS)
        or file_path.name.endswith(LEGAL_STARTS_ENDS)
        or file_path.stem.endswith(LEGAL_STARTS_ENDS)
    )


def get_package_extra_data(package_data):
    """Return the MatchCode package data kept as OriginMatch extra data."""
    return {
        "package_uid": package_data.get("package_uid", ""),
        "release_date": package_data.get("release_date") or "",
        "declared_license_expression": package_data.get(
            "declared_license_expression", ""
        ),
        "download_url": package_data.get("download_url", ""),
    }


def make_snippet_origin_matches(
    resource, matched_snippets, package_data_by_purl, tool_version
):
    """
    Yield unsaved OriginMatch instances for the ``resource`` snippet matches.
    Snippets matched in legal files are skipped, as a license text is a
    license clue, not an origin.
    The MatchCode snippet similarity is kept as extra data only, as its scale is
    not comparable with the other tools.
    """
    line_by_pos = get_resource_line_by_pos(resource)

    for matched_snippet in matched_snippets:
        origin_path = matched_snippet["resource"]
        if is_legal_file_path(origin_path):
            continue

        snippet_line_ranges = get_snippet_line_ranges(
            matched_snippet["match_detections"], line_by_pos
        )
        line_ranges = [
            {"lines": [start_line, end_line]}
            for start_line, end_line in snippet_line_ranges
        ]

        purl = matched_snippet["package"]
        extra_data = get_package_extra_data(package_data_by_purl.get(purl, {}))
        extra_data["snippet_similarity"] = matched_snippet["similarity"]

        yield OriginMatch(
            project=resource.project,
            resource=resource,
            purl=purl,
            match_type=OriginMatch.MatchType.SNIPPET,
            tool=TOOL_NAME,
            tool_version=tool_version,
            origin_path=origin_path,
            line_ranges=line_ranges,
            similarity=get_line_coverage(snippet_line_ranges, line_by_pos),
            extra_data=extra_data,
        )


def make_package_origin_matches(
    resource, match_type, package_uids, package_data_by_uid, tool_version
):
    """Yield unsaved OriginMatch instances for the ``resource`` matched packages."""
    similarity = 100 if match_type in OriginMatch.EXACT_MATCH_TYPES else None
    seen_purls = set()

    for package_uid in package_uids:
        package_data = package_data_by_uid[package_uid]
        purl = package_data["purl"]
        if purl in seen_purls:
            continue
        seen_purls.add(purl)

        yield OriginMatch(
            project=resource.project,
            resource=resource,
            purl=purl,
            match_type=match_type,
            tool=TOOL_NAME,
            tool_version=tool_version,
            similarity=similarity,
            extra_data=get_package_extra_data(package_data),
        )


def make_origin_matches(
    resource, resource_results, package_data_by_uid, package_data_by_purl, tool_version
):
    """Yield unsaved OriginMatch instances from a ``resource`` match results."""
    matched_snippets = (resource_results.get("extra_data") or {}).get(
        "matched_snippets"
    )
    if matched_snippets:
        yield from make_snippet_origin_matches(
            resource, matched_snippets, package_data_by_purl, tool_version
        )
        return

    match_type = MATCH_TYPE_BY_STATUS.get(resource_results.get("status"))
    if not match_type:
        return

    yield from make_package_origin_matches(
        resource,
        match_type,
        resource_results["for_packages"],
        package_data_by_uid,
        tool_version,
    )


def load_matchcode_results(project, match_results):
    """
    Create OriginMatch records for the ``project`` resources from the MatchCode.io
    ``match_results``. Return the number of processed origin matches.
    """
    packages_data = match_results.get("packages", [])
    package_data_by_uid = {
        package_data["package_uid"]: package_data for package_data in packages_data
    }
    package_data_by_purl = {
        package_data["purl"]: package_data for package_data in packages_data
    }
    results_by_path = {
        resource_results["path"]: resource_results
        for resource_results in match_results.get("files", [])
        if resource_results.get("for_packages")
    }
    make_matchcode_origin_matches = partial(
        make_origin_matches,
        package_data_by_uid=package_data_by_uid,
        package_data_by_purl=package_data_by_purl,
        tool_version=match_results["headers"][0]["tool_version"],
    )

    origin_match_count, _ = create_origin_matches(
        project, results_by_path, make_matchcode_origin_matches
    )
    return origin_match_count

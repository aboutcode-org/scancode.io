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

import hashlib
import logging
import os
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlparse

import requests
from license_expression import Licensing
from packageurl import PackageURL
from packageurl.contrib.purl2url import get_repo_download_url_by_package_type

from scanpipe.pipes import fetch
from scanpipe.pipes import flag

logger = logging.getLogger(__name__)


def validate_package_license_integrity(project):
    """Validate the correctness of the package license."""
    # Patterns to ignore certain resources during license validation
    ignore_patterns = [
        "*test*",
        "*.sh",
    ]

    for package in project.discoveredpackages.all():
        package_lic = package.get_declared_license_expression()
        if package_lic:
            if package.type == "cargo":
                # A single cargo package only has one Cargo.toml file
                # meaning only one package is defined. Therefore, we don't
                # need to check for the package_uid
                # In addition, the package_uid is not populated to source files:
                # https://github.com/aboutcode-org/scancode.io/issues/2169
                # so we set package_uid to None to consider all resources
                # in the codebase for license validation.
                package_uid = None
            else:
                package_uid = package.package_uid
            resources = project.codebaseresources.has_license_expression()
            detected_lic_list = collect_detected_licenses(
                resources, ignore_patterns, package_uid
            )

            if detected_lic_list:
                lic_exp = " AND ".join(detected_lic_list)
                detected_lic_exp = str(Licensing().dedup(lic_exp))

                if detected_lic_exp != package_lic:
                    package_issues = package.extra_data.get("issues", [])

                    package_issues.append(
                        {
                            "issue_type": "License Mismatch",
                            "declared_license": package_lic,
                            "detected_codebase_license": detected_lic_exp,
                        }
                    )

                    package.update_extra_data({"issues": package_issues})

                    for datafile_path in package.datafile_paths:
                        if not datafile_path.startswith("https://"):
                            data_path = project.codebaseresources.get(
                                path=datafile_path
                            )
                            data_path.update(status=flag.LICENSE_ISSUE)

                            resource_issues = data_path.extra_data.get("issues", [])
                            resource_issues.append(
                                {
                                    "issue_type": "License Mismatch",
                                    "declared_license": package_lic,
                                    "detected_codebase_license": detected_lic_exp,
                                }
                            )

                            data_path.update_extra_data({"issues": resource_issues})


def contains_ignore_pattern(resource_path, ignore_patterns):
    """Check if the resource path matches any of the ignore patterns."""
    for pattern in ignore_patterns:
        if fnmatch(resource_path, pattern):
            return True
    return False


def filter_ignored_licenses(license_expression, licensing):
    """Filter out ignored licenses from a license expression."""
    # Some licenses are not useful for validating package license
    # integrity, so we ignore them.
    ignored_licenses = [
        "free-unknown",
        "unknown",
        "unknown-license-reference",
        "unknown-spdx",
    ]

    if license_expression is None:
        return None

    if isinstance(license_expression, licensing.Symbol):
        if (
            hasattr(license_expression, "key")
            and license_expression.key in ignored_licenses
        ):
            return None
        return license_expression

    # Handle AND operations
    if isinstance(license_expression, licensing.AND):
        return handle_operator_expression(license_expression, licensing, licensing.AND)

    # Handle OR operations
    if isinstance(license_expression, licensing.OR):
        return handle_operator_expression(license_expression, licensing, licensing.OR)

    return license_expression


def handle_operator_expression(expression, licensing, operator):
    """
    Process AND/OR operations in a license expression, filtering out
    ignored licenses.
    """
    args = []
    for arg in expression.args:
        filtered_arg = filter_ignored_licenses(arg, licensing)
        if filtered_arg is not None:
            args.append(filtered_arg)
    if not args:
        return None
    if len(args) == 1:
        return args[0]

    return operator(*args)


def collect_detected_licenses(resources, ignore_patterns, package_uid=None):
    """Collect detected licenses from resources, ignoring defined patterns."""
    licensing = Licensing()
    detected_lic_list = []

    for resource in resources:
        if contains_ignore_pattern(resource.path, ignore_patterns):
            continue

        # If a package_uid is provided, only consider resources linked to it
        if package_uid and package_uid not in resource.for_packages:
            continue

        license_str = resource.detected_license_expression
        if not license_str:
            continue
        try:
            parsed_lic = licensing.parse(license_str)

            # Filter out the ignored keys
            filtered_license = filter_ignored_licenses(parsed_lic, licensing)

            if filtered_license is not None:
                final_lic = str(filtered_license)

                if final_lic not in detected_lic_list:
                    # Apply parentheses so that the 'OR' expression will
                    # not be filtered out when doing deduplication later.
                    detected_lic_list.append(f"({final_lic})")

        except Exception:
            logger.warning(
                "Failed to parse the license expression: %s at %s",
                license_str,
                resource.path,
            )
    return detected_lic_list


def get_url_netloc_namespace_and_name(url):
    """
    Extract netloc, namespace, and name from a URL path.
    - The last path component (except for web files) is considered the name.
    - Everything between netloc and name is considered the namespace.
    """
    parsed = urlparse(url)
    netloc = parsed.netloc
    parts = parsed.path.strip("/").split("/")

    if not parts or parts == [""]:
        return netloc, None, None

    if len(parts) > 1:
        last_part = parts[-1].lower()
        ignore_extensions = (".html", ".htm", ".php", ".jsp", ".asp", ".aspx")
        if last_part.startswith("index.") or last_part.endswith(ignore_extensions):
            parts.pop()

    name = parts[-1]
    namespace = "/".join(parts[:-1]) if len(parts) > 1 else None

    return netloc, namespace, name


def download_src_repo(download_url):
    try:
        return fetch.fetch_url(url=download_url).path
    except (ValueError, requests.RequestException):
        logger.warning("Failed to download source repository: %s", download_url)
        return None


def get_download_url(homepage_url, version):
    netloc, namespace, name = get_url_netloc_namespace_and_name(homepage_url)
    if netloc.endswith("github.io"):
        github_page_url = github_pages_to_repo(homepage_url)
        if github_page_url:
            netloc, namespace, name = get_url_netloc_namespace_and_name(github_page_url)

    if netloc in ("github.com", "gitlab.com", "bitbucket.org"):
        if netloc.endswith(".com"):
            package_type = netloc.removesuffix(".com")
            # There is an issue where the version may have a different prefix.
            # For example, version can have the following prefixes:
            # ["v", "V", "release-", "RELEASE-", "v-", "V-"]
            clarified_version = clarify_version_tag(
                package_type, namespace, name, version
            )
            if clarified_version:
                version = clarified_version
        elif netloc.endswith(".org"):
            package_type = netloc.removesuffix(".org")
        download_url = get_repo_download_url_by_package_type(
            type=package_type, namespace=namespace, name=name, version=version
        )
        return download_url
    return None


def clarify_version_tag(repo_type, namespace, name, version):
    """Use github/gitlab API to verify the version tag"""
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

    potential_prefixes = ["", "v", "V", "release-", "RELEASE-", "v-", "V-"]
    for prefix in potential_prefixes:
        potential_tag = f"{prefix}{version}"
        url = url_base.format(potential_tag)

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException:
            continue
        if response.status_code == 200:
            return potential_tag
        elif response.status_code in (403, 429):
            print(
                f"Rate limited by {repo_type} API while checking tag {potential_tag}."
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


def compute_sha1(file_path):
    """Compute the SHA1 hash of a file."""
    try:
        with open(file_path, "rb") as f:
            return hashlib.file_digest(f, "sha1").hexdigest()
    except OSError:
        return None


def get_all_files(base_dir):
    """
    Walk a directory and returns a dictionary mapping relative paths
    to their filename and SHA1 hash.
    """
    file_map = {}
    for root, _dirs, files in os.walk(base_dir):
        for file in files:
            full_path = os.path.join(root, file)
            hash = compute_sha1(full_path)
            rel_path = Path(full_path).relative_to(base_dir).as_posix()
            file_map[rel_path] = {"name": file, "hash": hash}
    return file_map


def consolidate_unmatched(all_files, unmatched_files):
    """
    Consolidate the unmatched files. If all files in a directory are
    unmatched, report the directory instead of individual files.
    Returns a list of tuples: (path, is_directory)
    """
    matched_files = set(all_files) - set(unmatched_files)

    # Find every parent directory that contains at least one matched file.
    directories_with_matches = set()
    for file_path in matched_files:
        for parent in Path(file_path).parents:
            parent_str = parent.as_posix()
            if parent_str != ".":
                directories_with_matches.add(parent_str)

    consolidated_results = set()

    # For each unmatched file, check if it belongs to a fully unmatched directory.
    for file_path in unmatched_files:
        path_obj = Path(file_path)
        target_path = file_path
        is_directory = False

        # Check from top to bottom
        for parent in reversed(path_obj.parents):
            current_dir = parent.as_posix()
            if current_dir == ".":
                continue

            if current_dir not in directories_with_matches:
                target_path = current_dir
                is_directory = True
                break  # Stop at the highest possible unmatched directory level

        consolidated_results.add((target_path, is_directory))

    # Convert the set to a list and sort it
    results_list = list(consolidated_results)
    results_list.sort()

    return results_list


def compare_directories(input_source, source_repo):
    """
    Compare two directories and return the count of matched files and a
    dictionary of mismatches.
    """
    input_files = get_all_files(input_source)
    repo_files = get_all_files(source_repo)

    matched_count = 0

    mismatches = {"mismatches": [], "input_source_only": [], "source_repo_only": []}

    repo_unmatched = {path: data for path, data in repo_files.items()}
    input_unmatched = {}

    # Check for exact path and hash match
    for input_path, input_data in input_files.items():
        if input_path in repo_files:
            if input_data["hash"] == repo_files[input_path]["hash"]:
                matched_count += 1
            else:
                mismatches["mismatches"].append(f"[File] {input_path}")
            del repo_unmatched[input_path]
        else:
            input_unmatched[input_path] = input_data

    repo_by_hash_name = {}
    for path, data in repo_unmatched.items():
        key = (data["hash"], data["name"])
        if key not in repo_by_hash_name:
            repo_by_hash_name[key] = []
        repo_by_hash_name[key].append(path)

    still_unmatched_input = {}

    # Check for files with the same hash and name but different paths
    for input_path, input_data in input_unmatched.items():
        hash_name_key = (input_data["hash"], input_data["name"])

        if hash_name_key in repo_by_hash_name and repo_by_hash_name[hash_name_key]:
            repo_match_path = repo_by_hash_name[hash_name_key].pop(0)
            matched_count += 1
            del repo_unmatched[repo_match_path]
        else:
            still_unmatched_input[input_path] = input_data

    input_consolidated = consolidate_unmatched(
        input_files.keys(), still_unmatched_input.keys()
    )
    for path, is_directory in input_consolidated:
        item_type = "Directory" if is_directory else "File"
        mismatches["input_source_only"].append(f"[{item_type}] {path}")

    repo_consolidated = consolidate_unmatched(repo_files.keys(), repo_unmatched.keys())
    for path, is_directory in repo_consolidated:
        item_type = "Directory" if is_directory else "File"
        mismatches["source_repo_only"].append(f"[{item_type}] {path}")

    return matched_count, mismatches


def count_total_files(directory):
    """Recursively counts all files in a given directory."""
    total_files = 0
    for _, _, files in os.walk(directory):
        total_files += len(files)
    return total_files


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
            )
        )


def fetch_inputs(purl):
    """Fetch the source for the given input purl"""
    purl_str = PackageURL.to_string(purl)
    purl_src_path = fetch_path(purl_str)
    if not purl_src_path:
        err_msg = f"No source could be resolved for {purl}."
        raise ValueError(err_msg)
    return purl_src_path


def fetch_path(purl):
    """Fetch the purl and return the location of the fetched tarball"""
    try:
        return fetch.fetch_url(url=purl).path
    except (ValueError, requests.RequestException) as e:
        logger.warning("Failed to fetch package: %s - %s", purl, e)
        return None

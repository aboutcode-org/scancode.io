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
import shutil
import subprocess
from pathlib import Path


def check_docker_command():
    """Check if the Docker command is available and the daemon is running."""
    docker_path = shutil.which("docker")
    if not docker_path:
        return False

    try:
        subprocess.run([docker_path, "info"], capture_output=True, check=True)  # noqa: S603
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


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
    base_dir = Path(base_dir)
    for full_path in base_dir.rglob("*"):
        if not full_path.is_file():
            continue
        hash = compute_sha1(full_path)
        rel_path = Path(full_path).relative_to(base_dir).as_posix()
        file_map[rel_path] = {"name": full_path.name, "hash": hash}
    return file_map


def get_all_files_from_resources(resources, base_path_prefix=""):
    """
    Build a file map from a ``CodebaseResource`` queryset using the SHA1
    already stored in the database.

    Return the same structure as get_all_files().
    """
    file_map = {}
    for resource in resources:
        if not resource.sha1:
            continue
        rel_path = resource.path.removeprefix(base_path_prefix)
        file_map[rel_path] = {
            "name": Path(resource.path).name,
            "hash": resource.sha1,
        }
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


def compare_directories(input_files, source_repo):
    """Compare the ``input_files`` mapping against the ``source_repo`` directory."""
    repo_files = get_all_files(source_repo)

    matched_count = 0

    mismatches = {"mismatches": [], "input_source_only": [], "source_repo_only": []}

    repo_unmatched = {path: data for path, data in repo_files.items()}
    input_unmatched = {}

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
    """Recursively count all files in a given directory."""
    total_files = 0
    for path in Path(directory).rglob("*"):
        if path.is_file():
            total_files += 1
    return total_files

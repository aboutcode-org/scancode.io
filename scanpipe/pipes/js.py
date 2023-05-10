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

import hashlib
import json
from pathlib import Path


def is_minified_and_map_compiled_from_source(
    to_resources, from_source, minified_extension
):
    """Return True if a minified file and its map were compiled from a source file."""
    if not minified_extension:
        return False
    path = Path(from_source.path.lstrip("/"))
    basename, extension = get_basename_and_extension(path.name)
    minified_file, minified_map_file = None, None

    source_file_name = path.name
    source_mapping = f"sourceMappingURL={basename}{minified_extension}.map"

    for resource in to_resources:
        if resource.path.endswith(minified_extension):
            minified_file = resource
        elif resource.path.endswith(f"{minified_extension}.map"):
            minified_map_file = resource

    if minified_file and minified_map_file:
        # Check minified_file contains reference to the source file.
        if source_mapping_in_minified(minified_file, source_mapping):
            # Check source file's content is in the map file or if the
            # source file path is in the map file.
            if source_content_in_map(minified_map_file, from_source) or source_in_map(
                minified_map_file, source_file_name
            ):
                return True

    return False


def source_mapping_in_minified(resource, source_mapping):
    """Return True if a string contains a specific string in its last 5 lines."""
    lines = resource.file_content.split("\n")
    total_lines = len(lines)
    # Get the last 5 lines.
    tail = 5 if total_lines > 5 else total_lines
    return any(source_mapping in line for line in reversed(lines[-tail:]))


def source_in_map(map_file, source_name):
    """
    Return True if the given source file name exists in the sources list of the
    specified map file.
    """
    with open(map_file.location) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return False

    sources = data.get("sources", [])
    return any(source.endswith(source_name) for source in sources)


def sha1(content):
    """Calculate the SHA-1 hash of a string."""
    hash_object = hashlib.sha1(content.encode())
    return hash_object.hexdigest()


def source_content_in_map(map_file, source_file):
    """Return True if the given source content is in specified map file."""
    with open(map_file.location) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return False

    contents = data.get("sourcesContent", [])
    return any(source_file.sha1 == sha1(content) for content in contents)


def get_basename_and_extension(filename):
    """Return the basename and extension of a JavaScript/TypeScript related file."""
    # The order of extensions in the list matters since
    # `.d.ts` should be tested first before `.ts`.
    js_extensions = [".d.ts", ".ts", ".js", ".jsx", ".scss"]
    for ext in js_extensions:
        if filename.endswith(ext):
            extension = ext
            break
    else:
        raise ValueError(f"{filename} has an invalid extension")
    basename = filename[: -len(extension)]
    return basename, extension

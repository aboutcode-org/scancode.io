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


def source_mapping_in_minified(resource, map_file_name):
    """Return True if a string contains a source mapping in its last 5 lines."""
    source_mapping = f"sourceMappingURL={map_file_name}"
    lines = resource.file_content.split("\n")
    total_lines = len(lines)
    # Get the last 5 lines.
    tail = 5 if total_lines > 5 else total_lines
    return any(source_mapping in line for line in reversed(lines[-tail:]))


def sha1(content):
    """Calculate the SHA-1 hash of a string."""
    hash_object = hashlib.sha1(content.encode())
    return hash_object.hexdigest()


def source_content_sha1(map_file):
    """Return list containing sha1 of sourcesContent."""
    contents = get_map_sources_content(map_file)
    return [sha1(content) for content in contents if content]


def get_map_sources(map_file):
    """Return source paths from a map file."""
    with open(map_file.location) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []

    sources = data.get("sources", [])
    sources = [source.rsplit("../", 1)[-1] for source in sources if source]
    return sources


def get_map_sources_content(map_file):
    """Return sources contents from a map file."""
    with open(map_file.location) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []

    contents = data.get("sourcesContent", [])
    return contents

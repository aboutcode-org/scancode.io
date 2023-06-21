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

from scanpipe.pipes import get_text_str_diff_ratio
from scanpipe.pipes import pathmap

# `PROSPECTIVE_JAVASCRIPT_MAP` maps transformed JS file to a dict
# that specifies extension of related files. The `related` key in
# each dict specifies the file extension of the related transformed file, and
# the `sources` key specifies the list of possible source extension.

PROSPECTIVE_JAVASCRIPT_MAP = {
    ".scss.js.map": {
        "related": [".scss.js", ".css", ".css.map", "_rtl.css"],
        "sources": [".scss"],
    },
    ".js.map": {
        "related": [".js", ".jsx", ".ts"],
        "sources": [".jsx", ".ts", ".js"],
    },
    ".soy.js.map": {
        "related": [".soy.js", ".soy"],
        "sources": [".soy"],
    },
    ".css.map": {
        "related": [".css"],
        "sources": [".css"],
    },
    ".ts": {
        "related": [],
        "sources": [".d.ts"],
    },
}


def is_source_mapping_in_minified(resource, map_file_name):
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


def source_content_sha1_list(map_file):
    """Return list containing sha1 of sourcesContent."""
    contents = get_map_sources_content(map_file)
    return [sha1(content) for content in contents if content]


def load_json_from_file(location):
    """Return the deserialized json content from ``location``."""
    with open(location) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return


def get_map_sources(map_file):
    """Return source paths from a map file."""
    if data := load_json_from_file(map_file.location):
        sources = data.get("sources", [])
        sources = [source.rsplit("../", 1)[-1] for source in sources if source]
        return sources
    return []


def get_map_sources_content(map_file):
    """Return sources contents from a map file."""
    if data := load_json_from_file(map_file.location):
        return data.get("sourcesContent", [])
    return []


def get_matches_by_ratio(
    to_map, from_resources_index, from_resources, diff_ratio_threshold=0.98
):
    sources = get_map_sources(to_map)
    sources_content = get_map_sources_content(to_map)

    matches = []
    for source, content in zip(sources, sources_content):
        prospect = pathmap.find_paths(source, from_resources_index)
        if not prospect:
            continue

        # Only create relations when the number of matches is inferior or equal to
        # the current number of path segment matched.
        too_many_prospects = len(prospect.resource_ids) > prospect.matched_path_length
        if too_many_prospects:
            continue

        for resource_id in prospect.resource_ids:
            from_source = from_resources.get(id=resource_id)
            diff_ratio = get_text_str_diff_ratio(content, from_source.file_content)
            if not diff_ratio or diff_ratio < diff_ratio_threshold:
                continue

            matches.append((from_source, {"diff_ratio": f"{diff_ratio:.1%}"}))

    return matches


def get_minified_resource(map_resource, minified_resources):
    """Return the corresponding minified file for a map file."""
    path = Path(map_resource.path.lstrip("/"))

    minified_file, _ = path.name.split(".map")
    minified_file_path = path.parent / minified_file
    minified_resource = minified_resources.get_or_none(path=minified_file_path)

    if not minified_resource:
        return

    if is_source_mapping_in_minified(minified_resource, path.name):
        return minified_resource


def get_basename_and_extension(filename):
    """Return the basename and extension of a JavaScript/TypeScript related file."""
    # The order of extensions in the list matters since
    # `.d.ts` should be tested first before `.ts`.
    js_extensions = [
        ".scss.js.map",
        ".soy.js.map",
        ".css.map",
        ".js.map",
        ".scss.js",
        ".soy.js",
        ".d.ts",
        ".scss",
        ".soy",
        ".css",
        ".jsx",
        ".js",
        ".ts",
    ]
    for ext in js_extensions:
        if filename.endswith(ext):
            extension = ext
            break
    else:
        raise ValueError(f"{filename} is not JavaScript related")
    basename = filename[: -len(extension)]
    return basename, extension

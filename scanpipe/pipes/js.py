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
import json
from contextlib import suppress
from pathlib import Path
import logging

from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist

from scanpipe import pipes
from scanpipe.models import CodebaseResource
from scanpipe.pipes import flag
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

logger = logging.getLogger(__name__)

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
    # The following hash is not used in any security context. It is only used
    # to generate a value for matching purposes, collisions are acceptable and
    # "content" is not coming from user-generated input.
    return hashlib.sha1(content.encode(), usedforsecurity=False).hexdigest()


def source_content_sha1_list(map_file):
    """Return list containing sha1 of sourcesContent."""
    contents = get_map_sources_content(map_file)
    return [sha1(content) for content in contents if content]


def load_json_from_file(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except UnicodeDecodeError as e:
        logger.error(f"Failed to decode {file} as JSON: {str(e)}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {file}: {str(e)}")
        return
    except Exception as e:
        logger.error(f"Unexpected error while reading {file}: {str(e)}")
        return


def get_map_sources(map_file):
    """Return source paths from a map file."""
    if data := load_json_from_file(map_file.location):
        sources = data.get("sources", [])
        sources = [
            source.rsplit("../", 1)[-1]
            for source in sources
            if source and not source.startswith("webpack:///")
        ]
        return [source for source in sources if len(Path(source).parts) > 1]
    return []


def get_map_sources_content(map_file):
    """Return sources contents from a map file."""
    if data := load_json_from_file(map_file.location):
        return data.get("sourcesContent", [])
    return []


def get_matches_by_sha1(to_map, from_resources):
    content_sha1_list = source_content_sha1_list(to_map)
    sources = get_map_sources(to_map)
    all_source_path_available = len(sources) == len(content_sha1_list)

    if not all_source_path_available:
        sha1_matches = from_resources.filter(sha1__in=content_sha1_list)

        # Only create relations when the number of sha1 matches if inferior or equal
        # to the number of sourcesContent in map.
        if len(sha1_matches) > len(content_sha1_list):
            return

        return [(match, {}) for match in sha1_matches]

    matches = []
    for sha1, source_path in zip(content_sha1_list, sources):
        try:
            match = from_resources.get(sha1=sha1, path__endswith=source_path)
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            match = None

        if match:
            matches.append((match, {}))

    return matches


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

        match = None
        too_many_match = False
        for resource_id in prospect.resource_ids:
            from_source = from_resources.get(id=resource_id)
            diff_ratio = get_text_str_diff_ratio(content, from_source.file_content)
            if not diff_ratio or diff_ratio < diff_ratio_threshold:
                continue

            if match:
                too_many_match = True
                break

            match = (from_source, {"diff_ratio": f"{diff_ratio:.1%}"})

        # For a given pair of source path and source content there should be
        # one and only one from resource.
        if not too_many_match and match:
            matches.append(match)

    return matches


def get_minified_resource(map_resource, minified_resources):
    """
    Return the corresponding minified_resource given a ``map_resource`` Resource
    object and a ``minified_resources`` query set of minified JS Resource.
    Return None if it cannot be found.
    """
    path = Path(map_resource.path.lstrip("/"))

    minified_file = path.name.removesuffix(".map")
    minified_file_path = path.parent / minified_file
    minified_resource = minified_resources.get_or_none(path=minified_file_path)

    if not minified_resource:
        return

    if is_source_mapping_in_minified(minified_resource, path.name):
        return minified_resource


_js_extensions = (
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
)


def get_js_map_basename_and_extension(filename):
    """
    Return a 2-tuple pf (basename, extension) of a JavaScript/TypeScript related
    file. Return None otherwise.
    """
    # The order of extensions in the list matters since
    # `.d.ts` should be tested first before `.ts`.
    if not filename.endswith(_js_extensions):
        return
    for ext in _js_extensions:
        if filename.endswith(ext):
            basename = filename[: -len(ext)]
            return basename, ext


def map_related_files(to_resources, to_resource, from_resource, map_type, extra_data):
    if not from_resource:
        return 0

    path = Path(to_resource.path.lstrip("/"))
    basename_and_extension = get_js_map_basename_and_extension(path.name)
    basename, extension = basename_and_extension
    base_path = path.parent / basename

    prospect = PROSPECTIVE_JAVASCRIPT_MAP.get(extension, {})

    transpiled = [to_resource]
    for related_ext in prospect.get("related", []):
        with suppress(CodebaseResource.DoesNotExist):
            transpiled.append(to_resources.get(path=f"{base_path}{related_ext}"))

    for match in transpiled:
        pipes.make_relation(
            from_resource=from_resource,
            to_resource=match,
            map_type=map_type,
            extra_data=extra_data,
        )
        match.update(status=flag.MAPPED)

    return len(transpiled)

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
import os
import shutil
import tempfile
from pathlib import Path

from django.conf import settings

from packageurl import PackageURL

from scanpipe.models import OriginMatch
from scanpipe.pipes import create_origin_matches
from scanpipe.pipes import make_origin_match
from scanpipe.pipes import run_command_safely

TOOL_NAME = "scanoss"

SCANOSS_URL = getattr(settings, "SCANOSS_URL", "")
SCANOSS_API_KEY = getattr(settings, "SCANOSS_API_KEY", "")

# The scanoss-py client is installed in a temporary environment for each scan,
# to keep its dependencies isolated from ScanCode.io. The latest version is used
# unless a version is pinned with this setting.
SCANOSS_PY_VERSION = getattr(settings, "SCANOSS_PY_VERSION", "")

# Engine flag to report all the candidate components instead of the best match.
DISABLE_BEST_MATCH_FLAG = 256

MATCH_TYPE_BY_SCANOSS_ID = {
    "file": OriginMatch.MatchType.FILE,
    "snippet": OriginMatch.MatchType.SNIPPET,
}


def is_configured():
    """Return True if a SCANOSS server URL is set."""
    return bool(SCANOSS_URL)


def get_uvx_location():
    """Return the full path of the uvx executable used to run scanoss-py, if any."""
    return shutil.which("uvx")


def get_scanoss_requirement():
    """Return the scanoss-py requirement, pinned when a version is configured."""
    if SCANOSS_PY_VERSION:
        return f"scanoss=={SCANOSS_PY_VERSION}"
    return "scanoss"


def scan_codebase(codebase_path, output_location):
    """
    Scan the ``codebase_path`` directory with SCANOSS and write the raw JSON
    results to ``output_location``.
    The scanoss-py client sends the file paths, checksums, sizes, and content
    fingerprints to the SCANOSS server, not the file contents.
    """
    # Only pass what scanoss-py needs to run, not the ScanCode.io secrets.
    scanoss_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "SCANOSS_API_KEY": SCANOSS_API_KEY,
    }

    with tempfile.TemporaryDirectory() as cache_directory:
        command_args = [
            get_uvx_location(),
            f"--cache-dir={cache_directory}",
            f"--from={get_scanoss_requirement()}",
            "scanoss-py",
            "scan",
            "--quiet",
            f"--apiurl={SCANOSS_URL}",
            f"--flags={DISABLE_BEST_MATCH_FLAG}",
            f"--output={output_location}",
            str(codebase_path),
        ]
        run_command_safely(command_args, env=scanoss_env)


def to_line_range(range_string):
    """Return a [start, end] list from a SCANOSS "start-end" range string."""
    start_line, end_line = range_string.split("-")
    return [int(start_line), int(end_line)]


def parse_line_ranges(lines, oss_lines):
    """
    Return the line range mappings of a SCANOSS match from its ``lines`` and
    ``oss_lines`` strings, such as "32-161,170-180". SCANOSS lists the ranges
    of both strings in the same order. A whole file match has no line ranges.
    """
    is_whole_file = lines == "all"
    if is_whole_file:
        return []

    return [
        {
            "lines": to_line_range(local_range),
            "origin_lines": to_line_range(origin_range),
        }
        for local_range, origin_range in zip(
            lines.split(","), oss_lines.split(","), strict=True
        )
    ]


def parse_similarity(matched):
    """Return the similarity as an integer from a SCANOSS "87%" matched string."""
    return int(matched.rstrip("%"))


def get_versioned_purl(component):
    """
    Return the versioned PURL string of a SCANOSS ``component``, or an empty
    string when the component has no valid PURL.
    SCANOSS reports versionless PURLs with the version in a separate field.
    """
    purls = component.get("purl")
    if not purls:
        return ""

    try:
        package_url = PackageURL.from_string(purls[0])
    except ValueError:
        return ""

    package_url_data = package_url.to_dict()
    package_url_data["version"] = package_url.version or component.get("version")
    return PackageURL(**package_url_data).to_string()


def get_components(scanoss_match):
    """
    Return the components of a ``scanoss_match``: the single best match
    component by default, or all the candidate components when the scan ran
    with the best match disabled.
    """
    return scanoss_match.get("components") or [scanoss_match]


def get_origin_match_extra_data(scanoss_match, component):
    """Return the SCANOSS data kept as OriginMatch extra data."""
    licenses = component.get("licenses", [])
    return {
        "purls": component.get("purl", []),
        "release_date": component.get("release_date", ""),
        "url": component.get("url", ""),
        "licenses": [
            {"name": license_data["name"], "source": license_data.get("source", "")}
            for license_data in licenses
        ],
        "file_hash": scanoss_match.get("file_hash", ""),
        "source_hash": scanoss_match.get("source_hash", ""),
        "hits": scanoss_match.get("hits"),
        "kb_version": scanoss_match.get("server", {}).get("kb_version", {}),
    }


def make_origin_matches(resource, scanoss_matches):
    """Yield unsaved OriginMatch instances for a ``resource`` SCANOSS matches."""
    for scanoss_match in scanoss_matches:
        match_type = MATCH_TYPE_BY_SCANOSS_ID.get(scanoss_match.get("id"))
        if not match_type:
            continue

        line_ranges = parse_line_ranges(
            scanoss_match["lines"], scanoss_match["oss_lines"]
        )
        similarity = parse_similarity(scanoss_match["matched"])
        tool_version = scanoss_match.get("server", {}).get("version", "")

        for component in get_components(scanoss_match):
            purl = get_versioned_purl(component)
            if not purl:
                continue

            yield make_origin_match(
                resource,
                TOOL_NAME,
                tool_version,
                purl=purl,
                match_type=match_type,
                origin_path=component.get("file", ""),
                line_ranges=line_ranges,
                similarity=similarity,
                extra_data=get_origin_match_extra_data(scanoss_match, component),
            )


def load_scanoss_results(project, results_location):
    """
    Create OriginMatch records for the ``project`` resources from the SCANOSS
    raw JSON results file at ``results_location``, a mapping of resource path to
    SCANOSS matches. Return the number of processed origin matches.
    """
    scanoss_results = json.loads(Path(results_location).read_text())
    origin_match_count, missing_paths = create_origin_matches(
        project, TOOL_NAME, scanoss_results, make_origin_matches
    )

    if missing_paths:
        project.add_warning(
            description="SCANOSS results for paths missing from the codebase",
            model="OriginMatch",
            details={"paths": sorted(missing_paths)},
        )

    return origin_match_count

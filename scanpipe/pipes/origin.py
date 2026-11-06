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

import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from itertools import batched
from itertools import groupby
from operator import attrgetter
from pathlib import PurePosixPath

from django.db import transaction
from django.db.models import Q

from packageurl import PackageURL

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import OriginDetermination
from scanpipe.models import OriginMatch
from scanpipe.pipes.resolve import convert_spdx_expression

VENDORED_PACKAGE_RULE = "vendored-package"
CONFLICTING_CANDIDATES_RULE = "conflicting-candidates"
CONTAINMENT_RULE = "containment"
EARLIEST_RELEASE_RULE = "earliest-release"
HIGHEST_SIMILARITY_RULE = "highest-similarity"
CONFLICTING_VERSIONS_RULE = "conflicting-versions"
PREFERRED_VERSION_RULE = "preferred-version"
NO_EXACT_MATCH_RULE = "no-exact-match"
SINGLE_TOOL_RULE = "single-tool"
CONFIRMED_BY_TWO_TOOLS_RULE = "confirmed-by-two-tools"

# Identifies the packages created from an origin determination, as opposed to
# the packages detected by the codebase scan.
ORIGIN_DATASOURCE_ID = "origin_determination"

# The paths of the resources assigned to a package detected by the codebase scan,
# kept in its extra data to unassign them on a re-run without touching the
# resources assigned by the scan.
ORIGIN_RESOURCE_PATHS_KEY = "origin_resource_paths"

# The SCANOSS license sources of the whole component. The other sources, such as
# "file_header", are the licenses of the matched file, already detected by the
# codebase scan.
SCANOSS_COMPONENT_LICENSE_SOURCES = ["component_declared", "license_file"]

# The shorter snippet matches are noise, such as a common license header matching
# unrelated packages: the MIT license header is 19 lines long. Counted in lines,
# not in percentage, to keep a copy of a few dozen lines in a large file.
MIN_SNIPPET_LINE_COUNT = 20

# The tools measure the similarity of a copy differently, a few points apart: a
# modified copy of inih "ini.c" is 95% similar for MatchCode.io and 94% for SCANOSS.
# A candidate is more similar than another only beyond this margin, in points.
MIN_SIMILARITY_MARGIN = 20

# A Git commit hash, full or abbreviated, such as the "498f34b" version reported by
# SCANOSS for a modified copy of inih.
COMMIT_HASH_PATTERN = re.compile(r"[0-9a-f]{7,40}")

# The directories where a package keeps its copies of other packages, such as
# "pip/_vendor/six.py" or "urllib3/packages/six.py".
VENDOR_DIRECTORY_NAMES = {
    "_vendor",
    "vendor",
    "vendored",
    "packages",
    "third_party",
    "extern",
}


def get_package_purl(purl, version=None):
    """
    Return the ``purl`` without qualifiers and subpath, with the ``version`` when
    provided.
    """
    package_url = PackageURL.from_string(purl)
    return PackageURL(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
        version=version or package_url.version,
    ).to_string()


def get_versioned_purls(purls, version):
    """
    Return the valid ``purls`` with the ``version``, such as the versionless
    equivalent PURLs reported by SCANOSS.
    """
    versioned_purls = set()
    for purl in purls:
        with suppress(ValueError):
            versioned_purls.add(get_package_purl(purl, version))
    return versioned_purls


def get_equivalent_purls(origin_match):
    """
    Return the PURLs identifying the ``origin_match`` package: its own PURL and
    the equivalent PURLs reported by the tool, such as the SCANOSS ``purls``.
    """
    version = PackageURL.from_string(origin_match.purl).version
    tool_purls = origin_match.extra_data.get("purls", [])
    return get_versioned_purls([origin_match.purl, *tool_purls], version)


def is_commit_version(version):
    """Return True when the ``version`` is a commit hash instead of a release."""
    # A date version, such as "20240101", is not a commit hash.
    return bool(COMMIT_HASH_PATTERN.fullmatch(version)) and not version.isdigit()


def normalize_name(name):
    """Return the ``name`` of a package or path segment in a comparable form."""
    return name.lower().replace("-", "_")


def get_path_names(path):
    """
    Return the normalized names of the directories of ``path`` and of its file
    name without extension.
    """
    file_path = PurePosixPath(path)
    names = [*file_path.parent.parts, file_path.stem]
    return {normalize_name(name) for name in names}


def get_vendored_package_name(path, carrier_names):
    """
    Return the name of the package vendored at ``path`` in a vendor directory of
    one of the ``carrier_names`` packages, such as "six" for
    "urllib3/packages/six.py", or the deepest for a package vendored by a vendored
    package, such as "pip/_vendor/urllib3/packages/six.py". Return an empty string
    when ``path`` is not in a vendor directory of a carrier.
    """
    path_parts = PurePosixPath(path).parts
    owner_names = carrier_names
    vendored_package_name = ""

    for parent_name, directory_name, child_name in zip(
        path_parts, path_parts[1:], path_parts[2:]
    ):
        is_owner_vendor_directory = (
            normalize_name(parent_name) in owner_names
            and normalize_name(directory_name) in VENDOR_DIRECTORY_NAMES
        )
        child_stem = PurePosixPath(child_name).stem
        # A private name, such as "_vendor/__init__.py", is not a package.
        if not is_owner_vendor_directory or child_stem.startswith("_"):
            continue

        vendored_package_name = child_stem
        owner_names = {normalize_name(vendored_package_name)}

    return vendored_package_name


def get_release_date(origin_match):
    """
    Return the release date of the ``origin_match`` package, None when the tool
    does not report a valid date.
    """
    release_date = origin_match.extra_data.get("release_date")
    if not release_date:
        return

    with suppress(ValueError):
        return date.fromisoformat(release_date)


def get_versionless_purl(purl):
    """Return the ``purl`` without version, qualifiers and subpath."""
    package_url = PackageURL.from_string(purl)
    return PackageURL(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
    ).to_string()


@dataclass
class Origin:
    """
    A candidate origin package of a resource, combining the origin matches that
    identify the same package, possibly with different but equivalent PURLs.
    """

    origin_matches: list
    # Kept up to date on merge, as it is compared for each resource.
    equivalent_purls: set

    @classmethod
    def from_origin_match(cls, origin_match):
        return cls([origin_match], get_equivalent_purls(origin_match))

    @property
    def tools(self):
        return {origin_match.tool for origin_match in self.origin_matches}

    @property
    def has_exact_match(self):
        return any(
            origin_match.match_type in OriginMatch.EXACT_MATCH_TYPES
            for origin_match in self.origin_matches
        )

    @property
    def purl(self):
        """
        Return the first reported PURL that is equivalent for all the origin
        matches, such as the "pypi" PURL when a tool reports the "github" one with
        "pypi" as equivalent.
        """
        reported_purls = [
            get_package_purl(origin_match.purl) for origin_match in self.origin_matches
        ]
        common_purls = set.intersection(*map(get_equivalent_purls, self.origin_matches))
        common_reported_purls = [
            reported_purl
            for reported_purl in reported_purls
            if reported_purl in common_purls
        ]
        return (common_reported_purls or reported_purls)[0]

    @property
    def versionless_purls(self):
        return {get_versionless_purl(purl) for purl in self.equivalent_purls}

    @property
    def package_names(self):
        return {
            normalize_name(PackageURL.from_string(purl).name)
            for purl in self.equivalent_purls
        }

    @property
    def origin_path_names(self):
        """Return the names in the paths of the copies in the origin package."""
        return {
            name
            for origin_match in self.origin_matches
            if origin_match.origin_path
            for name in get_path_names(origin_match.origin_path)
        }

    @property
    def vendored_package_names(self):
        """
        Return the names of the packages vendored by this origin package at the
        paths of the copies.
        """
        vendored_package_names = {
            get_vendored_package_name(origin_match.origin_path, self.package_names)
            for origin_match in self.origin_matches
        }
        vendored_package_names.discard("")
        return vendored_package_names

    @property
    def is_commit_version(self):
        return is_commit_version(PackageURL.from_string(self.purl).version)

    @property
    def similarity(self):
        """Return the highest similarity of the origin matches, 0 when unknown."""
        similarities = [
            origin_match.similarity
            for origin_match in self.origin_matches
            if origin_match.similarity is not None
        ]
        return max(similarities, default=0)

    @property
    def release_date(self):
        """Return the earliest release date of the origin matches, None if unknown."""
        release_dates = [
            release_date
            for origin_match in self.origin_matches
            if (release_date := get_release_date(origin_match))
        ]
        return min(release_dates, default=None)

    def is_same_package(self, other_origin):
        return bool(self.equivalent_purls & other_origin.equivalent_purls)

    def merge(self, other_origin):
        self.origin_matches.extend(other_origin.origin_matches)
        self.equivalent_purls |= other_origin.equivalent_purls


def get_same_package_origins(origin, origins):
    """Return the ``origins`` of the same package as ``origin``."""
    return [
        other_origin for other_origin in origins if origin.is_same_package(other_origin)
    ]


def group_origin_matches(origin_matches):
    """Return the list of distinct origins reported by the ``origin_matches``."""
    origins = []

    for origin_match in origin_matches:
        origin = Origin.from_origin_match(origin_match)
        for same_package_origin in get_same_package_origins(origin, origins):
            origin.merge(same_package_origin)
            origins.remove(same_package_origin)
        origins.append(origin)

    return origins


def get_matched_line_count(origin_match):
    """Return the number of resource lines covered by the ``origin_match``."""
    matched_lines = {
        line
        for line_range in origin_match.line_ranges
        for line in range(line_range["lines"][0], line_range["lines"][1] + 1)
    }
    return len(matched_lines)


def is_short_snippet_match(origin_match):
    """Return True when ``origin_match`` is a snippet match too short to count."""
    is_snippet_match = origin_match.match_type == OriginMatch.MatchType.SNIPPET
    return (
        is_snippet_match
        and get_matched_line_count(origin_match) < MIN_SNIPPET_LINE_COUNT
    )


def iter_resource_origins(origin_matches):
    """
    Yield (resource, origins) for the ``origin_matches`` ordered by resource.
    The short snippet matches are ignored.
    """
    get_resource = attrgetter("resource")
    for resource, resource_origin_matches in groupby(origin_matches, key=get_resource):
        counted_origin_matches = [
            origin_match
            for origin_match in resource_origin_matches
            if not is_short_snippet_match(origin_match)
        ]
        if not counted_origin_matches:
            continue

        yield resource, group_origin_matches(counted_origin_matches)


def get_ancestor_paths(path):
    """Return the ancestor directory paths of ``path``, closest first."""
    return [str(parent) for parent in PurePosixPath(path).parents[:-1]]


def remove_ancestor_directory_origins(origins_by_directory_path):
    """
    Remove from each directory the origins also found in one of its
    subdirectories, as the deepest directory is the most precise match.
    """
    for path, origins in origins_by_directory_path.items():
        for ancestor_path in get_ancestor_paths(path):
            ancestor_origins = origins_by_directory_path.get(ancestor_path)
            if not ancestor_origins:
                continue

            origins_by_directory_path[ancestor_path] = [
                ancestor_origin
                for ancestor_origin in ancestor_origins
                if not get_same_package_origins(ancestor_origin, origins)
            ]


def get_closest_directory_origins(path, origins_by_directory_path):
    """Return the origins of the closest ancestor directory of ``path``."""
    for ancestor_path in get_ancestor_paths(path):
        if ancestor_origins := origins_by_directory_path.get(ancestor_path):
            return ancestor_origins
    return []


def is_directory_origin(file_origins, directory_origins):
    """Return True when all the ``file_origins`` are ``directory_origins``."""
    return all(
        get_same_package_origins(file_origin, directory_origins)
        for file_origin in file_origins
    )


def is_same_package_versions(origins):
    """Return True when the ``origins`` are versions of the same package."""
    return bool(set.intersection(*(origin.versionless_purls for origin in origins)))


def get_only_origin_with(origins, attribute_name, value):
    """
    Return the only origin among the ``origins`` with the ``value`` of
    ``attribute_name``, None when there is none or several.
    """
    matching_origins = [
        origin for origin in origins if getattr(origin, attribute_name) == value
    ]
    if len(matching_origins) == 1:
        return matching_origins[0]


def get_preferred_version_origin(origins):
    """
    Return the origin of the preferred version among the ``origins`` versions of
    the same package: the only release version, as opposed to a commit, or else
    the clearly most similar version. Return None when no version is preferred.
    """
    release_origins = [origin for origin in origins if not origin.is_commit_version]
    if len(release_origins) == 1:
        return release_origins[0]

    return get_most_similar_origin(release_origins or origins)


def get_earliest_release_origin(origins):
    """
    Return the origin released before all the other ``origins``, as a copy cannot
    be older than its origin. Return None when a release date is unknown, or when
    the earliest date is shared.
    """
    release_dates = [origin.release_date for origin in origins]
    if None in release_dates:
        return

    return get_only_origin_with(origins, "release_date", min(release_dates))


def get_most_similar_origin(origins):
    """
    Return the origin more similar than all the other ``origins`` by at least
    ``MIN_SIMILARITY_MARGIN`` points, as the copy resembles it the most. Return None
    when a similarity is unknown, or when the margin is not reached.
    """
    similarities = sorted((origin.similarity for origin in origins), reverse=True)
    has_unknown_similarity = 0 in similarities
    if has_unknown_similarity:
        return

    highest_similarity, second_highest_similarity = similarities[:2]
    if highest_similarity - second_highest_similarity >= MIN_SIMILARITY_MARGIN:
        return get_only_origin_with(origins, "similarity", highest_similarity)


def is_carrier_origin(origin, other_origins):
    """
    Return True when the copy in the ``origin`` package is in a directory or file
    named after one of the ``other_origins`` packages, such as six.py vendored by
    pip in "pip/_vendor/six.py": the ``origin`` carries the copy of another
    package.
    """
    return any(
        origin.origin_path_names & other_origin.package_names
        for other_origin in other_origins
    )


def get_contained_origin(origins):
    """
    Return the only origin among the ``origins`` of different packages that does
    not carry the copy of another, when the others do. Return None otherwise.
    """
    non_carrier_origins = []
    for origin in origins:
        other_origins = [
            other_origin for other_origin in origins if other_origin is not origin
        ]
        if not is_carrier_origin(origin, other_origins):
            non_carrier_origins.append(origin)

    has_carrier_origin = len(non_carrier_origins) < len(origins)
    if has_carrier_origin and len(non_carrier_origins) == 1:
        return non_carrier_origins[0]


def get_conflict_rule_and_candidate(origins):
    """
    Return the determination rule of the conflicting candidate ``origins`` of a
    resource, and the proposed candidate origin, None when there is no proposal.
    """
    if not is_same_package_versions(origins):
        if contained_origin := get_contained_origin(origins):
            return CONTAINMENT_RULE, contained_origin
        if earliest_origin := get_earliest_release_origin(origins):
            return EARLIEST_RELEASE_RULE, earliest_origin
        if most_similar_origin := get_most_similar_origin(origins):
            return HIGHEST_SIMILARITY_RULE, most_similar_origin
        return CONFLICTING_CANDIDATES_RULE, None

    if preferred_origin := get_preferred_version_origin(origins):
        return PREFERRED_VERSION_RULE, preferred_origin

    return CONFLICTING_VERSIONS_RULE, None


def get_single_origin_rule(origin):
    """Return the determination rule of the only candidate ``origin`` of a resource."""
    if not origin.has_exact_match:
        return NO_EXACT_MATCH_RULE

    # A single tool can miss the other candidates: MatchCode.io stops at the
    # first package matched, and SCANOSS reports one component per file.
    if len(origin.tools) < 2:
        return SINGLE_TOOL_RULE

    return CONFIRMED_BY_TWO_TOOLS_RULE


def get_rule_and_candidate(origins):
    """
    Return the determination rule of the candidate ``origins`` of a resource, and
    the proposed candidate origin, None when there is no proposal.
    """
    if len(origins) > 1:
        return get_conflict_rule_and_candidate(origins)

    origin = origins[0]
    return get_single_origin_rule(origin), origin


def get_vendored_package_purl(origins):
    """
    Return the versionless PURL of the only package vendored by the ``origins``
    packages at the paths of the copies, when it is not itself a candidate, such
    as six for a copy of six taken from urllib3. Return an empty string otherwise.
    """
    candidate_names = set().union(*(origin.package_names for origin in origins))
    vendored_package_purls = {
        PackageURL(
            type=PackageURL.from_string(origin.purl).type,
            name=vendored_package_name,
        ).to_string()
        for origin in origins
        for vendored_package_name in origin.vendored_package_names
        if normalize_name(vendored_package_name) not in candidate_names
    }
    if len(vendored_package_purls) == 1:
        return vendored_package_purls.pop()
    return ""


def get_rule_and_purl(origins):
    """
    Return the determination rule of the candidate ``origins`` of a resource, and
    the proposed PURL, empty when there is no proposal. The package vendored by a
    candidate is the ultimate origin of the copy: its version is unknown.
    """
    if vendored_package_purl := get_vendored_package_purl(origins):
        return VENDORED_PACKAGE_RULE, vendored_package_purl

    rule, candidate_origin = get_rule_and_candidate(origins)
    return rule, candidate_origin.purl if candidate_origin else ""


def make_origin_determination(project, resource, origins):
    """Return an unsaved OriginDetermination for the ``resource`` ``origins``."""
    rule, purl = get_rule_and_purl(origins)
    status = OriginDetermination.Status.NEEDS_REVIEW
    if rule == CONFIRMED_BY_TWO_TOOLS_RULE:
        status = OriginDetermination.Status.AUTO_CONFIRMED

    return OriginDetermination(
        project=project,
        resource=resource,
        purl=purl,
        status=status,
        rule=rule,
    )


def iter_origin_determinations(project, origin_matches):
    """
    Yield unsaved OriginDetermination instances from the ``origin_matches``.
    The files of a matched directory are determined with the directory, unless
    they are matched to another package.
    """
    directory_origin_matches = origin_matches.filter(
        resource__type=CodebaseResource.Type.DIRECTORY
    )
    directories_by_path = {}
    origins_by_directory_path = {}
    for resource, origins in iter_resource_origins(directory_origin_matches):
        directories_by_path[resource.path] = resource
        origins_by_directory_path[resource.path] = origins

    remove_ancestor_directory_origins(origins_by_directory_path)

    file_origin_matches = origin_matches.exclude(
        resource__type=CodebaseResource.Type.DIRECTORY
    )
    file_origin_matches = file_origin_matches.iterator(chunk_size=2000)
    for resource, file_origins in iter_resource_origins(file_origin_matches):
        directory_origins = get_closest_directory_origins(
            resource.path, origins_by_directory_path
        )
        if not is_directory_origin(file_origins, directory_origins):
            yield make_origin_determination(project, resource, file_origins)
            continue

        # The file matches count for the directory: an exact file match by one tool
        # confirms the directory match by another tool.
        for file_origin in file_origins:
            get_same_package_origins(file_origin, directory_origins)[0].merge(
                file_origin
            )

    for path, origins in origins_by_directory_path.items():
        if origins:
            yield make_origin_determination(project, directories_by_path[path], origins)


def get_first_extra_data_value(origin_matches, key):
    """Return the first non-empty ``key`` value of the ``origin_matches`` extra data."""
    for origin_match in origin_matches:
        if value := origin_match.extra_data.get(key):
            return value
    return ""


def get_license_names(origin_matches):
    """
    Return the distinct component license names of the ``origin_matches`` extra
    data.
    """
    license_names = [
        license_data["name"]
        for origin_match in origin_matches
        for license_data in origin_match.extra_data.get("licenses", [])
        if license_data.get("source") in SCANOSS_COMPONENT_LICENSE_SOURCES
    ]
    return list(dict.fromkeys(license_names))


def get_origin_license_data(origin_matches):
    """
    Return the declared license fields of the ``origin_matches`` package: the
    MatchCode.io license expression, or else the component license names reported
    by SCANOSS, joined with AND.
    """
    license_expression = get_first_extra_data_value(
        origin_matches, "declared_license_expression"
    )
    if license_expression:
        return {"declared_license_expression": license_expression}

    license_names = get_license_names(origin_matches)
    if not license_names:
        return {}

    license_expression_spdx = " AND ".join(license_names)
    return {
        "declared_license_expression": convert_spdx_expression(license_expression_spdx),
        "declared_license_expression_spdx": license_expression_spdx,
    }


def get_origin_package_data(origin_matches):
    """Return the package data reported by the origin tools ``origin_matches``."""
    return {
        "download_url": get_first_extra_data_value(origin_matches, "download_url"),
        "homepage_url": get_first_extra_data_value(origin_matches, "url"),
        "release_date": get_first_extra_data_value(origin_matches, "release_date"),
        **get_origin_license_data(origin_matches),
    }


def get_purl_origin_matches(project, purl, resources):
    """Return the ``resources`` origin matches equivalent to the ``purl``."""
    origin_matches = project.originmatchs.filter(resource__in=resources).only(
        "purl", "extra_data"
    )
    return [
        origin_match
        for origin_match in origin_matches
        if purl in get_equivalent_purls(origin_match)
    ]


def get_origin_packages(project):
    """Return the ``project`` packages created from an origin determination."""
    return project.discoveredpackages.filter(datasource_ids=[ORIGIN_DATASOURCE_ID])


def get_or_create_origin_package(project, purl, resources):
    """
    Return the ``project`` package of ``purl``, such as a package detected by the
    codebase scan, or else create it from the ``resources`` origin matches.
    """
    purl_data = PackageURL.from_string(purl).to_dict()
    lookup_purl_data = DiscoveredPackage.extract_purl_data(purl_data)
    if package := project.discoveredpackages.filter(**lookup_purl_data).first():
        return package

    origin_matches = get_purl_origin_matches(project, purl, resources)
    package_data = {
        **purl_data,
        **get_origin_package_data(origin_matches),
        "datasource_ids": [ORIGIN_DATASOURCE_ID],
    }
    return DiscoveredPackage.create_from_data(project, package_data)


def assign_origin_package_resources(package, resources):
    """
    Assign the ``resources`` to the origin ``package``. On a package detected by
    the codebase scan, the paths of the newly assigned resources are kept in its
    extra data.
    """
    is_scan_package = ORIGIN_DATASOURCE_ID not in package.datasource_ids
    if not is_scan_package:
        package.add_resources(resources)
        return

    new_resources = list(resources.exclude(discovered_packages=package))
    if not new_resources:
        return

    package.add_resources(new_resources)
    new_resource_paths = [resource.path for resource in new_resources]
    package.update_extra_data({ORIGIN_RESOURCE_PATHS_KEY: new_resource_paths})


def unassign_scan_package_resources(project):
    """
    Remove the resources assigned by a previous run to the ``project`` packages
    detected by the codebase scan.
    """
    scan_packages = project.discoveredpackages.filter(
        extra_data__has_key=ORIGIN_RESOURCE_PATHS_KEY
    )
    for package in scan_packages:
        origin_resource_paths = package.extra_data.pop(ORIGIN_RESOURCE_PATHS_KEY)
        package.codebase_resources.through.objects.filter(
            discoveredpackage=package,
            codebaseresource__path__in=origin_resource_paths,
        ).delete()
        package.update(extra_data=package.extra_data)


def get_descendants_filter(directory_paths):
    """Return a filter of the resources under any of the ``directory_paths``."""
    # Matches no resource when there is no directory.
    descendants_filter = Q(pk__in=[])
    for directory_path in directory_paths:
        descendants_filter |= Q(path__startswith=f"{directory_path}/")
    return descendants_filter


def get_determined_directory_paths(project):
    """Return the paths of the ``project`` directories that have a determination."""
    directory_determinations = project.origindeterminations.filter(
        resource__type=CodebaseResource.Type.DIRECTORY
    )
    return list(directory_determinations.values_list("resource__path", flat=True))


def get_determined_resources(project, determinations, determined_directory_paths):
    """
    Return the resources of the ``determinations``, including the resources of
    the determined directories that have no determination of their own and are
    not under a determined subdirectory of ``determined_directory_paths``.
    """
    resource_ids = [determination.resource_id for determination in determinations]
    resources_filter = Q(pk__in=resource_ids)

    for determination in determinations:
        if not determination.resource.is_dir:
            continue

        directory_path = determination.resource.path
        subdirectory_paths = [
            path
            for path in determined_directory_paths
            if path.startswith(f"{directory_path}/")
        ]
        resources_filter |= (
            get_descendants_filter([directory_path])
            & ~get_descendants_filter(subdirectory_paths)
            & Q(origin_determination__isnull=True)
        )

    return project.codebaseresources.filter(resources_filter)


def assign_origin_packages(project):
    """
    Assign the resources of the confirmed ``project`` determinations to their
    origin package, created from the origin matches data when missing.
    Return the number of origin packages.
    """
    confirmed_determinations = (
        project.origindeterminations.confirmed()
        .select_related("resource")
        .only("purl", "resource__path", "resource__type")
        .order_by("purl")
        .iterator(chunk_size=2000)
    )
    determined_directory_paths = get_determined_directory_paths(project)
    get_purl = attrgetter("purl")
    package_count = 0

    for purl, purl_determinations in groupby(confirmed_determinations, key=get_purl):
        resources = get_determined_resources(
            project, list(purl_determinations), determined_directory_paths
        )
        package = get_or_create_origin_package(project, purl, resources)
        assign_origin_package_resources(package, resources)
        package_count += 1

    return package_count


def determine_origins(project, batch_size=2000):
    """
    Determine the origin of the ``project`` resources from their origin matches,
    and assign the resources of a confirmed origin to the origin package.
    The previous automatic determinations, origin packages and resources assigned
    to packages detected by the codebase scan are replaced, while the
    determinations made by a user are kept unchanged. A directory determined
    by a user covers its content: the origin matches under it are not used.
    Return the number of created determinations and the number of origin packages.
    """
    determination_count = 0

    with transaction.atomic():
        get_origin_packages(project).delete()
        unassign_scan_package_resources(project)
        project.origindeterminations.automatic().delete()

        # Only the user determinations are left.
        user_directory_paths = get_determined_directory_paths(project)
        user_covered_resources = project.codebaseresources.filter(
            get_descendants_filter(user_directory_paths)
        )
        origin_matches = (
            project.originmatchs.filter(resource__origin_determination__isnull=True)
            .exclude(resource__in=user_covered_resources)
            .select_related("resource")
            .only(
                "purl",
                "match_type",
                "tool",
                "origin_path",
                "line_ranges",
                "similarity",
                "extra_data",
                "resource__path",
                "resource__type",
            )
            .order_by("resource__path", "tool")
        )
        determinations = iter_origin_determinations(project, origin_matches)
        for determination_batch in batched(determinations, batch_size):
            OriginDetermination.objects.bulk_create(determination_batch)
            determination_count += len(determination_batch)

        package_count = assign_origin_packages(project)

    return determination_count, package_count

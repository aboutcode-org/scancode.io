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

from contextlib import suppress
from dataclasses import dataclass
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

CONFLICTING_CANDIDATES_RULE = "conflicting-candidates"
CONFLICTING_VERSIONS_RULE = "conflicting-versions"
NO_EXACT_MATCH_RULE = "no-exact-match"
SINGLE_TOOL_RULE = "single-tool"
CONFIRMED_BY_TWO_TOOLS_RULE = "confirmed-by-two-tools"

# Identifies the packages created from an origin determination, as opposed to
# the packages detected by the codebase scan.
ORIGIN_DATASOURCE_ID = "origin_determination"


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


def iter_resource_origins(origin_matches):
    """Yield (resource, origins) for the ``origin_matches`` ordered by resource."""
    get_resource = attrgetter("resource")
    for resource, resource_origin_matches in groupby(origin_matches, key=get_resource):
        yield resource, group_origin_matches(resource_origin_matches)


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


def get_rule(origins):
    """Return the determination rule of the candidate ``origins`` of a resource."""
    if len(origins) > 1:
        if is_same_package_versions(origins):
            return CONFLICTING_VERSIONS_RULE
        return CONFLICTING_CANDIDATES_RULE

    origin = origins[0]
    if not origin.has_exact_match:
        return NO_EXACT_MATCH_RULE

    # A single tool can miss the other candidates: MatchCode.io stops at the
    # first package matched, and SCANOSS reports one component per file.
    if len(origin.tools) < 2:
        return SINGLE_TOOL_RULE

    return CONFIRMED_BY_TWO_TOOLS_RULE


def make_origin_determination(project, resource, origins):
    """Return an unsaved OriginDetermination for the ``resource`` ``origins``."""
    rule = get_rule(origins)
    status = OriginDetermination.Status.NEEDS_REVIEW
    if rule == CONFIRMED_BY_TWO_TOOLS_RULE:
        status = OriginDetermination.Status.AUTO_CONFIRMED

    has_single_candidate = len(origins) == 1
    return OriginDetermination(
        project=project,
        resource=resource,
        purl=origins[0].purl if has_single_candidate else "",
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
    """Return the distinct license names of the ``origin_matches`` extra data."""
    license_names = [
        license_data["name"]
        for origin_match in origin_matches
        for license_data in origin_match.extra_data.get("licenses", [])
    ]
    return list(dict.fromkeys(license_names))


def get_origin_license_data(origin_matches):
    """
    Return the declared license fields of the ``origin_matches`` package: the
    MatchCode.io license expression, or else the SPDX license names reported by
    SCANOSS, all required.
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


def get_determined_resources(project, determinations):
    """
    Return the resources of the ``determinations``, including the resources of
    the determined directories that have no determination of their own.
    """
    resource_ids = [determination.resource_id for determination in determinations]
    resources_filter = Q(pk__in=resource_ids)

    for determination in determinations:
        if determination.resource.is_dir:
            resources_filter |= Q(
                path__startswith=f"{determination.resource.path}/",
                origin_determination__isnull=True,
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
    )
    get_purl = attrgetter("purl")
    package_count = 0

    for purl, purl_determinations in groupby(confirmed_determinations, key=get_purl):
        resources = get_determined_resources(project, list(purl_determinations))
        package = get_or_create_origin_package(project, purl, resources)
        package.add_resources(resources)
        package_count += 1

    return package_count


def determine_origins(project, batch_size=2000):
    """
    Determine the origin of the ``project`` resources from their origin matches,
    and assign the resources of a confirmed origin to the origin package.
    The previous automatic determinations and origin packages are replaced, while
    the determinations made by a user are kept unchanged.
    Return the number of created determinations and the number of origin packages.
    """
    determination_count = 0

    with transaction.atomic():
        get_origin_packages(project).delete()
        project.origindeterminations.automatic().delete()

        origin_matches = (
            project.originmatchs.filter(resource__origin_determination__isnull=True)
            .select_related("resource")
            .only(
                "purl",
                "match_type",
                "tool",
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

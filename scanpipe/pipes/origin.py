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

from packageurl import PackageURL

from scanpipe.models import CodebaseResource
from scanpipe.models import OriginDetermination
from scanpipe.models import OriginMatch

CONFLICTING_CANDIDATES_RULE = "conflicting-candidates"
NO_EXACT_MATCH_RULE = "no-exact-match"
SINGLE_TOOL_RULE = "single-tool"
CONFIRMED_BY_TWO_TOOLS_RULE = "confirmed-by-two-tools"


def get_package_purl(purl, version):
    """Return the ``purl`` with the ``version``, without qualifiers and subpath."""
    package_url = PackageURL.from_string(purl)
    return PackageURL(
        type=package_url.type,
        namespace=package_url.namespace,
        name=package_url.name,
        version=version,
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


@dataclass
class Origin:
    """
    A candidate origin package of a resource, combining the origin matches that
    identify the same package, possibly with different but equivalent PURLs.
    """

    reported_purls: list
    equivalent_purls: set
    common_purls: set
    tools: set
    has_exact_match: bool

    @classmethod
    def from_origin_match(cls, origin_match):
        version = PackageURL.from_string(origin_match.purl).version
        reported_purl = get_package_purl(origin_match.purl, version)
        tool_purls = origin_match.extra_data.get("purls", [])
        equivalent_purls = {reported_purl, *get_versioned_purls(tool_purls, version)}
        return cls(
            reported_purls=[reported_purl],
            equivalent_purls=equivalent_purls,
            common_purls=set(equivalent_purls),
            tools={origin_match.tool},
            has_exact_match=origin_match.match_type in OriginMatch.EXACT_MATCH_TYPES,
        )

    @property
    def purl(self):
        """
        Return the reported PURL shared by all the origin matches, such as the
        "pypi" PURL when a tool reports the "github" one with "pypi" as equivalent.
        """
        common_reported_purls = [
            reported_purl
            for reported_purl in self.reported_purls
            if reported_purl in self.common_purls
        ]
        return (common_reported_purls or self.reported_purls)[0]

    def is_same_package(self, other_origin):
        return bool(self.equivalent_purls & other_origin.equivalent_purls)

    def merge(self, other_origin):
        self.reported_purls.extend(other_origin.reported_purls)
        self.equivalent_purls |= other_origin.equivalent_purls
        self.common_purls &= other_origin.common_purls
        self.tools |= other_origin.tools
        self.has_exact_match = self.has_exact_match or other_origin.has_exact_match


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


def get_status_and_rule(origin):
    """Return the determination status and rule of a single candidate ``origin``."""
    if not origin.has_exact_match:
        return OriginDetermination.Status.NEEDS_REVIEW, NO_EXACT_MATCH_RULE

    # A single tool can miss the other candidates: MatchCode.io stops at the
    # first package matched, and SCANOSS reports one component per file.
    if len(origin.tools) < 2:
        return OriginDetermination.Status.NEEDS_REVIEW, SINGLE_TOOL_RULE

    return OriginDetermination.Status.AUTO_CONFIRMED, CONFIRMED_BY_TWO_TOOLS_RULE


def make_origin_determination(project, resource, origins):
    """Return an unsaved OriginDetermination for the ``resource`` ``origins``."""
    if len(origins) > 1:
        return OriginDetermination(
            project=project,
            resource=resource,
            status=OriginDetermination.Status.NEEDS_REVIEW,
            rule=CONFLICTING_CANDIDATES_RULE,
        )

    origin = origins[0]
    status, rule = get_status_and_rule(origin)
    return OriginDetermination(
        project=project,
        resource=resource,
        purl=origin.purl,
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

        for file_origin in file_origins:
            get_same_package_origins(file_origin, directory_origins)[0].merge(
                file_origin
            )

    for path, origins in origins_by_directory_path.items():
        if origins:
            yield make_origin_determination(project, directories_by_path[path], origins)


def determine_origins(project, batch_size=2000):
    """
    Determine the origin of the ``project`` resources from their origin matches.
    The previous automatic determinations are replaced, while the determinations
    made by a user are kept unchanged.
    Return the number of created determinations.
    """
    determination_count = 0

    with transaction.atomic():
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
            .order_by("resource__path")
        )
        determinations = iter_origin_determinations(project, origin_matches)
        for determination_batch in batched(determinations, batch_size):
            OriginDetermination.objects.bulk_create(determination_batch)
            determination_count += len(determination_batch)

    return determination_count

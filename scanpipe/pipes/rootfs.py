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

import fnmatch
import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

import attr
from commoncode.ignore import default_ignores
from container_inspector.distro import Distro
from packagedcode import plugin_package

from scanpipe import pipes

logger = logging.getLogger(__name__)

SUPPORTED_DISTROS = [
    "alpine",
    "debian",
    "ubuntu",
    "rhel",
    "centos",
    "fedora",
    "sles",
    "opensuse",
    "opensuse-tumbleweed",
    "photon",
    "windows",
]


class DistroNotFound(Exception):
    pass


class DistroNotSupported(Exception):
    pass


@attr.attributes
class Resource:
    rootfs_path = attr.attrib(
        default=None,
        metadata=dict(doc="The rootfs root-relative path for this Resource."),
    )

    location = attr.attrib(
        default=None, metadata=dict(doc="The absolute location for this Resource.")
    )


@attr.attributes
class RootFs:
    """A root filesystem."""

    location = attr.attrib(
        metadata=dict(doc="The root directory location where this rootfs lives.")
    )

    distro = attr.attrib(
        default=None, metadata=dict(doc="The Distro object for this rootfs.")
    )

    def __attrs_post_init__(self, *args, **kwargs):
        self.distro = Distro.from_rootfs(self.location)

    @classmethod
    def from_project_codebase(cls, project):
        """
        Return RootFs objects collected from the project's "codebase" directory.
        Each directory in the input/ is considered as the root of a root filesystem.
        """
        subdirs = [path for path in project.codebase_path.glob("*/") if path.is_dir()]
        for subdir in subdirs:
            rootfs_location = str(subdir.absolute())
            yield RootFs(location=rootfs_location)

    def get_resources(self, with_dir=False):
        """Return a Resource for each file in this rootfs."""
        return get_resources(location=self.location, with_dir=with_dir)

    def get_installed_packages(self, packages_getter):
        """
        Return tuples of (package_url, package) for installed packages found in
        this rootfs layer using the `packages_getter` function or callable.

        The `packages_getter()` function should:

        - Accept a first argument string that is the root directory of
          filesystem of this rootfs

        - Return tuples of (package_url, package) where package_url is a
          package_url string that uniquely identifies a package; while, a `package`
          is an object that represents a package (typically a scancode-
          toolkit packagedcode.models.Package class or some nested mapping with
          the same structure).

        The `packages_getter` function would typically query the system packages
        database, such as an RPM database or similar, to collect the list of
        installed system packages.
        """
        return packages_getter(self.location)


def get_resources(location, with_dir=False):
    """Return the Resource found in the `location` in root directory of a rootfs."""

    def get_res(parent, fname):
        loc = os.path.join(parent, fname)
        rootfs_path = pipes.normalize_path(loc.replace(location, ""))
        return Resource(
            location=loc,
            rootfs_path=rootfs_path,
        )

    for top, dirs, files in os.walk(location):
        for f in files:
            yield get_res(parent=top, fname=f)
        if with_dir:
            for d in dirs:
                yield get_res(parent=top, fname=d)


def create_codebase_resources(project, rootfs):
    """Create the CodebaseResource for a `rootfs` in `project`."""
    for resource in rootfs.get_resources(with_dir=True):
        pipes.make_codebase_resource(
            project=project,
            location=resource.location,
            rootfs_path=resource.rootfs_path,
        )


def has_hash_diff(install_file, codebase_resource):
    """
    Return True if one of available hashes on both `install_file` and
    `codebase_resource`, by hash type, is different.
    For example: Alpine uses SHA1 while Debian uses MD5, we prefer the strongest hash
    that's present.
    """
    hash_types = ["sha512", "sha256", "sha1", "md5"]

    for hash_type in hash_types:
        # Find a suitable hash type that is present on both install_file and
        # codebase_resource, skip otherwise.
        share_hash_type = all(
            [hasattr(install_file, hash_type), hasattr(codebase_resource, hash_type)]
        )

        if not share_hash_type:
            continue

        install_file_sum = getattr(install_file, hash_type)
        codebase_resource_sum = getattr(codebase_resource, hash_type)
        hashes_differ = all(
            [
                install_file_sum,
                codebase_resource_sum,
                install_file_sum != codebase_resource_sum,
            ]
        )
        if hashes_differ:
            return True

    return False


def package_getter(root_dir, **kwargs):
    """Return installed package objects."""
    packages = plugin_package.get_installed_packages(root_dir)
    for package in packages:
        yield package.purl, package


def scan_rootfs_for_system_packages(project, rootfs, detect_licenses=True):
    """
    Given a `project` Project and a `rootfs` RootFs, scan the `rootfs` for
    installed system packages, and create a DiscoveredPackage for each.

    Then for each installed DiscoveredPackage file, check if it exists
    as a CodebaseResource. If exists, relate that CodebaseResource to its
    DiscoveredPackage; otherwise, keep that as a missing file.
    """
    if not rootfs.distro:
        raise DistroNotFound("Distro not found.")

    distro_id = rootfs.distro.identifier
    if distro_id not in SUPPORTED_DISTROS:
        raise DistroNotSupported(f'Distro "{distro_id}" is not supported.')

    logger.info(f"rootfs location: {rootfs.location}")

    installed_packages = rootfs.get_installed_packages(package_getter)

    for i, (purl, package) in enumerate(installed_packages):
        logger.info(f"Creating package #{i}: {purl}")
        created_package = pipes.update_or_create_package(project, package.to_dict())

        installed_files = []
        if hasattr(package, "resources"):
            installed_files = package.resources

        # We have no files for this installed package, we cannot go further.
        if not installed_files:
            logger.info(f"  No installed_files for: {purl}")
            continue

        missing_resources = created_package.missing_resources[:]
        modified_resources = created_package.modified_resources[:]

        codebase_resources = project.codebaseresources.all()

        for install_file in installed_files:
            rootfs_path = pipes.normalize_path(install_file.path)
            logger.info(f"   installed file rootfs_path: {rootfs_path}")

            try:
                codebase_resource = codebase_resources.get(
                    rootfs_path=rootfs_path,
                )
            except ObjectDoesNotExist:
                if rootfs_path not in missing_resources:
                    missing_resources.append(rootfs_path)
                logger.info(f"      installed file is missing: {rootfs_path}")
                continue

            # id list?
            if created_package not in codebase_resource.discovered_packages.all():
                codebase_resource.discovered_packages.add(created_package)
                codebase_resource.status = "system-package"
                logger.info(f"      added as system-package to: {purl}")
                codebase_resource.save()

            if has_hash_diff(install_file, codebase_resource):
                if install_file.path not in modified_resources:
                    modified_resources.append(install_file.path)

        created_package.missing_resources = missing_resources
        created_package.modified_resources = modified_resources
        created_package.save()


def get_resource_with_md5(project, status):
    """
    Return a queryset of CodebaseResource from a `project` that has a `status`,
    a non-empty size, and md5.
    """
    return (
        project.codebaseresources.status(status=status)
        .exclude(md5__exact="")
        .exclude(size__exact=0)
    )


def match_not_analyzed(
    project,
    reference_status="system-package",
    not_analyzed_status="not-analyzed",
):
    """
    Given a `project` Project :
    1. Build an MD5 index of files assigned to a package that has a status of
    `reference_status`
    2. Attempt to match resources with status `not_analyzed_status` to that
    index
    3. Relate each matched CodebaseResource to the matching DiscoveredPackage and
    set its status.
    """
    known_resources = get_resource_with_md5(project=project, status=reference_status)
    known_resources_by_md5_size = {
        (
            r.md5,
            r.size,
        ): r
        for r in known_resources
    }
    count = 0
    matchables = get_resource_with_md5(project=project, status=not_analyzed_status)
    for matchable in matchables:
        key = (
            matchable.md5,
            matchable.size,
        )
        matched = known_resources_by_md5_size.get(key)
        if matched is None:
            continue
        count += 1
        package = matched.discovered_packages.all()[0]
        matchable.status = reference_status
        matchable.discovered_packages.add(package)
        matchable.save()


def tag_empty_codebase_resources(project):
    """Tags empty files as ignored."""
    qs = project.codebaseresources.files().empty()
    qs.filter(status__in=("", "not-analyzed")).update(status="ignored-empty-file")


def tag_uninteresting_codebase_resources(project):
    """
    Check any file that doesn’t belong to any system package and determine if it's:
    - A temp file
    - Generated
    - Log file of sorts (such as var) using few heuristics
    """
    uninteresting_and_transient = (
        "/tmp/",
        "/etc/",
        "/proc/",
        "/dev/",
        "/run/",
        "/lib/apk/db/",  # alpine specific
    )

    lookups = Q()
    for segment in uninteresting_and_transient:
        lookups |= Q(rootfs_path__startswith=segment)

    qs = project.codebaseresources.no_status()
    qs.filter(lookups).update(status="ignored-not-interesting")


def tag_ignorable_codebase_resources(project):
    """
    Tag codebase resource using the glob patterns from commoncode.ignore of
    ignorable files/directories, if their paths match an ignorable pattern.
    """
    lookups = Q()
    for pattern in default_ignores.keys():
        # Translate glob pattern to regex
        translated_pattern = fnmatch.translate(pattern)
        # PostgreSQL does not like parts of Python regex
        if translated_pattern.startswith("(?s"):
            translated_pattern = translated_pattern.replace("(?s", "(?")
        lookups |= Q(rootfs_path__icontains=pattern)
        lookups |= Q(rootfs_path__iregex=translated_pattern)

    qs = project.codebaseresources.no_status()
    qs.filter(lookups).update(status="ignored-default-ignores")


def tag_data_files_with_no_clues(project):
    """
    Tags CodebaseResources that have a file type of `data` and no detected clues
    to be uninteresting.
    """
    lookup = Q(
        file_type="data",
        copyrights=[],
        holders=[],
        authors=[],
        licenses=[],
        license_expressions=[],
        emails=[],
        urls=[],
    )

    qs = project.codebaseresources
    qs.filter(lookup).update(status="ignored-data-file-no-clues")


def tag_media_files_as_uninteresting(project):
    """Tags CodebaseResources that are media files to be uninteresting."""
    qs = project.codebaseresources.no_status()
    qs.filter(is_media=True).update(status="ignored-media-file")

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

import logging
import os
from functools import partial

import attr
from container_inspector.distro import Distro

from scanpipe import pipes
from scanpipe.models import CodebaseResource
from scanpipe.pipes import alpine
from scanpipe.pipes import debian

logger = logging.getLogger(__name__)

PACKAGE_GETTER_BY_DISTRO = {
    "alpine": alpine.package_getter,
    "debian": partial(debian.package_getter, distro="debian"),
    "ubuntu": partial(debian.package_getter, distro="ubuntu"),
}


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
    """
    A root filesystem.
    """

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
        Yield RootFs objects collected from the project "codebase" directory.
        """
        # for now we do a dumb thing:
        # each directory in input is considered as the root of a rootfs

        subdirs = [p for p in project.codebase_path.glob("*/") if p.is_dir()]
        for subdir in subdirs:
            rootfs_location = str(subdir.absolute())
            yield RootFs(location=rootfs_location)

    def get_resources(self, with_dir=False):
        """
        Yield a Resource for each file in this rootfs.
        """
        return get_resources(location=self.location, with_dir=with_dir)

    def get_installed_packages(self, packages_getter):
        """
        Yield tuples of (package_url, package) for installed packages found in
        this rootfs layer using the `packages_getter` function or callable.

        The `packages_getter()` function should:

        - accept a first argument string that is the root directory of
          filesystem of this the rootfs

        - yield tuples of (package_url, package) where package_url is a
          package_url string that uniquely identifies the package  and `package`
          is some object that represents the package (typically a scancode-
          toolkit packagedcode.models.Package class or some nested mapping with
          the same structure).

        An `packages_getter` function would typically query the system packages
        database (such as an RPM database or similar) to collect the list of
        installed system packages.
        """
        return packages_getter(self.location)


def get_resources(location, with_dir=False):
    """
    Yield the Resource found in the `location` in root directory of a rootfs.
    """

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
    """
    Create the CodebaseResource for a `rootfs` RootFs in `project` Project.
    """
    for resource in rootfs.get_resources():
        pipes.make_codebase_resource(
            project=project,
            location=resource.location,
            rootfs_path=resource.rootfs_path,
        )


def scan_rootfs_for_system_packages(project, rootfs, detect_licenses=True):
    """
    Given a `project` Project and an `rootfs` RootFs, scan the `rootfs` for
    installed system packages. Create a DiscoveredPackage for each.

    Then for each installed DiscoveredPackage installed file, check if it exists
    as a CodebaseResource and relate that CodebaseResource to its
    DiscoveredPackage or keep that as a missing file.
    """
    distro_id = rootfs.distro.identifier

    if distro_id not in PACKAGE_GETTER_BY_DISTRO:
        raise NotImplementedError(f'Distro "{distro_id}" is not supported.')

    package_getter = partial(
        PACKAGE_GETTER_BY_DISTRO[distro_id],
        distro=distro_id,
        detect_licenses=detect_licenses,
    )

    installed_packages = rootfs.get_installed_packages(package_getter)

    for i, (purl, package) in enumerate(installed_packages):
        logger.info(f"Creating package #{i}: {purl}")
        created_package = pipes.update_or_create_package(project, package.to_dict())

        # We have no files for this installed package, we cannot go further.
        if not package.installed_files:
            logger.info(f"  No installed_files for: {purl}")
            continue

        missing_resources = created_package.missing_resources[:]
        modified_resources = created_package.modified_resources[:]

        codebase_resources = CodebaseResource.objects.project(project)

        for install_file in package.installed_files:
            rootfs_path = pipes.normalize_path(install_file.path)
            logger.info(f"   installed file rootfs_path: {rootfs_path}")

            try:
                codebase_resource = codebase_resources.get(
                    rootfs_path=rootfs_path,
                )
            except CodebaseResource.DoesNotExist:
                if rootfs_path not in missing_resources:
                    missing_resources.append(rootfs_path)
                logger.info(f"      installed file is missing: {rootfs_path}")
                continue

            if created_package not in codebase_resource.discovered_packages:
                codebase_resource.discovered_packages.add(created_package)
                codebase_resource.status = "system-package"
                logger.info(f"      added as system-package to: {purl}")
                codebase_resource.save()

            if (
                (
                    install_file.sha512
                    and codebase_resource.sha512
                    and codebase_resource.sha512 != install_file.sha512
                )
                or (
                    install_file.sha256
                    and codebase_resource.sha256
                    and codebase_resource.sha256 != install_file.sha256
                )
                or (
                    install_file.sha1
                    and codebase_resource.sha1
                    and codebase_resource.sha1 != install_file.sha1
                )
                or (
                    install_file.md5
                    and codebase_resource.md5
                    and codebase_resource.md5 != install_file.md5
                )
            ):
                # Alpine uses SHA1 while Debian uses MD5, we prefer te strongest
                # hash that's present
                if install_file.path not in modified_resources:
                    modified_resources.append(install_file.path)

        created_package.missing_resources = missing_resources
        created_package.modified_resources = modified_resources
        created_package.save()


def get_resource_with_md5(project, status):
    """
    Return a queryset of CodebaseResource from `project` that have `status` and
    a non-empty size and md5.
    """
    return (
        project.codebaseresources.status(
            status=status,
        )
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
    1. build an MD5 index of files assigned to a package that have a status of
    `reference_status`
    2. attempt to match resources with status `not_analyzed_status` to that
    index
    3. relate each matched CodebaseResource to matching DiscoveredPackage and
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
    """
    Tag remaining empty files as ignored
    """
    project.codebaseresources.select_for_update().filter(
        type__exact="file",
        status__in=(
            "",
            "not-analyzed",
        ),
        size__isnull=True,
    ).update(status="ignored-empty-file")


def tag_uninteresting_codebase_resources(project):
    """
    Check remaining files not from a system package and determine if this is:
    - a temp file
    - generated
    - log file of sorts (such as var) using a few heuristics
    """
    uninteresting_and_transient = (
        "/tmp/",
        "/etc/",
        "/var/",
        "/proc/",
        "/dev/",
        "/run/",
    ) + (
        # alpine specific
        "/lib/apk/db/",
    )

    qs = project.codebaseresources.no_status()

    for codebase_resource in qs:
        if codebase_resource.rootfs_path.startswith(uninteresting_and_transient):
            codebase_resource.status = "ignored-not-interesting"
            codebase_resource.save()

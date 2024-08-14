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

from django.db.models import Q

from packagedcode import win_reg
from packagedcode.models import Package

from scanpipe import pipes
from scanpipe.pipes import flag


def package_getter(root_dir, **kwargs):
    """Return installed package objects."""
    packages = win_reg.get_installed_packages(root_dir)
    for package in packages:
        yield package.purl, package


def flag_uninteresting_windows_codebase_resources(project):
    """Flag known uninteresting files as uninteresting."""
    uninteresting_files = (
        "DefaultUser_Delta",
        "Sam_Delta",
        "Security_Delta",
        "Software_Delta",
        "System_Delta",
        "NTUSER.DAT",
        "desktop.ini",
        "BBI",
        "BCD-Template",
        "DEFAULT",
        "DRIVERS",
        "ELAM",
        "SAM",
        "SECURITY",
        "SOFTWARE",
        "SYSTEM",
        "system.ini",
    )

    uninteresting_file_extensions = (
        ".lnk",
        ".library-ms",
        ".LOG",
        ".inf_loc",
        ".NLS",
        ".dat",
        ".pem",
        ".xrm-ms",
        ".sql",
        ".mof",
        ".mfl",
        ".manifest",
        ".inf",
        ".cat",
        ".efi",
        ".evtx",
        ".cat",
        ".pnf",
    )

    lookups = Q()
    for file_name in uninteresting_files:
        lookups |= Q(rootfs_path__iendswith=file_name)
    for file_extension in uninteresting_file_extensions:
        lookups |= Q(extension__icontains=file_extension)

    qs = project.codebaseresources.no_status()
    qs.filter(lookups).update(status=flag.IGNORED_NOT_INTERESTING)


def flag_installed_package_files(project, root_dir_pattern, package, q_objects=None):
    """
    For all CodebaseResources from `project` whose `rootfs_path` starts with
    `root_dir_pattern`, add `package` to the discovered_packages of each
    CodebaseResource and set the status.
    """
    qs = project.codebaseresources.no_status()
    lookup = Q(rootfs_path__startswith=root_dir_pattern)

    # If there are Q() objects in `q_objects`, then those Q() objects are chained
    # to the initial query `lookup` using AND to allow a more specific query for
    # package files.
    for q_object in q_objects or []:
        lookup &= q_object

    installed_package_files = qs.filter(lookup)
    # If we find files whose names start with `root_dir_pattern`, we consider
    # these files to be part of the Package `package` and tag these files as such.
    if installed_package_files:
        created_package = pipes.update_or_create_package(project, package.to_dict())
        for installed_package_file in installed_package_files:
            installed_package_file.discovered_packages.add(created_package)
            installed_package_file.update(status=flag.INSTALLED_PACKAGE)


def _flag_python_software(project):
    qs = project.codebaseresources.no_status()
    python_root_pattern = r"(?P<root_path>^/(Files/)?Python(?P<version>\d+)?)/.*$"
    python_root_pattern_compiled = re.compile(python_root_pattern)
    python_resources = qs.filter(rootfs_path__regex=r"(^/(Files/)?Python(\d+)?)/.*$")

    python_versions_by_path = {}
    for python_resource in python_resources:
        match = python_root_pattern_compiled.match(python_resource.rootfs_path)
        if not match:
            continue

        python_root_path = match.group("root_path")
        if python_root_path in python_versions_by_path:
            continue

        version = match.group("version")
        if not version:
            version = "nv"
        if version != "nv":
            version = ".".join(digit for digit in version)

        python_versions_by_path[python_root_path] = version

    # We do not want to tag the files in the `site-packages` directory as being
    # from Python proper. The packages found here are oftentimes third-party
    # packages from outside the Python foundation
    q_objects = [~Q(rootfs_path__icontains="site-packages")]

    for python_path, python_version in python_versions_by_path.items():
        python_package = Package(
            type="windows-program",
            name="Python",
            version=python_version,
            declared_license_expression="python",
            copyright="Copyright (c) Python Software Foundation",
            homepage_url="https://www.python.org/",
        )
        flag_installed_package_files(
            project=project,
            root_dir_pattern=python_path,
            package=python_package,
            q_objects=q_objects,
        )


def _flag_openjdk_software(project):
    qs = project.codebaseresources.no_status()
    openjdk_root_pattern = (
        r"^(?P<root_path>/(Files/)?(open)?jdk(-(?P<version>(\d*)(\.\d+)*))*)/.*$"
    )
    openjdk_root_pattern_compiled = re.compile(openjdk_root_pattern)
    openjdk_resources = qs.filter(
        rootfs_path__regex=r"^(/(Files/)?(open)?jdk(-((\d*)(\.\d+)*))*)/.*$"
    )

    openjdk_versions_by_path = {}
    for openjdk_codebase_resource in openjdk_resources:
        match = openjdk_root_pattern_compiled.match(
            openjdk_codebase_resource.rootfs_path
        )
        if not match:
            continue

        openjdk_root_path = match.group("root_path")
        if openjdk_root_path in openjdk_versions_by_path:
            continue

        openjdk_version = match.group("version")
        if not openjdk_version:
            openjdk_version = "nv"

        openjdk_versions_by_path[openjdk_root_path] = openjdk_version

    for openjdk_path, openjdk_version in openjdk_versions_by_path.items():
        license_expression = "gpl-2.0 WITH oracle-openjdk-classpath-exception-2.0"
        openjdk_package = Package(
            type="windows-program",
            name="OpenJDK",
            version=openjdk_version,
            declared_license_expression=license_expression,
            copyright="Copyright (c) Oracle and/or its affiliates",
            homepage_url="http://openjdk.java.net/",
        )
        flag_installed_package_files(
            project=project,
            root_dir_pattern=openjdk_path,
            package=openjdk_package,
        )


def flag_known_software(project):
    """
    Find Windows software in `project` by checking CodebaseResources
    to see if their rootfs_path is under a known software root directory. If
    there are CodebaseResources that are under a known software root directory,
    a DiscoveredPackage is created for that software package and all files under
    that software package's root directory are considered installed files for
    that package.

    Currently, we are only checking for Python and openjdk in Windows Docker
    image layers.

    If a version number cannot be determined for an installed software Package,
    then a version number of "nv" will be set.
    """
    _flag_python_software(project)
    _flag_openjdk_software(project)


PROGRAM_FILES_DIRS_TO_IGNORE = (
    "Common Files",
    "Microsoft",
)


def flag_program_files(project):
    """
    Report all subdirectories of Program Files and Program Files (x86) as Packages.

    If a Package is detected in this manner, then we will attempt to determine
    the version from the path. If a version cannot be determined, a version of
    `nv` will be set for the Package.
    """
    qs = project.codebaseresources.no_status()
    # Get all files from Program Files and Program Files (x86)
    program_files_subdir_pattern = (
        r"(?P<program_files_subdir>^.*Program Files( \(x86\))?/(?P<dirname>[^/]+))"
    )
    program_files_subdir_pattern_compiled = re.compile(program_files_subdir_pattern)
    program_files_resources = qs.filter(
        rootfs_path__regex=r"^.*/Program Files( \(x86\))?"
    )

    program_files_dirname_by_path = {}
    for program_file in program_files_resources:
        match = program_files_subdir_pattern_compiled.match(program_file.rootfs_path)
        if not match:
            continue

        program_files_subdir = match.group("program_files_subdir")
        dirname = match.group("dirname")

        skip_conditions = [
            program_files_subdir in program_files_dirname_by_path,
            dirname.lower() in map(str.lower, PROGRAM_FILES_DIRS_TO_IGNORE),
        ]
        if any(skip_conditions):
            continue

        program_files_dirname_by_path[program_files_subdir] = dirname

    for root_dir, root_dir_name in program_files_dirname_by_path.items():
        package = Package(type="windows-program", name=root_dir_name, version="nv")
        flag_installed_package_files(
            project=project,
            root_dir_pattern=root_dir,
            package=package,
        )

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

from django.db.models import Q

from scanpipe import pipes

from packagedcode import win_reg
from packagedcode.models import Package


def package_getter(root_dir, **kwargs):
    """
    Yield installed package objects.
    """
    packages = win_reg.get_installed_packages(root_dir)
    for package in packages:
        yield package.purl, package


def tag_uninteresting_windows_codebase_resources(project):
    """
    Tag known uninteresting files as uninteresting
    """
    uninteresting_files = (
        'DefaultUser_Delta',
        'Sam_Delta',
        'Security_Delta',
        'Software_Delta',
        'System_Delta',
        'NTUSER.DAT',
        'desktop.ini',
    )

    uninteresting_file_extensions = (
        '.lnk',
        '.library-ms',
        '.LOG1',
        '.LOG2',
    )

    lookups = Q()
    for file_name in uninteresting_files:
        lookups |= Q(path__endswith=file_name)
    for file_extension in uninteresting_file_extensions:
        lookups |= Q(path__endswith=file_extension)

    qs = project.codebaseresources.no_status()
    qs.filter(lookups).update(status="ignored-not-interesting")


def tag_installed_package_files(project, root_dir_pattern, package):
    qs = project.codebaseresources.no_status()
    installed_package_files = qs.filter(rootfs_path__regex=root_dir_pattern)
    # If we find files whose names start with `root_dir_pattern`, we consider
    # these files to be part of the Package `package` and tag these files as
    # such
    if installed_package_files:
        created_package = pipes.update_or_create_package(project=project, package_data=package.to_dict())
        for installed_package_file in installed_package_files:
            installed_package_file.discovered_packages.add(created_package)
            installed_package_file.status = "system-package"
            installed_package_file.save()
        created_package.save()


def tag_known_software(project):
    python_root_directory_name_pattern = r"/Files/Python\d?\d?"
    python_package = Package(
            type="windows-program",
            name="Python",
            # TODO: find version from path
            version="nv",
            license_expression="python",
            copyright="Copyright (c) Python Software Foundation",
            homepage_url="https://www.python.org/"
    )
    tag_installed_package_files(
        project=project,
        root_dir_pattern=python_root_directory_name_pattern,
        package=python_package
    )

    openjdk_root_directory_name_pattern = r"/Files/jdk-\d\d?.?\d?.?\d?"
    openjdk_package = Package(
        name="OpenJDK",
        license_expression="gpl-2.0 WITH oracle-openjdk-classpath-exception-2.0",
        copyright="Copyright (c) Oracle and/or its affiliates",
        homepage_url="http://openjdk.java.net/",
    )
    tag_installed_package_files(
        project=project,
        root_dir_pattern=openjdk_root_directory_name_pattern,
        package=openjdk_package
    )

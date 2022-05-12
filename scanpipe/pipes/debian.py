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

import os

import attr
from commoncode import filetype
from debian_inspector import debcon
from packagedcode import debian
from packagedcode import debian_copyright
from packagedcode import models
from packageurl import PackageURL


@attr.s()
class PackageFile(models.ModelMixin):
    """
    A file that belongs to a package.
    """

    path = models.String(
        label="Path of this installed file",
        help="The path of this installed file either relative to a rootfs "
        "(typical for system packages) or a path in this scan (typical "
        "for application packages).",
        repr=True,
    )

    size = models.Integer(label="file size", help="size of the file in bytes")

    sha1 = models.String(
        label="SHA1 checksum", help="SHA1 checksum for this file in hexadecimal"
    )

    md5 = models.String(
        label="MD5 checksum", help="MD5 checksum for this file in hexadecimal"
    )

    sha256 = models.String(
        label="SHA256 checksum", help="SHA256 checksum for this file in hexadecimal"
    )

    sha512 = models.String(
        label="SHA512 checksum", help="SHA512 checksum for this file in hexadecimal"
    )


def package_getter(root_dir, distro="debian", detect_licenses=True, **kwargs):
    """
    Returns installed package objects. Optionally detect licenses in a Debian
    copyright file for each package.
    """
    packages = get_installed_packages(
        root_dir=root_dir, distro=distro, detect_licenses=detect_licenses
    )
    for package in packages:
        yield package.purl, package


def get_installed_packages(root_dir, distro="debian", detect_licenses=False, **kwargs):
    """
    Yield installed Package objects given a ``root_dir`` rootfs directory.
    """

    base_status_file_loc = os.path.join(root_dir, "var/lib/dpkg/status")
    base_statusd_loc = os.path.join(root_dir, "var/lib/dpkg/status.d/")

    if os.path.exists(base_status_file_loc):
        var_lib_dpkg_info_dir = os.path.join(root_dir, "var/lib/dpkg/info/")

        for package in parse_status_file(base_status_file_loc, distro=distro):
            populate_installed_files(package, var_lib_dpkg_info_dir)
            if detect_licenses:
                copyright_location = get_copyright_file_path(package, root_dir)
                dc = debian_copyright.parse_copyright_file(copyright_location)
                if dc:
                    package.declared_license = dc.get_declared_license(
                        filter_duplicates=True,
                        skip_debian_packaging=True,
                    )
                    package.license_expression = dc.get_license_expression(
                        skip_debian_packaging=True,
                        simplify_licenses=True,
                    )
                    package.copyright = dc.get_copyright(
                        skip_debian_packaging=True,
                        unique_copyrights=True,
                    )
            yield package

    elif os.path.exists(base_statusd_loc):
        for root, dirs, files in os.walk(base_statusd_loc):
            for f in files:
                status_file_loc = os.path.join(root, f)
                for package in parse_status_file(status_file_loc, distro=distro):
                    yield package


def parse_status_file(location, distro="debian"):
    """
    Yield Debian Package objects from a dpkg `status` file or None.
    """
    if not os.path.exists(location):
        raise FileNotFoundError(
            "[Errno 2] No such file or directory: {}".format(repr(location))
        )
    if not filetype.is_file(location):
        raise Exception(f"Location is not a file: {location}")
    for debian_pkg_data in debcon.get_paragraphs_data_from_file(location):
        yield debian.build_package_data(
            debian_data=debian_pkg_data, datasource_id="debian-pipe", distro=distro
        )


def populate_installed_files(package, var_lib_dpkg_info_dir):
    """
    Populate the installed_file  attribute given a `var_lib_dpkg_info_dir`
    path to a Debian /var/lib/dpkg/info directory.
    """
    package.installed_files = get_list_of_installed_files(
        package, var_lib_dpkg_info_dir
    )


def get_list_of_installed_files(package, var_lib_dpkg_info_dir):
    """
    Return a list of InstalledFile given a `var_lib_dpkg_info_dir` path to a
    Debian /var/lib/dpkg/info directory where <package>.list and/or
    <package>.md5sums files can be found for a package name.
    We first use the .md5sums file and switch to the .list file otherwise.
    The .list files also contains directories.
    """

    # Multi-Arch can be: foreign, same, allowed or empty
    # We only need to adjust the md5sum path in the case of `same`
    if package.extra_data.get("multi_arch", "") == "same":
        arch = ":{}".format(package.qualifiers.get("architecture"))
    else:
        arch = ""

    package_md5sum = "{}{}.md5sums".format(package.name, arch)
    md5sum_file = os.path.join(var_lib_dpkg_info_dir, package_md5sum)

    package_list = "{}{}.list".format(package.name, arch)
    list_file = os.path.join(var_lib_dpkg_info_dir, package_list)

    has_md5 = os.path.exists(md5sum_file)
    has_list = os.path.exists(list_file)

    if not (has_md5 or has_list):
        return []

    installed_files = []
    directories = set()
    if has_md5:
        with open(md5sum_file) as info_file:
            for line in info_file:
                line = line.strip()
                if not line:
                    continue
                md5sum, _, path = line.partition(" ")
                md5sum = md5sum.strip()

                path = path.strip()
                if not path.startswith("/"):
                    path = "/" + path

                # we ignore dirs in general, and we ignore these that would
                # be created a plain dir when we can
                if path in ignored_root_dirs:
                    continue

                installed_file = PackageFile(path=path, md5=md5sum)

                installed_files.append(installed_file)
                directories.add(os.path.dirname(path))

    elif has_list:
        with open(list_file) as info_file:
            for line in info_file:
                line = line.strip()
                if not line:
                    continue
                md5sum = None
                path = line

                path = path.strip()
                if not path.startswith("/"):
                    path = "/" + path

                # we ignore dirs in general, and we ignore these that would
                # be created a plain dir when we can
                if path in ignored_root_dirs:
                    continue

                installed_file = PackageFile(path=path, md5=md5sum)
                if installed_file not in installed_files:
                    installed_files.append(installed_file)
                directories.add(os.path.dirname(path))

    # skip directories when possible
    installed_files = [f for f in installed_files if f.path not in directories]

    return installed_files


def build_package(package_data, distro="debian"):
    """
    Return a Package object from a package_data mapping (from a dpkg status file)
    or None.
    """
    # construct the package
    package = models.PackageData(type="deb")
    package.namespace = distro

    # add debian-specific package 'qualifiers'
    package.qualifiers = dict(
        [
            ("arch", package_data.get("architecture")),
        ]
    )

    package.set_multi_arch(package_data.get("multi-arch"))

    # mapping of top level `status` file items to the Package object field name
    plain_fields = [
        ("description", "description"),
        ("homepage", "homepage_url"),
        ("installed-size", "size"),
        ("package", "name"),
        ("version", "version"),
        ("maintainer", "maintainer"),
    ]

    for source, target in plain_fields:
        value = package_data.get(source)
        if value:
            if isinstance(value, str):
                value = value.strip()
            if value:
                setattr(package, target, value)

    # mapping of top level `status` file items to a function accepting as
    # arguments the package.json element value and returning an iterable of key,
    # values Package Object to update
    field_mappers = [
        ("section", keywords_mapper),
        ("source", source_packages_mapper),
        # ('depends', dependency_mapper),
    ]

    for source, func in field_mappers:
        value = package_data.get(source) or None
        if value:
            func(value, package)

    # parties_mapper() need mutiple fields:
    parties_mapper(package_data, package)

    return package


def keywords_mapper(keyword, package):
    """
    Add `section` info as a list of keywords to a DebianPackage.
    """
    package.keywords = [keyword]
    return package


def source_packages_mapper(source, package):
    """
    Add `source` info as a list of `purl`s to a DebianPackage.
    """
    source_pkg_purl = PackageURL(
        type=package.type, name=source, namespace=package.namespace
    ).to_string()

    package.source_packages = [source_pkg_purl]

    return package


def parties_mapper(package_data, package):
    """
    add
    """
    parties = []

    maintainer = package_data.get("maintainer")
    orig_maintainer = package_data.get("original_maintainer")

    if maintainer:
        parties.append(models.Party(role="maintainer", name=maintainer))

    if orig_maintainer:
        parties.append(models.Party(role="original_maintainer", name=orig_maintainer))

    package.parties = parties

    return package


def get_copyright_file_path(debian_package, root_dir):
    """
    Given a root_dir path to a filesystem root, return the path to a copyright file
    for this Package
    """
    # We start by looking for a copyright file stored in a directory named after the
    # package name. Otherwise we look for a copyright file stored in a source package
    # name.
    candidate_names = [debian_package.name]
    candidate_names.extend(
        PackageURL.from_string(sp).name for sp in debian_package.source_packages
    )

    copyright_file = os.path.join(root_dir, "usr/share/doc/{}/copyright")

    for name in candidate_names:
        copyright_loc = copyright_file.format(name)
        if os.path.exists(copyright_loc):
            return copyright_loc


ignored_root_dirs = {
    "/.",
    "/bin",
    "/boot",
    "/cdrom",
    "/dev",
    "/etc",
    "/etc/skel",
    "/home",
    "/lib",
    "/lib32",
    "/lib64",
    "/lost+found",
    "/mnt",
    "/media",
    "/opt",
    "/proc",
    "/root",
    "/run",
    "/usr",
    "/sbin",
    "/snap",
    "/sys",
    "/tmp",
    "/usr",
    "/usr/games",
    "/usr/include",
    "/usr/sbin",
    "/usr/share/info",
    "/usr/share/man",
    "/usr/share/misc",
    "/usr/src",
    "/var",
    "/var/backups",
    "/var/cache",
    "/var/lib/dpkg",
    "/var/lib/misc",
    "/var/local",
    "/var/lock",
    "/var/log",
    "/var/opt",
    "/var/run",
    "/var/spool",
    "/var/tmp",
    "/var/lib",
}

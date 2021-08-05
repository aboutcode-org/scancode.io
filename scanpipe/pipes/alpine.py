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


import json
from shutil import copytree

from fetchcode import fetch
from fetchcode.vcs.git import fetch_via_git
from packagedcode import alpine

from scanpipe.models import DiscoveredPackage

APORTS_URL = "https://gitlab.alpinelinux.org/alpine/aports.git"
APORTS_DIR_NAME = "aports"
APORTS_SUBDIRS = ["main", "non-free", "testing", "community", "unmaintained"]


def download_or_checkout_aports(aports_dir_path, alpine_version, commit_id=None):
    """
    Download aports repository and it's branch based on `alpine_version`.
    Checkout to a branch (alpine version).
    If `commit_id` is provided also checkout to a commit.
    Return `aports_dir_path` if checkout(s) succeded. #TODO Proper fetchcode patch required (extending #54)
    """
    major, minor = alpine_version.split(".")[:2]
    aports_dir_path = str(aports_dir_path / APORTS_DIR_NAME)
    fetch_via_git(
        url=f"git+{APORTS_URL}@{major}.{minor}-stable", location=aports_dir_path
    )
    if commit_id:
        fetch_via_git(url=f"git+{APORTS_URL}@{commit_id}", location=aports_dir_path)
    return aports_dir_path


def get_unscanned_packages_from_db(project, alpine_versions):
    """
    Return an iterator of 5-tuples (alpine_version, commit_id, scan_target_path, scan_result_path, package) where:
    `alpine_version` is an alpine version from which a package comes from (obtained from `alpine_versions` dict),
    `commit_id` is an id of aports repository commit that added corresponding version of a package,
    `scan_target_path` is a path of the directory on which a scan will be performed,
    `scan_result_path` is a path of the scan result json file,
    `package` is a DiscoveredPackage instance that belongs to a `project` with an alpine package type.
    The returned iterator contains not-a-subpackage alpine packages that don't have an existing scan result file.
    """
    for package in DiscoveredPackage.objects.filter(project=project, type="alpine"):
        scan_id = f"{package.name}_{package.version}"
        scan_result_path = project.output_path / (scan_id + ".json")
        alpine_version = alpine_versions.get(package.extra_data["image_id"])
        commit_id = package.vcs_url.split("id=")[1]
        scan_target_path = project.tmp_path / scan_id
        not_a_subpackage = (
            not package.source_packages or package.source_packages[0] in package.purl
        )
        scan_result_nonexistent = not scan_result_path.exists()
        if not_a_subpackage and scan_result_nonexistent:
            yield alpine_version, commit_id, scan_target_path, scan_result_path, package


def prepare_scan_dir(package_name, scan_target_path, aports_dir_path=None):
    """
    A function to gather all the package's source files in `scan_target_path`.
    Source files of an alpine package are obtained from it's aports directory whose location has to be guessed.
    Such directory is present in one of the five aports repository subdirectories (main, non-free, testing, community, unmaintained).
    It's name is the same as the value of the corresponding package's `name` field (hence the `package_name` parameter).
    Here are some path examples:
    .../aports/main/acf-db
    .../aports/non-free/mongodb
    Inside, there are some extra files (patches) and an APKBUILD which contains urls to source tarballs.
    The function copies all these files (including APKBUILD) and downloads all the source tarballs to `scan_target_path`.
    The default value of `aports_dir_path` is set to the parent of the `scan_target_path`.
    If the package's aports path is found/guessed and it's also not empty the returned value is `scan_target_path`.
    """
    if aports_dir_path is None:
        aports_dir_path = scan_target_path.parent
    for subdir_name in APORTS_SUBDIRS:
        apkbuild_dir = aports_dir_path / APORTS_DIR_NAME / subdir_name / package_name
        if not apkbuild_dir.exists():
            continue
        if not any(apkbuild_dir.iterdir()):
            break
        copytree(apkbuild_dir, scan_target_path)
        package_sources = (
            alpine.parse_apkbuild(scan_target_path / "APKBUILD")
            .to_dict()
            .get("extra_data")
            .get("sources")
            or []
        )
        for source in package_sources:
            source_url = source.get("url")
            if source_url:
                fetch(source_url, scan_target_path)
        return scan_target_path


def extract_summary_fields(scan_result_path, summary_field_names):
    """
    Having a scancode result file extract all the values from the `summary` section of the scan result file (`scan_result_path`).
    Put them in the arrays inside the `result` object (result[`field_name`]).
    Return `result`.
    """
    scan_result = open(scan_result_path)
    summaries = json.load(scan_result)["summary"]
    scan_result.close()
    result = {}
    for field_name in summary_field_names:
        values = (summary["value"] for summary in summaries.get(field_name, []))
        result[field_name] = [v for v in values if v]
    return result


def package_getter(root_dir, **kwargs):
    """
    Returns installed package objects.
    """
    packages = alpine.get_installed_packages(root_dir)
    for package in packages:
        yield package.purl, package

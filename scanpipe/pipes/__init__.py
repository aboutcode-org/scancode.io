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

import traceback
from datetime import datetime
from functools import partial
from pathlib import Path

from django.db.models import Count
from django.forms import model_to_dict

from commoncode import fileutils
from packageurl import normalize_qualifiers
from scancode import api as scancode_api

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import ProjectError


def make_codebase_resource(project, location, rootfs_path=None):
    """
    Get or create and return a CodebaseResource with `location` absolute path
    for the `project` Project.

    The `location` of this Resource must be rooted in `project.codebase_path`.

    `rootfs_path` is an optional path relative to a rootfs root within an
    Image/VM filesystem context. e.g.: "/var/log/file.log"

    All paths use the POSIX separators.
    """
    location = location.rstrip("/")
    codebase_path = str(project.codebase_path)
    assert location.startswith(
        codebase_path
    ), f"Location: {location} is not under project/codebase: {codebase_path}"

    path = location.replace(codebase_path, "")

    resource_defaults = {}
    if rootfs_path:
        resource_defaults["rootfs_path"] = rootfs_path
    resource_defaults.update(get_resource_info(location=location))

    codebase_resource, _created = CodebaseResource.objects.get_or_create(
        project=project,
        path=path,
        defaults=resource_defaults,
    )
    return codebase_resource


def get_resource_info(location):
    """
    Return a mapping suitable for the creation of a new CodebaseResource
    """
    file_info = {}
    is_symlink = Path(location).is_symlink()
    is_file = Path(location).is_file()

    if is_symlink:
        resource_type = CodebaseResource.Type.SYMLINK
        file_info["status"] = "symlink"
    elif is_file:
        resource_type = CodebaseResource.Type.FILE
    else:
        resource_type = CodebaseResource.Type.DIRECTORY

    file_info.update(
        {
            "type": resource_type,
            "name": fileutils.file_base_name(location),
            "extension": fileutils.file_extension(location),
        }
    )

    if is_symlink:
        return file_info

    # Missing fields on CodebaseResource model returned by `get_file_info`.
    unsupported_fields = [
        "is_binary",
        "is_text",
        "is_archive",
        "is_media",
        "is_source",
        "is_script",
        "date",
    ]

    other_info = scancode_api.get_file_info(location)

    # Skip unsupported_fields
    # Skip empty values to avoid null vs. '' conflicts
    other_info = {
        field_name: value
        for field_name, value in other_info.items()
        if field_name not in unsupported_fields and value
    }

    file_info.update(other_info)

    return file_info


def update_or_create_package(project, package_data):
    """
    Get and update or create a DiscoveredPackage then return it.
    Use the `project` and `package_data` mapping to lookup and create the
    DiscoveredPackage using its Package URL as a unique key.
    """
    # make a copy
    package_data = dict(package_data or {})
    if not package_data:
        return

    # keep only known fields with values
    package_data = {
        field_name: value
        for field_name, value in package_data.items()
        if field_name in DiscoveredPackage.model_fields() and value
    }

    purl_fields = ("type", "namespace", "name", "version", "qualifiers", "subpath")
    purl_data = {}
    for k in purl_fields:
        # get and remove
        v = package_data.pop(k, "")
        if k == "qualifiers":
            v = normalize_qualifiers(v, encode=True)
        purl_data[k] = v or ""

    if not purl_data:
        raise Exception(f"Package without any Package URL fields: {package_data}")

    # if 'type' not in purl_data and 'name' not in purl_data:
    #     raise Exception(
    #         f'Package missing type and name Package URL fields: {package_data}')

    # FIXME: we should also consider the download URL as part of the key
    # Ensure a purl is treated like if this is the UNIQUE key to a package.
    dp, created = DiscoveredPackage.objects.get_or_create(
        project=project, **purl_data, defaults=package_data
    )

    if not created:
        # update/merge records since we have an existing record
        dp_fields = DiscoveredPackage.model_fields()
        has_updates = False
        for field_name, value in package_data.items():
            if field_name not in dp_fields or not value:
                continue
            existing_value = getattr(dp, field_name, "")
            if not existing_value:
                setattr(dp, field_name, value)
                has_updates = True
            elif existing_value != value:
                # TODO: handle this case
                pass
        if has_updates:
            dp.save()

    return dp


def scan_for_application_packages(project):
    """
    Run a package scan on remainder of files without status.
    """
    queryset = CodebaseResource.objects.project(project).no_status()

    for codebase_resource in queryset:
        package_info = scancode_api.get_package_info(codebase_resource.location)
        packages = package_info.get("packages", [])
        if packages:
            for package in packages:
                DiscoveredPackage.create_for_resource(package, codebase_resource)
            codebase_resource.status = "application-package"
            codebase_resource.save()


def scan_file(location):
    """
    Run a license, copyright, email, and url scan functions on provided
    `location`.
    """
    scan_functions = [
        scancode_api.get_copyrights,
        partial(scancode_api.get_licenses, include_text=True),
        scancode_api.get_emails,
        scancode_api.get_urls,
    ]

    scan_errors = []
    scan_results = {}
    for function in scan_functions:

        try:
            scan_results.update(function(location))
        except Exception as e:
            trace = traceback.format_exc()
            msg = f'ERROR: while scanning: "{location}"\n{trace}'
            scan_errors.append(msg)

    if scan_errors:
        scan_results["scan_errors"] = scan_errors
    return scan_results


def scan_for_files(project):
    """
    Run a license, copyright, email, and url scan on remainder of files
    without status.
    """
    queryset = CodebaseResource.objects.project(project).no_status()

    for codebase_resource in queryset:
        scan_results = scan_file(codebase_resource.location)
        scan_errors = scan_results.get("scan_errors")
        if scan_errors:
            for err in scan_errors:
                # by convention the first line is the error message and the
                # remainder is the traceback
                message, _, trace = err.partition("\n")
                ProjectError.objects.create(
                    project=codebase_resource.project,
                    model=CodebaseResource.__name__,
                    details=model_to_dict(codebase_resource),
                    message=message,
                    traceback=trace,
                )
                codebase_resource.status = "scanned-with-error"
        else:
            codebase_resource.status = "scanned"

        codebase_resource.set_scan_results(scan_results, save=True)


def has_unknown_license(codebase_resource):
    """
    Return True if an "unknown" license in present in the license expression.
    """
    return any(
        "unknown" in expression for expression in codebase_resource.license_expressions
    )


def has_no_licenses(codebase_resource):
    """
    Return True if the `codebase_resource` has no license expression.
    """
    return not codebase_resource.license_expressions


def analyze_scanned_files(project):
    """
    Set the status for CodebaseResource with unknown or no licenses.
    """
    queryset = CodebaseResource.objects.project(project).status("scanned")

    for codebase_resource in queryset:
        if has_unknown_license(codebase_resource):
            codebase_resource.status = "unknown-license"
            codebase_resource.save()
        elif has_no_licenses(codebase_resource):
            codebase_resource.status = "no-licenses"
            codebase_resource.save()


def tag_not_analyzed_codebase_resources(project):
    """
    Flag as "not-analyzed" the `CodebaseResource` without a status of the
    provided `project`
    """
    no_status = CodebaseResource.objects.project(project).no_status()
    no_status.update(status="not-analyzed")


def normalize_path(path):
    """
    Return a normalized path from a `path` string.
    """
    return "/" + path.strip("/")


def strip_root(location):
    """
    Return the provided `location` without the root directory.
    """
    return "/".join(str(location).strip("/").split("/")[1:])


def filename_now(sep="-"):
    """
    Return the current date and time as iso format suitable for filename.
    """
    now = datetime.now().isoformat(sep=sep, timespec="seconds")
    return now.replace(":", sep)


def count_group_by(queryset, field_name):
    """
    Return a summary of all existing values for the provided `field_name` on the
    `queryset`, including the count of each entry, as a dict.
    """
    counts = (
        queryset.values(field_name)
        .annotate(count=Count(field_name))
        .order_by(field_name)
    )

    return {entry.get(field_name): entry.get("count") for entry in counts}

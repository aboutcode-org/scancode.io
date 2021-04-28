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

import concurrent.futures
import logging
import os
import shlex
from functools import partial
from pathlib import Path

from django.apps import apps
from django.conf import settings

import packagedcode
from commoncode import fileutils
from commoncode.resource import VirtualCodebase
from extractcode.extract import extract_file
from packageurl import PackageURL
from scancode import ScancodeError
from scancode import Scanner
from scancode import api as scancode_api
from scancode import cli as scancode_cli

from scanpipe import pipes
from scanpipe.models import CodebaseResource

logger = logging.getLogger("scanpipe.pipes")

"""
Utilities to deal with ScanCode objects, in particular Codebase and Package.
"""

scanpipe_app = apps.get_app_config("scanpipe")

# The maximum number of processes that can be used to execute multiprocessing calls.
# If None or not give,n then as many worker processes, minus one, will be created as the
# machine has CPUs.
SCANCODEIO_PROCESSES = getattr(settings, "SCANCODEIO_PROCESSES", None)


def extract(location, target):
    """
    Wraps the `extractcode.extract_file` to execute the extraction and return errors.
    """
    errors = []

    for event in extract_file(location, target):
        if event.done:
            errors.extend(event.errors)

    return errors


def get_resource_info(location):
    """
    Return a mapping suitable for the creation of a new CodebaseResource.
    """
    file_info = {}

    location_path = Path(location)
    is_symlink = location_path.is_symlink()
    is_file = location_path.is_file()

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


def _scan_resource(location, scanners):
    """
    Wrap the scancode-toolkit `scan_resource` method to support timeout on direct
    scanner functions calls.

    Return a dict of scan `results` and a list of `errors`.
    """
    # `rid` is not needed in this context, yet required in the scan_resource args
    location_rid = location, 0
    _, _, errors, _, results, _ = scancode_cli.scan_resource(location_rid, scanners)
    return results, errors


def scan_file(location):
    """
    Run a license, copyright, email, and url scan on provided `location`,
    using the scancode-toolkit direct API.

    Return a dict of scan `results` and a list of `errors`.
    """
    scanners = [
        Scanner("copyrights", scancode_api.get_copyrights),
        Scanner("licenses", partial(scancode_api.get_licenses, include_text=True)),
        Scanner("emails", scancode_api.get_emails),
        Scanner("urls", scancode_api.get_urls),
    ]
    return _scan_resource(location, scanners)


def scan_for_package_info(location):
    """
    Run a package scan on provided `location` using the scancode-toolkit direct API.

    Return a dict of scan `results` and a list of `errors`.
    """
    scanners = [
        Scanner("packages", scancode_api.get_package_info),
    ]
    return _scan_resource(location, scanners)


def save_scan_file_results(codebase_resource, scan_results, scan_errors):
    """
    Save the resource scan file results in the database.
    Create project errors if any occurred during the scan.
    """
    if scan_errors:
        codebase_resource.add_errors(scan_errors)
        codebase_resource.status = "scanned-with-error"
    else:
        codebase_resource.status = "scanned"

    codebase_resource.set_scan_results(scan_results, save=True)


def save_scan_package_results(codebase_resource, scan_results, scan_errors):
    """
    Save the resource scan package results in the database.
    Create project errors if any occurred during the scan.
    """
    packages = scan_results.get("packages", [])
    if packages:
        for package_data in packages:
            codebase_resource.create_and_add_package(package_data)
        codebase_resource.status = "application-package"
        codebase_resource.save()

    if scan_errors:
        codebase_resource.add_errors(scan_errors)
        codebase_resource.status = "scanned-with-error"
        codebase_resource.save()


def _scan_and_save(project, scan_func, save_func):
    """
    Run the `scan_func` on files without status for `project`.
    The `save_func` is called to save the results.

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the SCANCODEIO_PROCESSES setting.

    The codebase resources QuerySet is chunked in 2000 results at the time,
    this can result in a significant reduction in memory usage.

    Note that all database related actions are executed in this main process as the
    database connection does not always fork nicely in the pool processes.
    """
    codebase_resources = project.codebaseresources.no_status()
    resource_count = codebase_resources.count()
    logger.info(f"Scan {resource_count} codebase resources with {scan_func.__name__}")
    resource_iterator = codebase_resources.iterator(chunk_size=2000)
    max_workers = SCANCODEIO_PROCESSES or os.cpu_count() - 1 or 1

    with concurrent.futures.ProcessPoolExecutor(max_workers) as executor:
        future_to_resource = {
            executor.submit(scan_func, resource.location): resource
            for resource in resource_iterator
        }

        # Iterate over the Futures as they complete (finished or cancelled)
        future_as_completed = concurrent.futures.as_completed(future_to_resource)

        for index, future in enumerate(future_as_completed):
            resource = future_to_resource[future]

            progress = f"{index / resource_count * 100:.1f}% ({index}/{resource_count})"
            logger.info(f"{scan_func.__name__} {progress} pk={resource.pk}")

            scan_results, scan_errors = future.result()
            save_func(resource, scan_results, scan_errors)


def scan_for_files(project):
    """
    Run a license, copyright, email, and url scan on files without status for `project`.

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the SCANCODEIO_PROCESSES setting.
    """
    _scan_and_save(project, scan_file, save_scan_file_results)


def scan_for_application_packages(project):
    """
    Run a package scan on files without status for `project`.

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the SCANCODEIO_PROCESSES setting.
    """
    _scan_and_save(project, scan_for_package_info, save_scan_package_results)


def run_extractcode(location, options=None, raise_on_error=False):
    """
    Extract content at `location` with extractcode.
    Optional arguments for the `extractcode` executable can be provided with the
    `options` list.
    If `raise_on_error` is enabled, a ScancodeError will be raised if the
    exitcode greater than 0.
    """
    extractcode_args = [
        pipes.get_bin_executable("extractcode"),
        shlex.quote(location),
    ]

    if options:
        extractcode_args.extend(options)

    exitcode, output = pipes.run_command(extractcode_args)
    if exitcode > 0 and raise_on_error:
        raise ScancodeError(output)

    return exitcode, output


def run_scancode(location, output_file, options, raise_on_error=False):
    """
    Scan `location` content and write results into `output_file`.
    The `scancode` executable will be run using the provided `options`.
    If `raise_on_error` is enabled, a ScancodeError will be raised if the
    exitcode greater than 0.
    """
    default_options = getattr(settings, "SCANCODE_DEFAULT_OPTIONS", [])

    scancode_args = [
        pipes.get_bin_executable("scancode"),
        shlex.quote(location),
        *default_options,
        *options,
        f"--json-pp {shlex.quote(output_file)}",
    ]

    exitcode, output = pipes.run_command(scancode_args)
    if exitcode > 0 and raise_on_error:
        raise ScancodeError(output)

    return exitcode, output


def get_virtual_codebase(project, input_location):
    """
    Return a ScanCode virtual codebase built from the JSON scan file at
    `input_location`.
    """
    temp_path = project.tmp_path / "scancode-temp-resource-cache"
    temp_path.mkdir(parents=True, exist_ok=True)

    return VirtualCodebase(
        location=input_location, temp_dir=str(temp_path), max_in_memory=0
    )


def create_codebase_resources(project, scanned_codebase):
    """
    Save the resources of a ScanCode `scanned_codebase` scancode.resource.Codebase
    object to the DB as CodebaseResource of the `project`.
    This function can be used to expends an existing `project` Codebase with new
    CodebaseResource objects as the existing objects (based on the `path`) will be
    skipped.
    """
    for scanned_resource in scanned_codebase.walk():
        resource_data = {}

        for field in CodebaseResource._meta.fields:
            value = getattr(scanned_resource, field.name, None)
            if value is not None:
                resource_data[field.name] = value

        resource_type = "FILE" if scanned_resource.is_file else "DIRECTORY"
        resource_data["type"] = CodebaseResource.Type[resource_type]

        path = resource_data.pop("path")
        CodebaseResource.objects.get_or_create(
            project=project,
            path=path,
            defaults=resource_data,
        )


def create_discovered_packages(project, scanned_codebase):
    """
    Save the packages of a ScanCode `scanned_codebase` scancode.resource.Codebase
    object to the DB as DiscoveredPackage of `project`.
    Relate package resources to CodebaseResource.
    """
    for scanned_resource in scanned_codebase.walk():
        scanned_packages = getattr(scanned_resource, "packages", [])
        if not scanned_packages:
            continue

        cbr = CodebaseResource.objects.get(project=project, path=scanned_resource.path)

        for scan_data in scanned_packages:
            discovered_package = pipes.update_or_create_package(project, scan_data)
            set_codebase_resource_for_package(
                codebase_resource=cbr, discovered_package=discovered_package
            )

            scanned_package = packagedcode.get_package_instance(scan_data)
            # Set all the resource attached to that package
            scanned_package_resources = scanned_package.get_package_resources(
                scanned_resource, scanned_codebase
            )
            for scanned_package_res in scanned_package_resources:
                package_cbr = CodebaseResource.objects.get(
                    project=project, path=scanned_package_res.path
                )
                set_codebase_resource_for_package(
                    codebase_resource=package_cbr, discovered_package=discovered_package
                )

            # also set dependencies as their own packages
            # TODO: we should instead relate these to the package
            # TODO: we likely need a status for DiscoveredPackage
            dependencies = scanned_package.dependencies or []
            for dependency in dependencies:
                # FIXME: we should get DependentPackage instances and not a mapping
                purl = getattr(dependency, "purl", None)
                if not purl:
                    # TODO: we should log that
                    continue
                purl = PackageURL.from_string(purl)
                dep = purl.to_dict()
                dependent_package = pipes.update_or_create_package(project, dep)

                # attached to the current resource (typically a manifest?)
                set_codebase_resource_for_package(
                    codebase_resource=cbr, discovered_package=dependent_package
                )


def set_codebase_resource_for_package(codebase_resource, discovered_package):
    """
    Assign the `discovered_package` to the `codebase_resource` and set its
    status to "application-package".
    """
    codebase_resource.discovered_packages.add(discovered_package)
    codebase_resource.status = "application-package"
    codebase_resource.save()

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
import hashlib
import json
import logging
import os
import shlex
from collections import defaultdict
from functools import partial
from pathlib import Path

from django.apps import apps
from django.conf import settings

from commoncode import fileutils
from commoncode.resource import VirtualCodebase
from extractcode import api as extractcode_api
from packagedcode import get_package_handler
from packagedcode import models as packagedcode_models
from scancode import ScancodeError
from scancode import Scanner
from scancode import api as scancode_api
from scancode import cli as scancode_cli

from scanpipe import pipes
from scanpipe.models import CodebaseResource

logger = logging.getLogger("scanpipe.pipes")

"""
Utilities to deal with ScanCode toolkit features and objects.
"""

scanpipe_app = apps.get_app_config("scanpipe")


def get_max_workers(keep_available):
    """
    Returns the `SCANCODEIO_PROCESSES` if defined in the setting,
    or returns a default value based on the number of available CPUs,
    minus the provided `keep_available` value.
    """
    processes = getattr(settings, "SCANCODEIO_PROCESSES", None)
    if processes is not None:
        return processes

    max_workers = os.cpu_count() - keep_available
    if max_workers < 1:
        return 1
    return max_workers


def extract_archive(location, target):
    """
    Extracts a single archive or compressed file at `location` to the `target`
    directory.

    Returns a list of extraction errors.

    Wrapper of the `extractcode.api.extract_archive` function.
    """
    errors = []

    for event in extractcode_api.extract_archive(location, target):
        if event.done:
            errors.extend(event.errors)

    return errors


def extract_archives(location, recurse=False):
    """
    Extracts all archives at `location` and return errors.

    Archives and compressed files are extracted in a new directory named
    "<file_name>-extract" created in the same directory as each extracted
    archive.

    If `recurse` is True, extract nested archives-in-archives recursively.

    Returns a list of extraction errors.

    Wrapper of the `extractcode.api.extract_archives` function.
    """
    options = {
        "recurse": recurse,
        "replace_originals": False,
        "all_formats": True,
    }

    errors = []
    for event in extractcode_api.extract_archives(location, **options):
        if event.done:
            errors.extend(event.errors)

    return errors


def get_resource_info(location):
    """
    Returns a mapping suitable for the creation of a new CodebaseResource.
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
            "name": fileutils.file_name(location),
            "extension": fileutils.file_extension(location),
        }
    )

    if is_symlink:
        return file_info

    # Missing fields on CodebaseResource model returned by `get_file_info`.
    unsupported_fields = [
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


def _scan_resource(location, scanners, with_threading=True):
    """
    Wraps the scancode-toolkit `scan_resource` method to support timeout on direct
    scanner functions calls.
    Returns a dictionary of scan `results` and a list of `errors`.
    The `with_threading` needs to be enabled for the timeouts support.
    """
    # `rid` is not needed in this context, yet required in the scan_resource args
    location_rid = location, 0
    _, _, errors, _, results, _ = scancode_cli.scan_resource(
        location_rid,
        scanners,
        with_threading=with_threading,
    )
    return results, errors


def scan_file(location, with_threading=True):
    """
    Runs a license, copyright, email, and url scan on a provided `location`,
    using the scancode-toolkit direct API.

    Returns a dictionary of scan `results` and a list of `errors`.
    """
    scanners = [
        Scanner("copyrights", scancode_api.get_copyrights),
        Scanner("licenses", partial(scancode_api.get_licenses, include_text=True)),
        Scanner("emails", scancode_api.get_emails),
        Scanner("urls", scancode_api.get_urls),
    ]
    return _scan_resource(location, scanners, with_threading)


def scan_for_package_data(location, with_threading=True):
    """
    Runs a package scan on provided `location` using the scancode-toolkit direct API.

    Returns a dict of scan `results` and a list of `errors`.
    """
    scanners = [
        Scanner("package_data", scancode_api.get_package_data),
    ]
    return _scan_resource(location, scanners, with_threading)


def save_scan_file_results(codebase_resource, scan_results, scan_errors):
    """
    Saves the resource scan file results in the database.
    Creates project errors if any occurred during the scan.
    """
    if scan_errors:
        codebase_resource.add_errors(scan_errors)
        codebase_resource.status = "scanned-with-error"
    else:
        codebase_resource.status = "scanned"

    codebase_resource.set_scan_results(scan_results, save=True)


def save_scan_package_results(codebase_resource, scan_results, scan_errors):
    """
    Saves the resource scan package results in the database.
    Creates project errors if any occurred during the scan.
    """
    package_data = scan_results.get("package_data", [])
    if package_data:
        codebase_resource.package_data = package_data
        codebase_resource.status = "application-package"
        codebase_resource.save()

    if scan_errors:
        codebase_resource.add_errors(scan_errors)
        codebase_resource.status = "scanned-with-error"
        codebase_resource.save()


def _log_progress(scan_func, resource, resource_count, index):
    progress = f"{index / resource_count * 100:.1f}% ({index}/{resource_count})"
    logger.info(f"{scan_func.__name__} {progress} completed pk={resource.pk}")


def _scan_and_save(resource_qs, scan_func, save_func):
    """
    Runs the `scan_func` on the codebase resources if the provided `resource_qs`.
    The `save_func` is called to save the results.

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the `SCANCODEIO_PROCESSES` setting.
    Multiprocessing can be disable using `SCANCODEIO_PROCESSES=0`,
    and threading can also be disabled `SCANCODEIO_PROCESSES=-1`

    The codebase resources QuerySet is chunked in 2000 results at the time,
    this can result in a significant reduction in memory usage.

    Note that all database related actions are executed in this main process as the
    database connection does not always fork nicely in the pool processes.
    """
    resource_count = resource_qs.count()
    logger.info(f"Scan {resource_count} codebase resources with {scan_func.__name__}")
    resource_iterator = resource_qs.iterator(chunk_size=2000)

    max_workers = get_max_workers(keep_available=1)

    if max_workers <= 0:
        with_threading = False if max_workers == -1 else True
        for index, resource in enumerate(resource_iterator):
            _log_progress(scan_func, resource, resource_count, index)
            scan_results, scan_errors = scan_func(resource.location, with_threading)
            save_func(resource, scan_results, scan_errors)
        return

    logger.info(f"Starting ProcessPoolExecutor with {max_workers} max_workers")

    with concurrent.futures.ProcessPoolExecutor(max_workers) as executor:
        future_to_resource = {
            executor.submit(scan_func, resource.location): resource
            for resource in resource_iterator
        }

        # Iterate over the Futures as they complete (finished or cancelled)
        future_as_completed = concurrent.futures.as_completed(future_to_resource)

        for index, future in enumerate(future_as_completed, start=1):
            resource = future_to_resource[future]
            _log_progress(scan_func, resource, resource_count, index)
            scan_results, scan_errors = future.result()
            save_func(resource, scan_results, scan_errors)


def scan_for_files(project):
    """
    Runs a license, copyright, email, and url scan on files without a status for
    a `project`.

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the SCANCODEIO_PROCESSES setting.
    """
    resource_qs = project.codebaseresources.no_status()
    _scan_and_save(resource_qs, scan_file, save_scan_file_results)


def scan_for_application_packages(project):
    """
    Runs a package scan on files without a status for a `project`,
    then create DiscoveredPackage and DiscoveredDependency instances
    from the detected package data

    Multiprocessing is enabled by default on this pipe, the number of processes can be
    controlled through the SCANCODEIO_PROCESSES setting.
    """
    resource_qs = project.codebaseresources.no_status()

    # Collect detected Package data and save it to the CodebaseResource it was
    # detected from
    _scan_and_save(
        resource_qs=resource_qs,
        scan_func=scan_for_package_data,
        save_func=save_scan_package_results,
    )

    # Iterate through CodebaseResources with Package data and handle them using
    # the proper Package handler from packagedcode
    assemble_packages(project=project)


def add_to_package(package_uid, resource, project):
    """
    Relate a DiscoveredPackage to `resource` from `project` using `package_uid`
    """
    if not package_uid:
        return
    package_associated_with_resource = resource.discovered_packages.filter(
        package_uid=package_uid
    ).exists()
    if not package_associated_with_resource:
        package = project.discoveredpackages.get(package_uid=package_uid)
        resource.discovered_packages.add(package)


def assemble_packages(project):
    """
    Create instances of DiscoveredPackage and DiscoveredDependency for `project`
    from the parsed package data present in the CodebaseResources of `project`.
    """
    logger.info(f"Project: {project}:\n" "Function: assemble_packages\n")
    seen_resource_paths = set()
    for resource in project.codebaseresources.has_package_data():
        if resource.path in seen_resource_paths:
            continue

        logger.info(f"Processing: CodebaseResource {resource.path}\n")

        for package_mapping in resource.package_data:
            pd = packagedcode_models.PackageData.from_dict(mapping=package_mapping)

            logger.info(f"Processing: PackageData {pd.purl}\n")

            handler = get_package_handler(pd)

            logger.info(f"Selected: Package handler {handler}\n")

            items = handler.assemble(
                package_data=pd,
                resource=resource,
                codebase=project,
                package_adder=add_to_package,
            )

            for item in items:
                logger.info(f"Processing: item {item}\n")
                if isinstance(item, packagedcode_models.Package):
                    package_data = item.to_dict()
                    pipes.update_or_create_package(project, package_data)
                elif isinstance(item, packagedcode_models.Dependency):
                    dependency_data = item.to_dict()
                    pipes.update_or_create_dependencies(project, dependency_data)
                elif isinstance(item, CodebaseResource):
                    seen_resource_paths.add(item.path)
                else:
                    logger.info(f"Unknown Package assembly item type: {item!r}\n")


def run_scancode(location, output_file, options, raise_on_error=False):
    """
    Scans the `location` content and write the results into an `output_file`.
    The `scancode` executable will run using the provided `options`.
    If `raise_on_error` is enabled, a ScancodeError will be raised if the
    exitcode is greater than 0.
    """
    options_from_settings = getattr(settings, "SCANCODE_TOOLKIT_CLI_OPTIONS", [])
    max_workers = get_max_workers(keep_available=1)

    scancode_args = [
        pipes.get_bin_executable("scancode"),
        shlex.quote(location),
        *options_from_settings,
        *options,
        f"--processes {max_workers}",
        "--verbose",
        f"--json-pp {shlex.quote(output_file)}",
    ]

    exitcode, output = pipes.run_command(scancode_args, log_output=True)
    if exitcode > 0 and raise_on_error:
        raise ScancodeError(output)

    return exitcode, output


def get_virtual_codebase(project, input_location):
    """
    Returns a ScanCode virtual codebase built from the JSON scan file located at
    the `input_location`.
    """
    temp_path = project.tmp_path / "scancode-temp-resource-cache"
    temp_path.mkdir(parents=True, exist_ok=True)

    return VirtualCodebase(input_location, temp_dir=str(temp_path), max_in_memory=0)


def create_codebase_resources(project, scanned_codebase):
    """
    Saves the resources of a ScanCode `scanned_codebase` scancode.resource.Codebase
    object to the database as a CodebaseResource of the `project`.
    This function can be used to expend an existing `project` Codebase with new
    CodebaseResource objects as the existing objects (based on the `path`) will be
    skipped.
    """
    for scanned_resource in scanned_codebase.walk(skip_root=True):
        resource_data = {}

        for field in CodebaseResource._meta.fields:
            # Do not include the path as provided by the scanned_resource since it
            # includes the "root". The `get_path` method is used instead.
            if field.name == "path":
                continue
            value = getattr(scanned_resource, field.name, None)
            if value is not None:
                resource_data[field.name] = value

        resource_type = "FILE" if scanned_resource.is_file else "DIRECTORY"
        resource_data["type"] = CodebaseResource.Type[resource_type]
        resource_path = scanned_resource.get_path(strip_root=True)

        codebase_resource, _ = CodebaseResource.objects.get_or_create(
            project=project,
            path=resource_path,
            defaults=resource_data,
        )

        for_packages = getattr(scanned_resource, "for_packages", [])
        for package_uid in for_packages:
            logger.debug(f"Assign {package_uid} to {codebase_resource}")
            package = project.discoveredpackages.get(package_uid=package_uid)
            set_codebase_resource_for_package(
                codebase_resource=codebase_resource,
                discovered_package=package,
            )


def create_discovered_packages(project, scanned_codebase):
    """
    Saves the packages of a ScanCode `scanned_codebase` scancode.resource.Codebase
    object to the database as a DiscoveredPackage of `project`.
    """
    if hasattr(scanned_codebase.attributes, "packages"):
        for package_data in scanned_codebase.attributes.packages:
            pipes.update_or_create_package(project, package_data)


def create_discovered_dependencies(project, scanned_codebase):
    """
    Saves the dependencies of a ScanCode `scanned_codebase` scancode.resource.Codebase
    object to the database as a DiscoveredDependency of `project`.
    """
    if hasattr(scanned_codebase.attributes, "dependencies"):
        for dependency_data in scanned_codebase.attributes.dependencies:
            pipes.update_or_create_dependencies(project, dependency_data)


def set_codebase_resource_for_package(codebase_resource, discovered_package):
    """
    Assigns the `discovered_package` to the `codebase_resource` and set its
    status to "application-package".
    """
    codebase_resource.discovered_packages.add(discovered_package)
    codebase_resource.status = "application-package"
    codebase_resource.save()


def _get_license_matches_grouped(project):
    """
    Returns a dictionary of all license_matches of a given `project` grouped by
    license_expression.
    """
    license_matches = defaultdict(list)

    for resource in project.codebaseresources.has_licenses():
        file_cache = []

        for license in resource.licenses:
            matched_rule = license.get("matched_rule", {})
            license_expression = matched_rule.get("license_expression")
            matched_text = license.get("matched_text")

            # Do not include duplicated matched_text for a given license_expression
            # within the same file
            cache_key = ":".join([license_expression, resource.path, matched_text])
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            if cache_key in file_cache:
                continue
            file_cache.append(cache_key)

            license_matches[license_expression].append(
                {
                    "path": resource.path,
                    "matched_text": matched_text,
                }
            )

    return dict(license_matches)


def make_results_summary(project, scan_results_location):
    """
    Extracts selected sections of the Scan results, such as the `summary`
    `license_clarity_score`, and `license_matches` related data.
    The `key_files` are also collected and injected in the `summary` output.
    """
    from scanpipe.api.serializers import CodebaseResourceSerializer
    from scanpipe.api.serializers import DiscoveredPackageSerializer

    with open(scan_results_location) as f:
        scan_data = json.load(f)

    summary = scan_data.get("summary")

    # Inject the generated `license_matches` in the summary
    summary["license_matches"] = _get_license_matches_grouped(project)

    # Inject the `key_files` and their file content in the summary
    key_files = []
    key_files_qs = project.codebaseresources.filter(is_key_file=True, is_text=True)

    for resource in key_files_qs:
        resource_data = CodebaseResourceSerializer(resource).data
        resource_data["content"] = resource.file_content
        key_files.append(resource_data)

    summary["key_files"] = key_files

    # Inject the `key_files_packages` filtered from the key_files_qs
    key_files_packages_qs = project.discoveredpackages.filter(
        codebase_resources__in=key_files_qs
    ).distinct()

    summary["key_files_packages"] = [
        DiscoveredPackageSerializer(package).data for package in key_files_packages_qs
    ]

    return summary


def create_inventory_from_scan(project, input_location):
    """
    Create CodebaseResource and DiscoveredPackage instances loaded from the scan
    results located at `input_location`.
    """
    scanned_codebase = get_virtual_codebase(project, input_location)
    create_discovered_packages(project, scanned_codebase)
    create_discovered_dependencies(project, scanned_codebase)
    create_codebase_resources(project, scanned_codebase)

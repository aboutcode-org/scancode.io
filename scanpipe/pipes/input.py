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

import os
import shutil
from pathlib import Path

from django.core.exceptions import FieldDoesNotExist
from django.core.validators import EMPTY_VALUES
from django.db import models

import openpyxl
from typecode.contenttype import get_type

from scanpipe import pipes
from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredLicense
from scanpipe.models import DiscoveredPackage
from scanpipe.pipes import scancode
from scanpipe.pipes.output import mappings_key_by_fieldname


def copy_input(input_location, dest_path):
    """Copy the ``input_location`` (file or directory) to the ``dest_path``."""
    input_path = Path(input_location)
    destination_dir = Path(dest_path)
    destination = destination_dir / input_path.name

    if input_path.is_dir():
        shutil.copytree(input_location, destination)
    else:
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        shutil.copyfile(input_location, destination)

    return destination


def copy_inputs(input_locations, dest_path):
    """Copy the provided ``input_locations`` to the ``dest_path``."""
    for input_location in input_locations:
        copy_input(input_location, dest_path)


def move_input(input_location, dest_path):
    """Move the provided ``input_location`` to the ``dest_path``."""
    destination = dest_path / Path(input_location).name
    return shutil.move(input_location, destination)


def move_inputs(inputs, dest_path):
    """Move the provided ``inputs`` to the ``dest_path``."""
    for input_location in inputs:
        move_input(input_location, dest_path)


def get_tool_name_from_scan_headers(scan_data):
    """Return the ``tool_name`` of the first header in the provided ``scan_data``."""
    if headers := scan_data.get("headers", []):
        first_header = headers[0]
        tool_name = first_header.get("tool_name", "")
        return tool_name


def get_extra_data_from_scan_headers(scan_data):
    """Return the ``extra_data`` of the first header in the provided ``scan_data``."""
    if headers := scan_data.get("headers", []):
        first_header = headers[0]
        if extra_data := first_header.get("extra_data"):
            return extra_data


def is_archive(location):
    """Return True if the file at ``location`` is an archive."""
    return get_type(location).is_archive


def load_inventory_from_toolkit_scan(project, input_location):
    """
    Create license detections, packages, dependencies, and resources
    loaded from the ScanCode-toolkit scan results located at ``input_location``.
    """
    scanned_codebase = scancode.get_virtual_codebase(project, input_location)
    scancode.create_discovered_licenses(project, scanned_codebase)
    scancode.create_discovered_packages(project, scanned_codebase)
    scancode.create_codebase_resources(project, scanned_codebase)
    scancode.create_discovered_dependencies(
        project, scanned_codebase, strip_datafile_path_root=True
    )
    scancode.load_todo_issues(project, scanned_codebase)


def load_inventory_from_scanpipe(project, scan_data, extra_data_prefix=None):
    """
    Create packages, dependencies, license detections, resources, and relations
    loaded from a ScanCode.io JSON output provided as ``scan_data``.

    An ``extra_data_prefix`` can be provided in case multiple input files are loaded
    into the same project. The prefix is usually the filename of the input.
    """
    for detection_data in scan_data.get("license_detections", []):
        pipes.update_or_create_license_detection(project, detection_data)

    for package_data in scan_data.get("packages", []):
        pipes.update_or_create_package(project, package_data)

    for resource_data in scan_data.get("files", []):
        pipes.update_or_create_resource(project, resource_data)

    for dependency_data in scan_data.get("dependencies", []):
        pipes.update_or_create_dependency(project, dependency_data)

    for relation_data in scan_data.get("relations", []):
        pipes.get_or_create_relation(project, relation_data)

    if extra_data := get_extra_data_from_scan_headers(scan_data):
        if extra_data_prefix:
            extra_data = {extra_data_prefix: extra_data}
        project.update_extra_data(extra_data)


model_to_object_maker_func = {
    DiscoveredPackage: pipes.update_or_create_package,
    DiscoveredDependency: pipes.update_or_create_dependency,
    DiscoveredLicense: pipes.update_or_create_license_detection,
    CodebaseResource: pipes.update_or_create_resource,
    CodebaseRelation: pipes.get_or_create_relation,
}

worksheet_name_to_model = {
    "PACKAGES": DiscoveredPackage,
    "LICENSE_DETECTIONS": DiscoveredLicense,
    "RESOURCES": CodebaseResource,
    "DEPENDENCIES": DiscoveredDependency,
    "RELATIONS": CodebaseRelation,
}


def get_worksheet_data(worksheet):
    """Return the data from provided ``worksheet`` as a list of dict."""
    try:
        header = [cell.value for cell in next(worksheet.rows)]
    except StopIteration:
        return {}

    worksheet_data = [
        dict(zip(header, row))
        for row in worksheet.iter_rows(min_row=2, values_only=True)
    ]
    return worksheet_data


def clean_xlsx_field_value(model_class, field_name, value):
    """Clean the ``value`` for compatibility with the database ``model_class``."""
    if value in EMPTY_VALUES:
        return

    if field_name == "for_packages":
        return value.splitlines()

    elif field_name in ["purl", "for_package_uid", "datafile_path"]:
        return value

    try:
        field = model_class._meta.get_field(field_name)
    except FieldDoesNotExist:
        return

    if dict_key := mappings_key_by_fieldname.get(field_name):
        return [{dict_key: entry} for entry in value.splitlines()]

    elif isinstance(field, models.JSONField):
        if field.default is list:
            return value.splitlines()
        elif field.default is dict:
            return  # dict stored as JSON are not supported

    return value


def clean_xlsx_data_to_model_data(model_class, xlsx_data):
    """Clean the ``xlsx_data`` for compatibility with the database ``model_class``."""
    cleaned_data = {}

    for field_name, value in xlsx_data.items():
        if cleaned_value := clean_xlsx_field_value(model_class, field_name, value):
            cleaned_data[field_name] = cleaned_value

    return cleaned_data


def load_inventory_from_xlsx(project, input_location, extra_data_prefix=None):
    """
    Create packages, dependencies, resources, and relations loaded from XLSX file
    located at ``input_location``.

    An ``extra_data_prefix`` can be provided in case multiple input files are loaded
    into the same project. The prefix is usually the filename of the input.
    """
    workbook = openpyxl.load_workbook(input_location, read_only=True, data_only=True)

    for worksheet_name, model_class in worksheet_name_to_model.items():
        if worksheet_name not in workbook:
            continue

        worksheet_data = get_worksheet_data(worksheet=workbook[worksheet_name])
        for row_data in worksheet_data:
            object_maker_func = model_to_object_maker_func.get(model_class)
            cleaned_data = clean_xlsx_data_to_model_data(model_class, row_data)
            if cleaned_data:
                object_maker_func(project, cleaned_data)

    if "LAYERS" in workbook:
        layers_data = get_worksheet_data(worksheet=workbook["LAYERS"])
        extra_data = {"layers": layers_data}
        if extra_data_prefix:
            extra_data = {extra_data_prefix: extra_data}
        project.update_extra_data(extra_data)


def get_integrated_tool_name(scan_data):
    """
    Detect and return the integrated tool name from the ``scan_data`` structure.

    Supported tools:
    - vulnerablecode: VulnerableCode vulnerability data export
    - purldb: PurlDB package enrichment data export
    - matchcodeio: MatchCode.io matching results export

    Returns None if the tool cannot be identified.
    """
    if "vulnerabilities" in scan_data or (
        isinstance(scan_data, list)
        and scan_data
        and "affected_by_vulnerabilities" in scan_data[0]
    ):
        return "vulnerablecode"

    if "files" in scan_data and "packages" in scan_data:
        files = scan_data.get("files", [])
        if files and any("for_packages" in f for f in files if isinstance(f, dict)):
            for file_data in files:
                if isinstance(file_data, dict):
                    extra_data = file_data.get("extra_data", {})
                    if any(
                        key in extra_data
                        for key in ["matched_to", "path_score", "matched_fingerprints"]
                    ):
                        return "matchcodeio"

    if "packages" in scan_data or (
        isinstance(scan_data, list)
        and scan_data
        and isinstance(scan_data[0], dict)
        and "purl" in scan_data[0]
        and any(
            key in scan_data[0]
            for key in ["repository_homepage_url", "api_data_url", "package_content"]
        )
    ):
        return "purldb"

    return None


def load_vulnerabilities_from_vulnerablecode(project, scan_data):
    """
    Load vulnerability data from VulnerableCode export and update project packages.

    The ``scan_data`` should contain vulnerability information that can be matched
    to existing packages in the project by their PURL.

    Expected format:
    - List of package dicts with 'purl' and 'affected_by_vulnerabilities' keys
    - Or dict with 'vulnerabilities' key containing vulnerability details
    """
    packages_by_purl = {}
    for package in project.discoveredpackages.all():
        if package.package_url:
            packages_by_purl[package.package_url] = package

    if isinstance(scan_data, list):
        vulnerability_data_list = scan_data
    elif "packages" in scan_data:
        vulnerability_data_list = scan_data.get("packages", [])
    elif "results" in scan_data:
        vulnerability_data_list = scan_data.get("results", [])
    else:
        vulnerability_data_list = []

    updated_packages = []
    for vuln_data in vulnerability_data_list:
        purl = vuln_data.get("purl")
        if not purl:
            continue

        package = packages_by_purl.get(purl)
        if not package:
            continue

        affected_by = vuln_data.get("affected_by_vulnerabilities", [])
        if affected_by:
            package.affected_by_vulnerabilities = affected_by
            updated_packages.append(package)

    if updated_packages:
        DiscoveredPackage.objects.bulk_update(
            objs=updated_packages,
            fields=["affected_by_vulnerabilities"],
            batch_size=1000,
        )

    return len(updated_packages)


def load_enrichment_from_purldb(project, scan_data):
    """
    Load package enrichment data from PurlDB export and update/create packages.

    The ``scan_data`` should contain package information that can be used to
    enrich existing packages or create new packages in the project.

    Expected format:
    - List of package dicts with package data fields
    - Or dict with 'packages' key containing package dicts
    """
    if isinstance(scan_data, list):
        package_data_list = scan_data
    elif "packages" in scan_data:
        package_data_list = scan_data.get("packages", [])
    elif "results" in scan_data:
        package_data_list = scan_data.get("results", [])
    else:
        package_data_list = []

    created_count = 0
    updated_count = 0

    for package_data in package_data_list:
        purl = package_data.get("purl")
        if not purl:
            continue

        existing_package = project.discoveredpackages.filter(
            package_url=purl
        ).first()

        if existing_package:
            updated_fields = existing_package.update_from_data(package_data)
            if updated_fields:
                existing_package.update_extra_data(
                    {"enriched_from_purldb": updated_fields}
                )
                updated_count += 1
        else:
            pipes.update_or_create_package(project, package_data)
            created_count += 1

    return {"created": created_count, "updated": updated_count}


def load_matches_from_matchcode(project, scan_data):
    """
    Load matching results from MatchCode.io export and create packages/associations.

    The ``scan_data`` should contain matching results with package data and
    resource associations.

    Expected format:
    - Dict with 'files' and 'packages' keys
    - 'files' contains resource data with 'for_packages' associations
    - 'packages' contains matched package data
    """
    from collections import defaultdict

    files_data = scan_data.get("files", [])
    packages_data = scan_data.get("packages", [])

    resource_paths_by_package_uid = defaultdict(list)
    for file_data in files_data:
        for_packages = file_data.get("for_packages", [])
        file_path = file_data.get("path")
        if file_path:
            for package_uid in for_packages:
                resource_paths_by_package_uid[package_uid].append(file_path)

    created_packages = 0

    for package_data in packages_data:
        package_uid = package_data.get("package_uid")
        if not package_uid:
            continue


        resource_paths = resource_paths_by_package_uid.get(package_uid, [])

        resources = project.codebaseresources.filter(path__in=resource_paths)

        package, created = pipes.update_or_create_package(project, package_data)
        if created:
            created_packages += 1

        if package and resources.exists():
            package.add_resources(resources)

        for file_data in files_data:
            if file_data.get("path") in resource_paths:
                extra_data = file_data.get("extra_data", {})
                if extra_data:
                    resource = project.codebaseresources.filter(
                        path=file_data["path"]
                    ).first()
                    if resource:
                        resource.update_extra_data(extra_data)

    return created_packages

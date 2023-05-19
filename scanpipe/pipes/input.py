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

import shutil
from pathlib import Path

import openpyxl

from scanpipe import pipes
from scanpipe.pipes import scancode


def copy_input(input_location, dest_path):
    """Copy the ``input_location`` to the ``dest_path``."""
    destination = dest_path / Path(input_location).name
    return shutil.copyfile(input_location, destination)


def copy_inputs(input_locations, dest_path):
    """Copy the provided ``input_locations`` to the ``dest_path``."""
    for input_location in input_locations:
        copy_input(input_location, dest_path)


def move_inputs(inputs, dest_path):
    """Move the provided ``inputs`` to the ``dest_path``."""
    for input_location in inputs:
        destination = dest_path / Path(input_location).name
        shutil.move(input_location, destination)


def get_tool_name_from_scan_headers(scan_data):
    """Return the ``tool_name`` of the first header in the provided ``scan_data``."""
    if headers := scan_data.get("headers", []):
        first_header = headers[0]
        tool_name = first_header.get("tool_name", "")
        return tool_name


def load_inventory_from_toolkit_scan(project, input_location):
    """
    Create packages, dependencies, and resources loaded from the ScanCode-toolkit scan
    results located at ``input_location``.
    """
    scanned_codebase = scancode.get_virtual_codebase(project, input_location)
    scancode.create_discovered_packages(project, scanned_codebase)
    scancode.create_codebase_resources(project, scanned_codebase)
    scancode.create_discovered_dependencies(
        project, scanned_codebase, strip_datafile_path_root=True
    )


def load_inventory_from_scanpipe(project, scan_data):
    """
    Create packages, dependencies, resources, and relations loaded from a ScanCode.io
    JSON output provided as ``scan_data``.
    """
    for package_data in scan_data.get("packages", []):
        pipes.update_or_create_package(project, package_data)

    for resource_data in scan_data.get("files", []):
        pipes.update_or_create_resource(project, resource_data)

    for dependency_data in scan_data.get("dependencies", []):
        pipes.update_or_create_dependency(project, dependency_data)

    for relation_data in scan_data.get("relations", []):
        pipes.get_or_create_relation(project, relation_data)


worksheet_name_to_object_maker = {
    "PACKAGES": pipes.update_or_create_package,
    "DEPENDENCIES": pipes.update_or_create_dependency,
    "RESOURCES": pipes.update_or_create_resource,
    "RELATIONS": pipes.get_or_create_relation,
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


def load_inventory_from_xlsx(project, input_location):
    """
    Create packages, dependencies, resources, and relations loaded from XLSX file
    located at ``input_location``.
    """
    workbook = openpyxl.load_workbook(input_location, read_only=True, data_only=True)

    for worksheet_name, object_maker in worksheet_name_to_object_maker.items():
        if worksheet_name not in workbook:
            continue

        worksheet_data = get_worksheet_data(worksheet=workbook[worksheet_name])
        for entry_data in worksheet_data:
            # TODO: "for_packages", "holders", "copyrights" are STR not JSON
            if entry_data.get("for_packages"):
                entry_data["for_packages"] = [entry_data["for_packages"]]
            object_maker(project, entry_data)

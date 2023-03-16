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


def copy_input(input_location, dest_path):
    """Copy the `input_location` to the `dest_path`."""
    destination = dest_path / Path(input_location).name
    shutil.copyfile(input_location, destination)


def copy_inputs(input_locations, dest_path):
    """Copy the provided `input_locations` to the `dest_path`."""
    for input_location in input_locations:
        copy_input(input_location, dest_path)


def move_inputs(inputs, dest_path):
    """Move the provided `inputs` to the `dest_path`."""
    for input_location in inputs:
        destination = dest_path / Path(input_location).name
        shutil.move(input_location, destination)


def get_tool_name_from_scan_headers(scan_data):
    """Return the `tool_name` value of the first header in the provided `scan_data`."""
    if headers := scan_data.get("headers", []):
        first_header = headers[0]
        tool_name = first_header.get("tool_name", "")
        return tool_name

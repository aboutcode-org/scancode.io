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

# isort:skip_file

import django

django.setup()

from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import step
from scanpipe.pipes import scancode


class LoadInventoryFromScanCodeScan(Pipeline):
    """
    A pipeline to load a files and packages inventory from a ScanCode JSON scan.
    (assumed to contain file information and package scan data).
    """

    @step
    def start(self):
        """
        Load the Project instance.
        """
        self.project = self.get_project(self.project_name)
        self.next(self.get_scan_json_input)

    @step
    def get_scan_json_input(self):
        """
        Locate the JSON scan input from the project input/ directory.
        """
        inputs = list(self.project.inputs(pattern="*.json"))
        if len(inputs) != 1:
            raise Exception("Only 1 JSON input file supported")
        self.input_location = str(inputs[0].absolute())
        self.next(self.build_inventory_from_scan)

    @step
    def build_inventory_from_scan(self):
        """
        Process the JSON scan to populate resources and packages.
        """
        project = self.project
        scanned_codebase = scancode.get_virtual_codebase(project, self.input_location)
        scancode.create_codebase_resources(project, scanned_codebase)
        scancode.create_discovered_packages(project, scanned_codebase)
        self.next(self.end)

    @step
    def end(self):
        """
        Inventory loaded.
        """


if __name__ == "__main__":
    LoadInventoryFromScanCodeScan()

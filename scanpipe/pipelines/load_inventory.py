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

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import scancode


class LoadInventory(Pipeline):
    """
    A pipeline to load one or more inventory of files and packages from a ScanCode JSON
    scan results. (Presumably containing resource information and package scan data).
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_scan_json_inputs,
            cls.build_inventory_from_scans,
        )

    def get_scan_json_inputs(self):
        """
        Locate all the ScanCode JSON scan results from the project's input/ directory.
        This includes all files with a .json extension.
        """
        self.input_locations = [
            str(scan_input.absolute())
            for scan_input in self.project.inputs(pattern="*.json")
        ]

    def build_inventory_from_scans(self):
        """
        Process JSON scan results files to populate codebase resources and packages.
        """
        for input_location in self.input_locations:
            scancode.create_inventory_from_scan(self.project, input_location)

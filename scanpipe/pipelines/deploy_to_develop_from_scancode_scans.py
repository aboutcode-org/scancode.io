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
from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipelines.load_inventory import LoadInventory
from scanpipe.pipes import scancode


class DeployToDevelopFromScancodeScans(DeployToDevelop, LoadInventory):
    """
    Relate deploy and develop code trees.

    This pipeline is expecting 1 scancode-toolkit scan 1 archive file with "from-" and "to-" filename
    prefixes as inputs:
    - "from-[FILENAME]" archive containing the scancode-toolkit scan results
    - "to-[FILENAME]" archive containing the deployment compiled code
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.build_inventory_from_scans,
            cls.extract_inputs_to_codebase_directory,
            cls.extract_archives_in_place,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_and_ignored_files,
            cls.map_checksum,
            cls.map_path,
            cls.flag_mapped_resources_and_ignored_directories,
        )

    extract_recursively = True

    def extract_inputs_to_codebase_directory(self):
        """Extract input files to the project's codebase/ directory."""
        errors = []
        errors += scancode.extract_archive(self.to_file, self.to_path)

        if errors:
            self.add_error("\n".join(errors))
    
    def build_inventory_from_scans(self):
        """
        Process JSON scan results files to populate packages, dependencies, and
        resources.
        """
        scan_data = json.loads(self.from_file.read_text())
        tool_name = input.get_tool_name_from_scan_headers(scan_data)

        if tool_name == "scancode-toolkit":
            scancode.load_inventory_from_toolkit_scan(self.project, self.from_path)
        else:
            raise Exception(f"Input not supported: {str(self.from_file)} ")

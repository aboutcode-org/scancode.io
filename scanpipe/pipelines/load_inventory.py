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

import json

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import input


class LoadInventory(Pipeline):
    """
    Load JSON/XLSX inventory files generated with ScanCode-toolkit or ScanCode.io.

    Supported format are ScanCode-toolkit JSON scan results, ScanCode.io JSON output,
    and ScanCode.io XLSX output.

    Additionally supports importing scan results from integrated tools:
    - VulnerableCode: Vulnerability data export
    - PurlDB: Package enrichment data export
    - MatchCode.io: Matching results export

    An inventory is composed of packages, dependencies, resources, and relations.
    """

    supported_extensions = [".json", ".xlsx"]

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.build_inventory_from_scans,
        )

    def get_inputs(self):
        """Locate all the supported input files from the project's input/ directory."""
        self.input_paths = self.project.inputs(extensions=self.supported_extensions)

    def build_inventory_from_scans(self):
        """
        Process JSON scan results files to populate packages, dependencies, and
        resources.
        """
        self.input_paths = list(self.input_paths)
        is_single_input = len(self.input_paths) == 1

        for input_path in self.input_paths:
            extra_data_prefix = None if is_single_input else input_path.name

            if input_path.suffix.endswith(".xlsx"):
                input.load_inventory_from_xlsx(
                    self.project, input_path, extra_data_prefix
                )
                continue

            scan_data = json.loads(input_path.read_text())
            tool_name = input.get_tool_name_from_scan_headers(scan_data)

            if tool_name == "scancode-toolkit":
                input.load_inventory_from_toolkit_scan(self.project, input_path)

            elif tool_name == "scanpipe":
                input.load_inventory_from_scanpipe(
                    self.project, scan_data, extra_data_prefix
                )

            else:
                integrated_tool = input.get_integrated_tool_name(scan_data)

                if integrated_tool == "vulnerablecode":
                    updated_count = input.load_vulnerabilities_from_vulnerablecode(
                        self.project, scan_data
                    )
                    self.log(
                        f"Loaded vulnerability data for {updated_count} packages "
                        f"from {input_path.name}"
                    )

                elif integrated_tool == "purldb":
                    result = input.load_enrichment_from_purldb(self.project, scan_data)
                    self.log(
                        f"PurlDB import: {result['created']} packages created, "
                        f"{result['updated']} packages updated from {input_path.name}"
                    )

                elif integrated_tool == "matchcodeio":
                    created_count = input.load_matches_from_matchcode(
                        self.project, scan_data
                    )
                    self.log(
                        f"MatchCode.io import: {created_count} packages created "
                        f"from {input_path.name}"
                    )

                else:
                    raise Exception(f"Input not supported: {str(input_path)} ")

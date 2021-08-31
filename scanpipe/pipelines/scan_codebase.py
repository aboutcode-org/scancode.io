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
from scanpipe.pipes import output
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_inputs


class ScanCodebase(Pipeline):
    """
    A pipeline to scan a codebase resource with ScanCode-toolkit.

    Input files are copied to the project's codebase/ directory and are extracted
    in place before running the scan.
    Alternatively, the code can be manually copied to the project codebase/
    directory.
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.run_scancode,
            cls.build_inventory_from_scan,
            cls.csv_output,
        )

    # Set to True to extract recursively nested archives in archives.
    extract_recursively = False

    scancode_options = [
        "--copyright",
        "--email",
        "--info",
        "--license",
        "--license-text",
        "--package",
        "--url",
    ]

    def copy_inputs_to_codebase_directory(self):
        """
        Copies input files to the project's codebase/ directory.
        The code can also be copied there prior to running the Pipeline.
        """
        copy_inputs(self.project.inputs(), self.project.codebase_path)

    def extract_archives(self):
        """
        Extracts archives with extractcode.
        """
        extract_errors = scancode.extract_archives(
            location=self.project.codebase_path,
            recurse=self.extract_recursively,
        )

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def run_scancode(self):
        """
        Scans extracted codebase/ content.
        """
        self.scan_output = self.project.get_output_file_path("scancode", "json")

        with self.save_errors(scancode.ScancodeError):
            scancode.run_scancode(
                location=str(self.project.codebase_path),
                output_file=str(self.scan_output),
                options=self.scancode_options,
                raise_on_error=True,
            )

        if not self.scan_output.exists():
            raise FileNotFoundError("ScanCode output not available.")

    def build_inventory_from_scan(self):
        """
        Processes the JSON scan results to determine resources and packages.
        """
        project = self.project
        scanned_codebase = scancode.get_virtual_codebase(project, str(self.scan_output))
        scancode.create_codebase_resources(project, scanned_codebase)
        scancode.create_discovered_packages(project, scanned_codebase)

    def csv_output(self):
        """
        Generates a .csv output.
        """
        output.to_csv(self.project)

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

from scanpipe.pipelines import scan_codebase
from scanpipe.pipes import glc


class GLicenseScan(scan_codebase.ScanCodebase):
    """
    A pipeline to scan a codebase with GoLicense-Classifier for Copyright and License Detection
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.run_extractcode,
            cls.run_glc,
            cls.build_inventory_from_scan,
            cls.csv_output,
        )

    def run_glc(self):
        """
        Scan extracted codebase/ content.
        """
        self.scan_output = self.project.get_output_file_path("scancode", "json")
        # print(self.scan_output)
        glc.run_glc(
            location=str(self.project.codebase_path),
            output_file=str(self.scan_output),
        )

        if not self.scan_output.exists():
            raise FileNotFoundError("GLC output not available.")

    def build_inventory_from_scan(self):
        """
        Process the JSON scan results to populate resources and packages.
        """
        project = self.project
        scan_data = glc.to_dict(str(self.scan_output))
        glc.create_codebase_resources(project, scan_data)

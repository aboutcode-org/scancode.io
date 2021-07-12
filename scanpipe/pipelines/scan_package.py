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

from django.core.serializers.json import DjangoJSONEncoder

from commoncode.hash import multi_checksums

from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes import scancode


class ScanPackage(ScanCodebase):
    """
    A pipeline to scan a single package archive with ScanCode-toolkit.
    The output is a summary of scan results as a JSON file.
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_package_archive_input,
            cls.collect_archive_information,
            cls.extract_archive_to_codebase_directory,
            cls.run_scancode,
            cls.build_inventory_from_scan,
            cls.make_summary_from_scan_results,
        )

    scancode_options = ScanCodebase.scancode_options + [
        "--classify",
        "--consolidate",
        "--is-license-text",
        "--license-clarity-score",
        "--summary",
        "--summary-key-files",
    ]

    def get_package_archive_input(self):
        """
        Locate the package archive in the project input/ directory.
        """
        input_files = self.project.input_files
        inputs = list(self.project.inputs())

        if len(inputs) != 1 or len(input_files) != 1:
            raise Exception("Only 1 input file supported")

        self.archive_path = inputs[0]

    def collect_archive_information(self):
        """
        Collect information about the input archive and store the data on project.
        """
        self.project.update_extra_data(
            {
                "filename": self.archive_path.name,
                "size": self.archive_path.stat().st_size,
                **multi_checksums(self.archive_path),
            }
        )

    def extract_archive_to_codebase_directory(self):
        """
        Extract package archive with extractcode.
        """
        extract_errors = scancode.extract(self.archive_path, self.project.codebase_path)

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def make_summary_from_scan_results(self):
        """
        Build a summary from the JSON scan results.
        """
        summary = scancode.make_results_summary(self.project, str(self.scan_output))
        output_file = self.project.get_output_file_path("summary", "json")

        with output_file.open("w") as summary_file:
            summary_file.write(json.dumps(summary, indent=2, cls=DjangoJSONEncoder))

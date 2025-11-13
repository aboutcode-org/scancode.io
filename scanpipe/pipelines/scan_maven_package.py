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

from scanpipe.pipelines.scan_single_package import ScanSinglePackage

from scanpipe.pipes.resolve import get_pom_url_list
from scanpipe.pipes.resolve import download_and_scan_pom_file


class ScanMavenPackage(ScanSinglePackage):
    """
    Scan a single package archive (or package manifest file).

    This pipeline scans a single package for package metadata,
    declared dependencies, licenses, license clarity score and copyrights.

    The output is a summary of the scan results in JSON format.
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_package_input,
            cls.collect_input_information,
            cls.extract_input_to_codebase_directory,
            cls.extract_archives,
            cls.run_scan,
            cls.fetch_and_scan_remote_pom,
            cls.load_inventory_from_toolkit_scan,
            cls.make_summary_from_scan_results,
        )

    def fetch_and_scan_remote_pom(self):
        """Fetch the pom.xml file from from maven.org if not present in codebase."""
        with open(self.scan_output_location, 'r') as file:
            data = json.load(file)
            # Return and do nothing if data has pom.xml
            for file in data['files']:
                if 'pom.xml' in file['path']:
                    return
            packages = data.get("packages", [])

        pom_url_list = get_pom_url_list(self.project.input_sources[0], packages)
        scanned_pom_packages, scanned_dependencies = download_and_scan_pom_file(pom_url_list)

        updated_pacakges = packages + scanned_pom_packages
        # Replace/Update the package and dependencies section
        data['packages'] = updated_pacakges
        data['dependencies'] = scanned_dependencies
        with open(self.scan_output_location, 'w') as file:
            json.dump(data, file, indent=2)

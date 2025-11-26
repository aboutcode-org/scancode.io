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

from scanpipe.pipelines.scan_single_package import ScanSinglePackage
from scanpipe.pipes.maven import fetch_and_scan_remote_pom
from scanpipe.pipes.maven import update_package_license_from_resource_if_missing


class ScanMavenPackage(ScanSinglePackage):
    """
    Scan a single maven package archive.

    This pipeline scans a single maven package for package metadata,
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
            cls.update_package_license_from_resource_if_missing,
            cls.make_summary_from_scan_results,
        )

    def fetch_and_scan_remote_pom(self):
        """Fetch and scan remote POM files."""
        scanning_errors = fetch_and_scan_remote_pom(
            self.project, self.scan_output_location
        )
        if scanning_errors:
            for scanning_error in scanning_errors:
                for resource_path, errors in scanning_error.items():
                    self.project.add_error(
                        description="\n".join(errors),
                        model=self.pipeline_name,
                        details={
                            "resource_path": resource_path.removeprefix("codebase/")
                        },
                    )

    def update_package_license_from_resource_if_missing(self):
        """Update PACKAGE license from the license detected in RESOURCES if missing."""
        update_package_license_from_resource_if_missing(self.project)

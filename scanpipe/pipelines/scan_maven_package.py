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

from aboutcode.pipeline import optional_step
from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipelines.scan_single_package import ScanSinglePackage
from scanpipe.pipes.maven import fetch_and_scan_remote_pom
from scanpipe.pipes.maven import update_package_license_from_resource_if_missing


class ScanMavenPackage(ScanSinglePackage, DeployToDevelop):
    """
    Scan a single maven package archive.

    This pipeline scans a single maven package for package metadata,
    declared dependencies, licenses, license clarity score and copyrights.

    The output is a summary of the scan results in JSON format.
    """

    d2d_option_enabled = False

    @classmethod
    def steps(cls):
        return (
            cls.check_option_status,
            cls.get_input,
            cls.collect_input_info,
            cls.extract_input,
            cls.extract_archives,
            cls.maven_d2d_steps,
            cls.run_scan,
            cls.fetch_and_scan_remote_pom,
            cls.load_inventory_from_toolkit_scan,
            cls.update_package_license_from_resource_if_missing,
            cls.make_summary_from_scan_results,
        )

    @optional_step("deploy_to_develop")
    def check_option_status(self):
        """Set d2d_option_enabled to True."""
        self.d2d_option_enabled = True

    def get_input(self):
        """Locate the the input."""
        if not self.d2d_option_enabled:
            self.get_package_input()
        else:
            self.get_inputs()

    def collect_input_info(self):
        """Collect information about the input."""
        if not self.d2d_option_enabled:
            self.collect_input_information()

    def extract_input(self):
        """Extract the input to the codebase directory."""
        if not self.d2d_option_enabled:
            self.extract_input_to_codebase_directory()
        else:
            self.extract_inputs_to_codebase_directory()

    @optional_step("deploy_to_develop")
    def maven_d2d_steps(self):
        """Run D2D steps for Maven projects."""
        # The following langages will be included:
        # - Java
        # - Kotlin
        # - Scala
        # - JavaScript
        from scanpipe.pipes import d2d_config

        self.collect_and_create_codebase_resources()
        self.fingerprint_codebase_directories()
        self.flag_empty_files()
        self.flag_whitespace_files()
        self.flag_ignored_resources()

        options = ["Java", "Kotlin", "Scala", "JavaScript"]
        d2d_config.load_ecosystem_config(pipeline=self, options=options)

        self.map_about_files()
        self.map_checksum()
        self.match_archives_to_purldb()
        # Java
        self.find_java_packages()
        self.map_java_to_class()
        self.map_jar_to_java_source()
        # Scala
        self.find_scala_packages()
        self.map_scala_to_class()
        self.map_jar_to_scala_source()
        # Kotlin
        self.find_kotlin_packages()
        self.map_kotlin_to_class()
        self.map_jar_to_kotlin_source()
        # JavaScript
        self.map_javascript()
        self.map_javascript_symbols()
        self.map_javascript_strings()
        self.get_symbols_from_binaries()
        self.map_elf()
        self.match_directories_to_purldb()
        self.match_resources_to_purldb()
        self.map_javascript_post_purldb_match()
        self.map_javascript_path()
        self.map_javascript_colocation()
        self.map_path()
        self.flag_mapped_resources_archives_and_ignored_directories()
        self.perform_house_keeping_tasks()
        self.match_purldb_resources_post_process()
        self.remove_packages_without_resources()
        self.scan_ignored_to_files()
        self.scan_unmapped_to_files()
        self.scan_mapped_from_for_files()
        self.collect_and_create_license_detections()
        self.flag_deployed_from_resources_with_missing_license()
        self.create_local_files_packages()

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

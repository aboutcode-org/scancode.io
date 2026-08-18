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

from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipelines.scan_single_package import ScanSinglePackage
from scanpipe.pipes import d2d
from scanpipe.pipes import flag
from scanpipe.pipes import nix
from scanpipe.pipes import utils
from scanpipe.pipes.nix import check_input_and_return_purl
from scanpipe.pipes.nix import cleanup_docker_volumes
from scanpipe.pipes.nix import fetch_inputs


class ScanNixPackage(ScanSinglePackage, DeployToDevelop, ScanCodebase):
    """
    Download the nix source and binary, and run a deployment to development
    scan between the binary and the source to detect any discrepancies.

    Scan the sources and confirm that the detected license aligns with
    the declared license that is detected from the nix package.
    """

    download_inputs = False

    @classmethod
    def steps(cls):
        return (
            cls.check_input_and_return_purl,
            cls.check_docker_command,
            cls.fetch_inputs,
            cls.collect_input_info,
            cls.extract_input_to_codebase_directory,
            cls.run_scan,
            cls.load_inventory_from_toolkit_scan,
            cls.add_from_to_tag,
            cls.d2d_steps,
            cls.validate_package_license_integrity,
            cls.flag_mapped_status,
            cls.make_summary_from_scan_results,
            cls.cleanup_docker_volumes,
        )

    def check_input_and_return_purl(self):
        """Validate the input is a PURL string and return the PURL object."""
        self.purl = check_input_and_return_purl(self.project)

    def check_docker_command(self):
        """Check if the Docker command is available."""
        if not utils.check_docker_command():
            raise Exception("Docker is required and its daemon must be running.")
        nix.ensure_multiarch_emulation()

    def fetch_inputs(self):
        """Fetch the binary and source of the given PURL."""
        from_file = ""
        to_file = ""
        output_format = ""
        from_file, to_file, output_format = fetch_inputs(
            self.purl, self.project.codebase_path
        )
        self.from_file = from_file
        self.to_file = to_file
        self.output_format = output_format

        self.d2d_enable = bool(self.from_file and self.to_file)

    def collect_input_info(self):
        """Collect information about the input."""
        self.input_path = ""
        if self.to_file:
            self.input_path = self.to_file
            self.collect_input_information()

    def extract_input_to_codebase_directory(self):
        """Extract input to project codebase/ directory."""
        if self.input_path:
            nix.extract_nar_archive(
                self.input_path, self.project.codebase_path, self.output_format
            )

            # Reload the project env post-extraction as the scancode-config.yml file
            # may be located in one of the extracted archives.
            self.env = self.project.get_env()

    def add_from_to_tag(self):
        """Update 'from' and 'to' tag to resources based on their path."""
        d2d.update_from_to_tag(self.project)

    def d2d_steps(self):
        """
        Run the deployment to development scan if both the source and
        binary are available.
        """
        if self.d2d_enable:
            self.flag_empty_files()
            self.flag_whitespace_files()
            self.flag_ignored_resources()
            self.map_about_files()
            self.map_checksum()
            self.match_archives_to_purldb()
            self.load_ecosystem_config()
            self.d2d_java()
            self.d2d_scala()
            self.d2d_kotlin()
            self.d2d_grammar()
            self.d2d_groovy()
            self.d2d_aspectj()
            self.d2d_clojure()
            self.d2d_xtend()
            self.d2d_javascript()
            self.d2d_process()

    def d2d_java(self):
        self.find_java_packages()
        self.map_java_to_class()
        self.map_jar_to_java_source()

    def d2d_scala(self):
        self.find_scala_packages()
        self.map_scala_to_class()
        self.map_jar_to_scala_source()

    def d2d_kotlin(self):
        self.find_kotlin_packages()
        self.map_kotlin_to_class()
        self.map_jar_to_kotlin_source()

    def d2d_grammar(self):
        self.find_grammar_packages()
        self.map_grammar_to_class()
        self.map_jar_to_grammar_source()

    def d2d_groovy(self):
        self.find_groovy_packages()
        self.map_groovy_to_class()
        self.map_jar_to_groovy_source()

    def d2d_aspectj(self):
        self.find_aspectj_packages()
        self.map_aspectj_to_class()
        self.map_jar_to_aspectj_source()

    def d2d_clojure(self):
        self.find_clojure_packages()
        self.map_clojure_to_class()
        self.map_jar_to_clojure_source()

    def d2d_xtend(self):
        self.find_xtend_packages()
        self.map_xtend_to_class()

    def d2d_javascript(self):
        self.map_javascript()
        self.map_javascript_symbols()
        self.map_javascript_strings()

    def d2d_process(self):
        self.get_symbols_from_binaries()
        self.map_elf()
        self.map_macho()
        self.map_winpe()
        self.map_go()
        self.map_rust()
        self.map_python()
        self.match_directories_to_purldb()
        self.match_resources_to_purldb()
        self.map_javascript_post_purldb_match()
        self.map_javascript_path()
        self.map_javascript_colocation()
        self.map_thirdparty_npm_packages()
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

    def validate_package_license_integrity(self):
        """
        Validate the correctness of the package license compare with the
        detected license from the codebase.
        """
        utils.validate_package_license_integrity(self.project)

    def flag_mapped_status(self):
        """Flag the from codebase resources that were mapped."""
        if self.d2d_enable:
            flag.flag_mapped_resources(self.project)

    def cleanup_docker_volumes(self):
        """Cleanup the Docker volumes used for Nix."""
        cleanup_docker_volumes()

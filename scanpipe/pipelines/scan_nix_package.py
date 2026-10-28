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

import shutil
from pathlib import Path

from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipelines.scan_single_package import ScanSinglePackage
from scanpipe.pipes import d2d_config
from scanpipe.pipes import flag
from scanpipe.pipes import license_validation
from scanpipe.pipes import nix
from scanpipe.pipes import scancode
from scanpipe.pipes import utils


class ScanNixPackage(ScanSinglePackage, DeployToDevelop, ScanCodebase):
    """
    Fetch and build a Nix package to detect discrepancies and validate licenses.

    Download the nix source and binary, and run a deployment to development
    scan between the binary and the source to detect any discrepancies.

    Scan the sources and confirm that the detected license aligns with
    the declared license that is detected from the nix package.

    The ``commit`` qualifier in the Nix PURL is validated against the
    official NixOS/nixpkgs repository history. Commits that exist only in
    forks or unmerged pull requests are rejected.
    """

    download_inputs = False

    # A Nix derivation can target any language, so we load every ecosystem
    # the D2D mappers support.
    D2D_ECOSYSTEM_OPTIONS = [
        name for name in d2d_config.ECOSYSTEM_CONFIGS if name != "Default"
    ]

    @classmethod
    def get_availability(cls):
        if not shutil.which("docker"):
            return (
                "Docker CLI is not available. Use the 'dind' Compose profile "
                "(docker compose --profile dind up), or install the Docker CLI "
                "in your custom image."
            )

        if utils.has_docker_endpoint():
            return

        return (
            "No Docker daemon endpoint found: DOCKER_HOST is not set and "
            f"{utils.DEFAULT_DOCKER_SOCKET} does not exist. For a Docker Compose "
            "deployment, use the 'dind' profile and uncomment DOCKER_HOST in "
            "docker.env; otherwise set DOCKER_HOST to a reachable Docker daemon."
        )

    @classmethod
    def steps(cls):
        return (
            cls.check_input_and_return_purl,
            cls.prepare_nix_environment,
            cls.fetch_inputs,
            cls.collect_input_info,
            cls.extract_input_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.fingerprint_codebase_directories,
            cls.flag_empty_files,
            cls.flag_whitespace_files,
            cls.flag_ignored_resources,
            cls.d2d_steps,
            cls.perform_from_codebase_scans,
            cls.collect_and_create_license_detections,
            cls.flag_deployed_from_resources_with_missing_license,
            cls.create_package_from_nix_metadata,
            cls.validate_package_license_integrity,
        )

    def check_input_and_return_purl(self):
        """Validate the input is a Nix PURL string and return the PURL object."""
        self.purl = nix.check_input_and_return_purl(self.project)

    def prepare_nix_environment(self):
        """Ensure the custom Nix image exists and run the periodic store GC."""
        nix.prepare_nix_environment()

    def fetch_inputs(self):
        """Fetch the binary and source of the given PURL."""
        try:
            (
                self.from_file,
                self.to_file,
                self.output_format,
                self.concluded_commit_hash,
                error_messages,
                warning_messages,
            ) = nix.fetch_inputs(self.purl, self.project.codebase_path)

            self.d2d_enable = bool(self.from_file and self.to_file)
        finally:
            nix.cleanup_nixpkgs_worktrees()

        for error_message in error_messages:
            self.project.add_error(error_message)
        for warning_message in warning_messages:
            self.project.add_warning(warning_message)

    def collect_input_info(self):
        """Collect information about the input."""
        self.input_path = ""
        if self.to_file:
            self.input_path = Path(self.to_file)
            self.collect_input_information()

    def extract_input_to_codebase_directory(self):
        """Extract input to project codebase/ directory."""
        if not self.input_path:
            return

        success, error_message = nix.extract_nar_archive_to_codebase(
            archive_path=self.input_path,
            codebase_path=self.project.codebase_path,
            output_format=self.output_format,
        )
        if not success:
            self.d2d_enable = False
            self.project.add_error(error_message)

        self.env = self.project.get_env()

    def d2d_steps(self):
        """
        Run the deployment to development scan if both the source and
        binary are available.
        """
        if self.d2d_enable:
            self.d2d_ecosystem_config()
            self.map_about_files()
            self.map_checksum()
            self.match_archives_to_purldb()
            self.d2d_java()
            self.d2d_scala()
            self.d2d_kotlin()
            self.d2d_grammar()
            self.d2d_groovy()
            self.d2d_aspectj()
            self.d2d_clojure()
            self.d2d_xtend()
            self.d2d_javascript()
            self.d2d_haskell()
            self.d2d_process()

    def d2d_ecosystem_config(self):
        d2d_config.load_ecosystem_config(
            pipeline=self, options=self.D2D_ECOSYSTEM_OPTIONS
        )

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

    def d2d_haskell(self):
        self.map_haskell()

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
        self.flag_generated_code()
        self.flag_mapped_resources_archives_and_ignored_directories()
        self.perform_house_keeping_tasks()
        self.match_purldb_resources_post_process()
        self.remove_packages_without_resources()
        self.scan_ignored_to_files()
        self.scan_unmapped_to_files()

    def perform_from_codebase_scans(self):
        """
        Scan the source codebase for application packages and file details with
        filtering out resources that are flagged as generated or ignored.
        """
        from_resource_qs = (
            self.project.codebaseresources.from_codebase()
            .files()
            .exclude(status=flag.GENERATED)
            .exclude(status__startswith="ignored")
        )
        scancode.scan_for_application_packages(
            project=self.project, resource_qs=from_resource_qs, progress_logger=self.log
        )

        scancode.scan_for_files(
            project=self.project, resource_qs=from_resource_qs, progress_logger=self.log
        )

    def create_package_from_nix_metadata(self):
        """
        Create a DiscoveredPackage for the Nix package using the declared
        license from nixpkgs ``meta.license``. This is used to compare the
        declared license against the licenses detected in the source and
        binary trees.
        """
        metadata = nix.get_nix_package_metadata(
            purl=self.purl, commit_hash=self.concluded_commit_hash
        )
        if not metadata:
            return

        package = nix.create_package_from_nix_metadata(
            self.project, self.purl, metadata
        )
        if not package:
            return

        from_resources = self.project.codebaseresources.from_codebase()
        nix.add_codebase_resources_to_package(package, from_resources)

    def validate_package_license_integrity(self):
        """
        Validate the correctness of the package license compared with the
        detected license from the codebase.
        """
        license_validation.validate_package_license_integrity(self.project)

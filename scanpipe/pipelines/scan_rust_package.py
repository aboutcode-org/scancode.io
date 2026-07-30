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

from pathlib import Path

from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipelines.scan_single_package import ScanSinglePackage
from scanpipe.pipes import d2d
from scanpipe.pipes import flag
from scanpipe.pipes import rust
from scanpipe.pipes import utils

from scanpipe.pipes.rust import check_input_and_return_purl, fetch_inputs

import shutil


class ScanRustPackage(ScanSinglePackage, DeployToDevelop, ScanCodebase):
    """
    Download the crate’s source, build it, and run a d2d comparison between
    the compiled binary and the source crate to detect any discrepancies.

    Identify the upstream source repository and verify that it matches the
    contents of the source crate.

    Scan the source crate and confirm that the detected license aligns with
    the license declared in Cargo.toml.

    Compare the crate’s source code against all other crates (MatchCode),
    excluding itself, to detect any borrowed code from third-party crates.
    """

    download_inputs = False

    @classmethod
    def steps(cls):
        return (
            cls.check_input_and_return_purl,
            cls.fetch_inputs,
            cls.collect_input_info,
            cls.extract_input_to_codebase_directory,
            cls.check_docker_command,
            cls.build_crates,
            cls.run_scan,
            cls.load_inventory_from_toolkit_scan,
            cls.add_from_to_tag,
            cls.validate_package_license_integrity,
            cls.identify_built_sources,
            cls.flag_mapped_status,
            cls.make_summary_from_scan_results,
        )

    def check_input_and_return_purl(self):
        """Validate the input is a PURL string and return the PURL object."""
        self.purl = check_input_and_return_purl(self.project)

    def fetch_inputs(self):
        """Fetch the source of the given PURL."""
        self.from_files = fetch_inputs(self.purl)

    def collect_input_info(self):
        """Collect information about the input."""
        self.input_path = self.from_files
        self.collect_input_information()

    def check_docker_command(self):
        self.have_docker = False
        if shutil.which("docker"):
            self.have_docker = True

    def build_crates(self):
        """
        Build the Rust crate using Docker and put the built files under the
        "to" directory.
        """
        self.d2d_enable = False
        if self.have_docker:
            if rust.build_crates(self.project.codebase_path):
                self.d2d_enable = True
            else:
                print("Docker command not found. Skipping crate build.")

    def add_from_to_tag(self):
        """Update 'from' or 'to' tag to resources based on their path."""
        if self.d2d_enable:
            d2d.update_from_to_tag(self.project)

    def validate_package_license_integrity(self):
        """
        Validate the correctness of the package license compare with the
        detected license from the codebase.
        """
        utils.validate_package_license_integrity(self.project)

    def identify_built_sources(self):
        """Identify the built sources from the '.d' file in the "to" directory."""
        if self.d2d_enable:
            d2d.map_rust_paths(self.project)

    def flag_mapped_status(self):
        """Flag the from codebase resources that were mapped."""
        if self.d2d_enable:
            flag.flag_mapped_resources(self.project)

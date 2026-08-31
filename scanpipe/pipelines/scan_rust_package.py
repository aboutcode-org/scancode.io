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

import tempfile
from pathlib import Path

from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipelines.scan_single_package import ScanSinglePackage
from scanpipe.pipes import d2d
from scanpipe.pipes import flag
from scanpipe.pipes import utils
from scanpipe.pipes.rust import build_crates
from scanpipe.pipes.rust import check_input_and_return_purl
from scanpipe.pipes.rust import get_cargo_toml_path
from scanpipe.pipes.rust import get_repository_value_from_cargo_toml


class ScanRustPackage(ScanSinglePackage, DeployToDevelop, ScanCodebase):
    """
    Download the crate’s source, build it, and run a d2d comparison between
    the compiled binary and the source crate to detect any discrepancies.

    Identify the upstream source repository and verify that it matches the
    contents of the source crate.

    Scan the source crate and confirm that the detected license aligns with
    the license declared in Cargo.toml.
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
            cls.get_cargo_toml,
            cls.build_crates,
            cls.run_scan,
            cls.load_inventory_from_toolkit_scan,
            cls.add_from_to_tag,
            cls.validate_package_license_integrity,
            cls.identify_built_sources,
            cls.flag_mapped_status,
            cls.get_src_repo_download_url,
            cls.download_src_repo,
            cls.compare_src_repo_with_from_codebase,
            cls.update_comparison_summary,
            cls.make_summary_from_scan_results,
        )

    def check_input_and_return_purl(self):
        """Validate the input is a PURL string and return the PURL object."""
        self.purl = check_input_and_return_purl(self.project)

    def fetch_inputs(self):
        """Fetch the source of the given PURL."""
        self.from_files = utils.fetch_inputs(self.purl)

    def collect_input_info(self):
        """Collect information about the input."""
        self.input_path = self.from_files
        self.collect_input_information()

    def check_docker_command(self):
        self.have_docker = False
        """Check if the Docker command is available."""
        if not utils.check_docker_command():
            raise Exception("Docker is required and its daemon must be running.")
        else:
            self.have_docker = True

    def get_cargo_toml(self):
        """Get the Cargo.toml path from the codebase directory."""
        self.cargo_toml_path = None
        self.devel_codebase_dir = None
        if self.have_docker:
            codebase_dir = Path(self.project.codebase_path)
            self.devel_codebase_dir = codebase_dir
            self.cargo_toml_path = get_cargo_toml_path(codebase_dir)

    def build_crates(self):
        """
        Build the Rust crate using Docker and put the built files under the
        "to" directory.
        """
        self.d2d_enable = False
        if self.cargo_toml_path:
            codebase_dir = self.devel_codebase_dir
            cargo_toml_path = self.cargo_toml_path
            if build_crates(codebase_dir, cargo_toml_path):
                self.d2d_enable = True
                updated_path = cargo_toml_path.relative_to(codebase_dir)
                self.cargo_toml_path = codebase_dir / "from" / updated_path
                self.devel_codebase_dir = codebase_dir / "from"
            else:
                print("Docker command not found. Skipping crate build.")
        else:
            print("Cargo.toml is not found.")

    def add_from_to_tag(self):
        """Update 'from' and 'to' tag to resources based on their path."""
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

    def get_src_repo_download_url(self):
        """
        Get the source repository url from Cargo.toml and determine its
        download url.
        """
        self.src_download_url = None
        repository_url = get_repository_value_from_cargo_toml(self.cargo_toml_path)
        if not repository_url:
            self.project.add_warning(
                description="No source repository URL found in Cargo.toml."
            )
        else:
            self.src_download_url = utils.get_download_url(
                repository_url, self.purl.version
            )
            if not self.src_download_url:
                self.project.add_warning(
                    description=(
                        "Not able to determine the source repository download URL from "
                        "Cargo.toml."
                    )
                )

    def download_src_repo(self):
        """Download the source from the source repo."""
        self.src_repo_path = None
        if self.src_download_url:
            self.src_repo_path = utils.download_src_repo(self.src_download_url)
            if not self.src_repo_path:
                self.project.add_warning(
                    description=(
                        f"The source repository URL "
                        f"{self.src_download_url} "
                        f"could not be downloaded. Skipping the source "
                        f"crate and source repository comparison."
                    )
                )

    def compare_src_repo_with_from_codebase(self):
        """Compare the downloaded source repo with the from codebase."""
        self.matched_count = 0
        self.mismatches = []
        if self.src_repo_path:
            with tempfile.TemporaryDirectory() as source_repo_path:
                self.extract_archive(self.src_repo_path, source_repo_path)

                self.matched_count, self.mismatches = utils.compare_directories(
                    self.devel_codebase_dir, source_repo_path
                )

    def update_comparison_summary(self):
        """Update the comparison summary in the discovered package."""
        if self.src_repo_path:
            utils.update_comparison_summary(
                self.project,
                self.purl,
                self.devel_codebase_dir,
                self.src_download_url,
                self.purl.name,
                self.purl.version,
                self.matched_count,
                self.mismatches,
            )

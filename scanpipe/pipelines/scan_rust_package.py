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
from scanpipe.pipes import d2d_config
from scanpipe.pipes import flag
from scanpipe.pipes import license_validation
from scanpipe.pipes import rust
from scanpipe.pipes import source_repo
from scanpipe.pipes import utils


class ScanRustPackage(ScanSinglePackage, DeployToDevelop, ScanCodebase):
    """
    Fetch, build and compare crate source/binary, verify repo match, validate license.

    Download the crate’s source, build it, and run a d2d comparison between
    the compiled binary and the source crate to detect any discrepancies.

    Identify the upstream source repository and verify that it matches the
    contents of the source crate.

    Scan the source crate and confirm that the detected license aligns with
    the license declared in Cargo.toml.

    Deployment notes:
        The pipeline runs ``docker run`` from the worker container. This
        requires two things:

        - The Docker CLI is installed in the worker image.
        - The Docker daemon (``DOCKER_HOST``) can see the same ``workspace``
          volume as the worker.

        The default Compose stack provides both through the ``dind`` service,
        see ``docker-compose.yml``.
    """

    download_inputs = False

    @classmethod
    def get_availability(cls):
        if not utils.check_docker_command():
            return "Docker is required and its daemon must be running."
        return None

    @classmethod
    def steps(cls):
        return (
            cls.check_input_and_return_purl,
            cls.fetch_inputs,
            cls.collect_input_info,
            cls.extract_input_to_codebase_directory,
            cls.get_cargo_toml,
            cls.build_crates,
            cls.run_scan,
            cls.load_inventory_from_toolkit_scan,
            cls.add_from_to_tag,
            cls.validate_package_license_integrity,
            cls.identify_built_sources,
            cls.load_ecosystem_config,
            cls.flag_mapped_status,
            cls.run_house_keeping_tasks,
            cls.get_src_repo_download_url,
            cls.download_src_repo,
            cls.compare_src_repo_with_from_codebase,
            cls.update_comparison_summary,
            cls.make_summary_from_scan_results,
        )

    def check_input_and_return_purl(self):
        """Validate the input is a PURL string and return the PURL object."""
        self.purl = rust.check_input_and_return_purl(self.project)

    def fetch_inputs(self):
        """Fetch the source of the given PURL."""
        self.from_files = rust.fetch_inputs(self.purl)

    def collect_input_info(self):
        """Collect information about the input."""
        self.input_path = self.from_files
        self.collect_input_information()

    def get_cargo_toml(self):
        """Locate the root Cargo.toml of the extracted crate."""
        self.devel_codebase_dir = Path(self.project.codebase_path)
        self.cargo_toml_path = rust.get_cargo_toml_path(
            self.devel_codebase_dir, self.purl
        )
        if not self.cargo_toml_path:
            self.log("Cargo.toml not found in the extracted crate.")

    def build_crates(self):
        """
        Build the Rust crate using Docker and put the built files under the
        "to" directory.
        """
        self.d2d_enable = False
        if not self.cargo_toml_path:
            self.log("Skipping crate build: Cargo.toml not found.")
            return

        (
            self.d2d_enable,
            self.cargo_toml_path,
            self.devel_codebase_dir,
        ) = rust.build_crates(self.devel_codebase_dir, self.cargo_toml_path)

        if not self.d2d_enable:
            self.log("Failed to build the Rust crate. Skipping D2D steps.")

    def add_from_to_tag(self):
        """Update 'from' and 'to' tag to resources based on their path."""
        if self.d2d_enable:
            d2d.update_from_to_tag(self.project)

    def validate_package_license_integrity(self):
        """
        Validate the correctness of the package license compare with the
        detected license from the codebase.
        """
        license_validation.validate_package_license_integrity(self.project)

    def identify_built_sources(self):
        """Identify the built sources from the '.d' file in the "to" directory."""
        if self.d2d_enable:
            d2d.map_rust_paths(self.project, logger=self.log)

    def load_ecosystem_config(self):
        """Load the Rust ecosystem configuration for D2D steps."""
        d2d_config.load_ecosystem_config(pipeline=self, options=["Rust"])

    def flag_mapped_status(self):
        """Flag the from codebase resources that were mapped."""
        if self.d2d_enable:
            flag.flag_mapped_resources(self.project)

    def run_house_keeping_tasks(self):
        """Run D2D housekeeping tasks, only when D2D is enabled."""
        if not self.d2d_enable:
            return
        self.perform_house_keeping_tasks()

    def get_src_repo_download_url(self):
        """
        Get the source repository url from Cargo.toml and determine its
        download url.
        """
        self.src_download_url = None
        if not self.cargo_toml_path:
            return

        repository_url = rust.get_repository_value_from_cargo_toml(self.cargo_toml_path)
        self.src_download_url, warning = source_repo.get_src_repo_download_url(
            repository_url=repository_url,
            version=self.purl.version,
        )
        if warning:
            self.project.add_warning(description=warning)

    def download_src_repo(self):
        """Download the source from the source repo."""
        self.src_repo_path = None
        if not self.src_download_url:
            return

        self.src_repo_path = source_repo.download_src_repo(self.src_download_url)
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
        self.mismatches = {}
        if not self.src_repo_path:
            return

        from_resources = (
            self.project.codebaseresources.files().from_codebase().has_value("sha1")
        )
        input_files = utils.get_all_files_from_resources(
            from_resources, base_path_prefix="from/"
        )

        with tempfile.TemporaryDirectory() as source_repo_path:
            self.extract_archive(self.src_repo_path, source_repo_path)

            # If the crate lives in a subdirectory of the repository
            # (monorepo layout), narrow the comparison to that subdirectory.
            crate_subdir = rust.find_crate_subdirectory(
                source_repo_path=source_repo_path,
                purl=self.purl,
            )
            if crate_subdir:
                source_repo_path = crate_subdir

            self.matched_count, self.mismatches = utils.compare_directories(
                input_files, source_repo_path
            )

    def update_comparison_summary(self):
        """Update the comparison summary in the discovered package."""
        if not self.src_repo_path:
            return

        source_repo.update_comparison_summary(
            project=self.project,
            purl=self.purl,
            devel_codebase_dir=self.devel_codebase_dir,
            src_repo_url=self.src_download_url,
            package_name=self.purl.name,
            package_version=self.purl.version,
            matched_count=self.matched_count,
            mismatches=self.mismatches,
        )

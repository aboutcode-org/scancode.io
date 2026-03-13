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

# from scanpipe.pipes.maven import update_package_license_from_resource_if_missing


class ScanRustPackage(ScanSinglePackage, DeployToDevelop, ScanCodebase):
    """
    Download the crate’s source, build it, and run a d2d comparison between
    the compiled binary and the source crate to detect any discrepancies.

    Identify the upstream source repository and verify that it matches the
    contents of the source crate.

    Scan the source crate and confirm that the detected license aligns with
    the license declared in Cargo.toml.

    Compare the crate’s source code against all other crates (MatchCode),
    excluding itself, to detect any borrowed code from third‑party crates.
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_input,
            cls.get_package_input,
            cls.collect_input_information,
            cls.extract_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.build_crates,
            cls.run_scan,
            cls.load_inventory_from_toolkit_scan,
            cls.add_from_to_tag,
            cls.validate_package_license_integrity,
            cls.identify_built_sources,
            cls.flag_mapped_status,
            cls.make_summary_from_scan_results,
        )

    def get_input(self):
        """Get the input file for the Rust package scan pipeline."""
        from_files = list(self.project.inputs("from*"))
        from_files.extend([input.path for input in self.project.inputsources.all()])
        self.from_files = from_files
        self.to_files = list()

    def build_crates(self):
        """
        Build the Rust crate using Cargo and put the built files under the
        "to" directory.
        """
        # Find the Cargo.toml file in the codebase directory
        codebase_dir = Path(self.project.codebase_path)
        cargo_toml_path = None
        for path in codebase_dir.rglob("Cargo.toml"):
            cargo_toml_path = path
            break
        if cargo_toml_path:
            rust.build_crates(cargo_toml_path, self.project.codebase_path / "to/")

    def add_from_to_tag(self):
        """Update 'from' or 'to' tag to resources based on their path."""
        d2d.update_from_to_tag(self.project)

    def validate_package_license_integrity(self):
        """
        Validate the correctness of the package license compare with the
        detected license from the codebase.
        """
        utils.validate_package_license_integrity(self.project)

    def identify_built_sources(self):
        """Identify the built sources from the '.d' file in the "to" directory."""
        d2d.map_rust_paths(self.project)

    def flag_mapped_status(self):
        """Flag the from codebase resources that were mapped."""
        flag.flag_mapped_resources(self.project)

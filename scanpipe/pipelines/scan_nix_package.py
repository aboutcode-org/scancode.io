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
from scanpipe.pipes import d2d
from scanpipe.pipes import nix


class ScanNixPackage(DeployToDevelop):
    """
    Scan a nixpkgs package and compare its binary with its source.

    This pipeline takes a single nixpkgs PURL as input, for example:
    ``pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux``.
    The ``system`` qualifier is required. The nixpkgs commit is looked up from
    the version, or can be provided with the ``commit`` qualifier.

    The source is fetched with the nixpkgs patches applied, and the binary is
    downloaded from the Nix binary cache. A deployment to development analysis
    runs between them, and the whole source is scanned to compare the detected
    licenses with the license declared in nixpkgs.

    The ELF binaries mapping is always enabled, as nixpkgs binaries are ELF
    files on Linux. It relies on the DWARF debug paths, available only for the
    packages that provide a ``debug`` output.

    The source is evaluated for the Linux system running ScanCode.io: for a
    macOS ``system``, the source does not include the macOS specific patches.

    Add the ``match_to_matchcode`` addon pipeline to the project to match the
    source with MatchCode.io and find the code borrowed from other packages.

    This pipeline requires the ``nix`` command, available in the full
    ScanCode.io image.
    """

    download_inputs = False

    def __init__(self, run_instance):
        super().__init__(run_instance)
        if "Elf" not in self.selected_groups:
            self.selected_groups = [*self.selected_groups, "Elf"]

    @classmethod
    def get_availability(cls):
        if missing_commands := nix.get_missing_commands():
            return (
                f"Missing commands: {', '.join(missing_commands)}. "
                "Use the full ScanCode.io image."
            )

    @classmethod
    def steps(cls):
        excluded_steps = (
            cls.get_inputs,
            cls.extract_inputs_to_codebase_directory,
            cls.create_local_files_packages,
        )
        d2d_steps = tuple(
            step for step in super().steps() if step not in excluded_steps
        )
        return (
            cls.get_nix_package,
            cls.get_nix_package_metadata,
            cls.fetch_nix_source,
            cls.fetch_nix_binary,
            *d2d_steps,
            cls.create_nix_package,
            cls.check_nix_package_license,
            cls.collect_nix_garbage,
        )

    def get_nix_package(self):
        """Validate the input Nix PURL and get its nixpkgs commit."""
        self.purl = nix.get_nix_purl(self.project)
        self.commit = nix.get_nixpkgs_commit(self.purl)

    def get_nix_package_metadata(self):
        """Get the package metadata and binary store paths from nixpkgs."""
        self.metadata = nix.get_package_metadata(
            attribute_path=self.purl.name,
            commit=self.commit,
            system=self.purl.qualifiers["system"],
        )

        version = self.metadata["version"]
        if self.purl.version and self.purl.version != version:
            self.project.add_warning(
                description=(
                    f"The PURL version {self.purl.version} differs from the "
                    f"nixpkgs version {version} at commit {self.commit}."
                ),
                model=self.pipeline_name,
            )

    def fetch_nix_source(self):
        """Fetch the source to ``from/``, with the nixpkgs patches applied."""
        patch_error = nix.fetch_source(
            attribute_path=self.purl.name,
            commit=self.commit,
            destination=self.project.codebase_path / d2d.FROM,
        )
        if patch_error:
            self.project.add_warning(
                description=(
                    "The nixpkgs patches cannot be applied, the upstream source "
                    "is used instead."
                ),
                model=self.pipeline_name,
                details={"error": patch_error},
            )

    def fetch_nix_binary(self):
        """Download the package outputs from the Nix binary cache to ``to/``."""
        selected_output = self.purl.qualifiers.get("output")
        missing_outputs = []
        for output, store_path in self.metadata["outputs"].items():
            if selected_output and output != selected_output:
                continue

            is_fetched = nix.fetch_binary(
                store_path=store_path,
                destination=self.project.codebase_path / d2d.TO / output,
                download_directory=self.project.tmp_path,
            )
            if not is_fetched:
                missing_outputs.append(output)

        if missing_outputs:
            self.project.add_warning(
                description=(
                    f"Outputs not available in the Nix binary cache: "
                    f"{', '.join(missing_outputs)}"
                ),
                model=self.pipeline_name,
            )

    def scan_mapped_from_for_files(self):
        """
        Scan the ``from/`` files for copyrights, licenses, emails, and urls,
        including the files not deployed in the binary.
        """
        super().scan_mapped_from_for_files()
        nix.scan_undeployed_from_files(self.project, progress_logger=self.log)

    def create_nix_package(self):
        """Create the Nix package and assign the codebase resources to it."""
        self.package = nix.create_nix_package(self.project, self.purl, self.metadata)
        nix.add_resources_to_package(
            self.package, self.project.codebaseresources.files()
        )

    def check_nix_package_license(self):
        """Store the licenses detected in the source but not declared in nixpkgs."""
        declared_license = self.package.declared_license_expression
        if not declared_license:
            self.project.add_warning(
                description="No declared license in nixpkgs, license check skipped.",
                model=self.pipeline_name,
            )
            return

        uncovered_licenses = nix.get_uncovered_license_keys(
            self.project, declared_license
        )
        self.package.update_extra_data({"uncovered_licenses": uncovered_licenses})

    def collect_nix_garbage(self):
        """Delete the Nix store paths fetched and built for this scan."""
        nix.collect_garbage()

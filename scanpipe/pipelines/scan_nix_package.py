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
from scanpipe.pipes import flag
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

    The package outputs holding only headers and documentation, such as ``dev``,
    ``doc``, or ``man``, are not downloaded. A single output can be selected with
    the ``output`` qualifier.

    When the source cannot be fetched, for a package without a ``src`` attribute,
    the binary is analyzed alone and the license check is skipped.

    The binaries mapping is always enabled: ELF for a Linux ``system``, and
    Mach-O for a macOS ``system``. The ELF mapping relies on the DWARF debug
    paths, available only for the packages that provide a ``debug`` output.

    The source is evaluated for the Linux system running ScanCode.io: for a
    macOS ``system``, the source does not include the macOS specific patches.

    Add the ``match_to_matchcode`` addon pipeline to the project to match the
    source with MatchCode.io and find the code borrowed from other packages.

    The nixpkgs commit is checked with the GitHub API, limited to 60 requests
    per hour without a token. Provide a token with the
    ``SCANCODEIO_FETCH_HEADERS`` setting, for example:
    ``api.github.com=Authorization=token <YOUR_TOKEN>``.

    This pipeline requires the ``nix`` command, available in the full
    ScanCode.io image.
    """

    download_inputs = False

    def __init__(self, run_instance):
        super().__init__(run_instance)
        binary_group = nix.get_binary_group(self.project)
        if binary_group not in self.selected_groups:
            self.selected_groups = [*self.selected_groups, binary_group]

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
        self.log(f"nixpkgs commit: {self.commit}")

    def get_nix_package_metadata(self):
        """Get the package metadata and binary store paths from nixpkgs."""
        self.metadata = nix.get_package_metadata(
            attribute_path=self.purl.name,
            commit=self.commit,
            system=self.purl.qualifiers["system"],
            cache_directory=self.project.tmp_path,
        )
        self.selected_outputs = nix.get_selected_outputs(
            outputs=self.metadata["outputs"],
            selected_output=self.purl.qualifiers.get("output"),
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
        try:
            patch_error = nix.fetch_source(
                attribute_path=self.purl.name,
                commit=self.commit,
                destination=self.project.codebase_path / d2d.FROM,
                cache_directory=self.project.tmp_path,
            )
        except nix.NixCommandError as error:
            self.project.add_warning(
                description=(
                    "The source cannot be fetched, the binary is analyzed alone "
                    "and the license check is skipped."
                ),
                model=self.pipeline_name,
                details={"error": str(error)},
            )
            return

        if patch_error:
            self.project.add_warning(
                description=(
                    "The source with the nixpkgs patches cannot be built, the "
                    "upstream source is used instead."
                ),
                model=self.pipeline_name,
                details={"error": patch_error},
            )

    def fetch_nix_binary(self):
        """Download the package outputs from the Nix binary cache to ``to/``."""
        missing_outputs = []
        for output, store_path in self.selected_outputs.items():
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
        # The license check needs the whole source, including the legal files
        # that are usually not deployed.
        d2d.scan_files_keeping_status(
            project=self.project,
            resource_qs=self.project.codebaseresources.from_codebase(),
            status=flag.NOT_DEPLOYED,
            logger=self.log,
        )

    def create_nix_package(self):
        """Create the Nix package and assign the codebase resources to it."""
        self.package = nix.create_nix_package(
            self.project, self.purl, self.metadata, self.commit
        )
        nix.add_resources_to_package(
            self.package, self.project.codebaseresources.files()
        )

    def check_nix_package_license(self):
        """Store the licenses detected in the source but not declared in nixpkgs."""
        has_source = self.project.codebaseresources.from_codebase().files().exists()
        if not has_source:
            return

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
        """Delete the Nix store paths not in use, such as the ones of this scan."""
        try:
            nix.collect_garbage()
        except nix.NixCommandError as error:
            self.project.add_warning(
                description="The Nix store garbage collection failed.",
                model=self.pipeline_name,
                details={"error": str(error)},
            )

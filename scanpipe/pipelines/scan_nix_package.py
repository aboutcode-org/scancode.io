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
    Scan a nixpkgs package and check its binary and license against its source.

    Use this pipeline to review a package of nixpkgs, the Nix packages collection.
    It maps the binary distributed by Nix to the source it is built from, and
    checks that the license declared in nixpkgs covers the licenses found in the
    source.

    Provide a single nixpkgs Package URL as input, with the target ``system``, for
    example: ``pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux``.
    Add a ``commit`` qualifier to scan the package at a specific nixpkgs commit,
    or an ``output`` qualifier to scan a single package output, such as ``man``.

    The Nix package is created with the license declared in nixpkgs, its origin
    (download URL, Git repository, and nixpkgs recipe), and the licenses found in
    the source but not declared in nixpkgs.

    Add the ``match_to_matchcode`` addon pipeline to the project to find the code
    borrowed from other packages.
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
        """Get the package metadata and binary outputs from nixpkgs."""
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
        nix.add_metadata_warnings(self.project, self.purl, self.commit, self.metadata)

    def fetch_nix_source(self):
        """Fetch the source to ``from/``, with the nixpkgs patches applied."""
        nix.fetch_codebase_source(self.project, self.purl.name, self.commit)

    def fetch_nix_binary(self):
        """Download the package outputs from the Nix binary cache to ``to/``."""
        nix.fetch_codebase_binaries(self.project, self.selected_outputs)

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
        nix.check_package_license(self.project, self.package)

    def collect_nix_garbage(self):
        """Delete the unused Nix files, such as the ones downloaded for this scan."""
        nix.collect_garbage(self.project)

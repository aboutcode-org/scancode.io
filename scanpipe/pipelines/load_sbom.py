# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes import resolve
from scanpipe.pipes import update_or_create_package


class LoadSBOM(ScanCodebase):
    """
    Inspect a codebase for SBOMs and gets all associated packages.

    Supported BOMs:
    - SPDX document
    - CycloneDX BOM
    - AboutCode ABOUT file
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.get_sbom_inputs,
            cls.get_packages_from_sboms,
        )

    def get_sbom_inputs(self):
        """Locate all the SBOMs from the project's input/ directory."""
        self.manifest_resources = resolve.get_manifest_resources(self.project)

    def get_packages_from_sboms(self):
        """Get packages data from manifest files."""
        self.resolved_packages = []

        if not self.manifest_resources.exists():
            self.project.add_warning(
                description="No SBOMs found for resolving packages",
                model="get_packages_from_sboms",
            )
            return

        for resource in self.manifest_resources:
            if packages := resolve.resolve_packages(
                input_location=resource.location,
                package_registry=resolve.sbom_registry,
            ):
                for package_data in packages:
                    package_data = resolve.set_license_expression(package_data)
                    update_or_create_package(self.project, package_data)
            else:
                self.project.add_error(
                    description="No packages could be resolved for SBOM",
                    model="get_packages_from_sboms",
                    details={"path": resource.path},
                )

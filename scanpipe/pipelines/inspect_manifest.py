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

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import resolve
from scanpipe.pipes import update_or_create_package


class InspectManifest(Pipeline):
    """
    Inspect one or more manifest files and resolve its packages.

    Supports:
    - PyPI "requirements.txt" files
    - SPDX document as JSON ".spdx.json" files
    - CycloneDX BOM as JSON ".bom.json" and ".cdx.json" files
    - AboutCode ".ABOUT" files
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_manifest_inputs,
            cls.create_packages_from_manifest,
        )

    def get_manifest_inputs(self):
        """Locate all the manifest files from the project's input/ directory."""
        self.input_locations = [
            str(input.absolute()) for input in self.project.inputs()
        ]

    def create_packages_from_manifest(self):
        """Resolve manifest files into packages."""
        for input_location in self.input_locations:
            default_package_type = resolve.get_default_package_type(input_location)
            if not default_package_type:
                raise Exception(f"No package type found for {input_location}")

            resolver = resolve.resolver_registry.get(default_package_type)
            if not resolver:
                raise Exception(
                    f'No resolver for package type "{default_package_type}" for '
                    f"{input_location}"
                )

            self.log(f"`{default_package_type}` input detected for {input_location}")
            resolved_packages = resolver(input_location=input_location)
            if not resolved_packages:
                raise Exception(f"No packages could be resolved for {input_location}")

            for package_data in resolved_packages:
                package_data = resolve.set_license_expression(package_data)
                update_or_create_package(self.project, package_data)

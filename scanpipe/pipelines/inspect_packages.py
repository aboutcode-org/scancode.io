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


class InspectPackages(ScanCodebase):
    """
    Inspect a codebase manifest files and resolve their associated packages.

    Supports resolved packages for:
    - Python: using nexB/python-inspector, supports requirements.txt and
      setup.py manifests as input

    Supports:
    - BOM: SPDX document, CycloneDX BOM, AboutCode ABOUT file
    - Python: requirements.txt, setup.py, setup.cfg, Pipfile.lock
    - JavaScript: yarn.lock lockfile, npm package-lock.json lockfile
    - Java: Java JAR MANIFEST.MF, Gradle build script
    - Ruby: RubyGems gemspec manifest, RubyGems Bundler Gemfile.lock
    - Rust: Rust Cargo.lock dependencies lockfile, Rust Cargo.toml package manifest
    - PHP: PHP composer lockfile, PHP composer manifest
    - NuGet: nuspec package manifest
    - Dart: pubspec manifest, pubspec lockfile
    - OS: FreeBSD compact package manifest, Debian installed packages database

    Full list available at https://scancode-toolkit.readthedocs.io/en/
    doc-update-licenses/reference/available_package_parsers.html
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_ignored_resources,
            cls.get_manifest_inputs,
            cls.get_packages_from_manifest,
            cls.create_resolved_packages,
        )

    def get_manifest_inputs(self):
        """Locate all the manifest files from the project's input/ directory."""
        self.manifest_resources = resolve.get_manifest_resources(self.project)

    def get_packages_from_manifest(self):
        """Get packages data from manifest files."""
        self.resolved_packages = []

        if not self.manifest_resources.exists():
            self.project.add_warning(
                description="No manifests found for resolving packages",
                model="get_packages_from_manifest",
            )
            return

        for resource in self.manifest_resources:
            if packages := resolve.resolve_packages(resource.location):
                self.resolved_packages.extend(packages)
            else:
                self.project.add_error(
                    description="No packages could be resolved for",
                    model="get_packages_from_manifest",
                    details={"path": resource.path},
                )

    def create_resolved_packages(self):
        """Create the resolved packages and their dependencies in the database."""
        for package_data in self.resolved_packages:
            package_data = resolve.set_license_expression(package_data)
            dependencies = package_data.pop("dependencies", [])
            update_or_create_package(self.project, package_data)

            for dependency_data in dependencies:
                resolved_package = dependency_data.get("resolved_package")
                if resolved_package:
                    resolved_package.pop("dependencies", [])
                    update_or_create_package(self.project, resolved_package)

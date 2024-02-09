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
from scanpipe.pipes import scancode


class InspectPackages(ScanCodebase):
    """
    Inspect a codebase for manifest files and gets all associated packages.

    Supports:
    - Python: requirements.txt, setup.py, setup.cfg, Pipfile.lock
    - JavaScript: yarn.lock lockfile, npm package-lock.json lockfile
    - Java: Java JAR MANIFEST.MF, Gradle build script
    - Ruby: RubyGems gemspec manifest, RubyGems Bundler Gemfile.lock
    - Rust: Rust Cargo.lock dependencies lockfile, Rust Cargo.toml package manifest
    - PHP: PHP composer lockfile, PHP composer manifest
    - NuGet: nuspec package manifest
    - Dart: pubspec manifest, pubspec lockfile
    - OS: FreeBSD compact package manifest, Debian installed packages database

    Full list available at https://scancode-toolkit.readthedocs.io/en/stable/
    reference/available_package_parsers.html
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
        )

    def scan_for_application_packages(self):
        """
        Scan resources for package information to add DiscoveredPackage
        and DiscoveredDependency objects from detected package data.
        """
        # `assemble` is set to False because here in this pipeline we
        # only detect package_data in resources without creating
        # Package/Dependency instances, to get all the purls from a codebase.
        scancode.scan_for_application_packages(self.project, assemble=False)
        scancode.process_package_data(self.project)

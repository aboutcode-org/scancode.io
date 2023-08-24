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
from scanpipe.pipes import purldb


class PopulatePurlDB(Pipeline):
    """Populate PurlDB with project discovered packages and dependencies."""

    @classmethod
    def steps(cls):
        return (
            cls.populate_purldb_with_discovered_packages,
            cls.populate_purldb_with_discovered_dependencies,
        )

    def populate_purldb_with_discovered_packages(self):
        """Add DiscoveredPackage to PurlDB."""
        self.feed_purldb(
            packages=self.project.discoveredpackages.all(),
            package_type="DiscoveredPackage",
        )

    def populate_purldb_with_discovered_dependencies(self):
        """Add DiscoveredDependency to PurlDB."""
        self.feed_purldb(
            packages=self.project.discovereddependencies.all(),
            package_type="DiscoveredDependency",
        )

    def feed_purldb(self, packages, package_type):
        """Feed PurlDB with list of PURLs for indexing."""
        if not purldb.is_available():
            raise Exception("PurlDB is not available.")

        package_urls = [package.purl for package in packages]
        self.log(f"Populating PurlDB with {len(package_urls):,d} {package_type}")

        response = purldb.submit_purls(purls=package_urls)
        queued_packages_count = response.get("queued_packages_count", 0)
        unqueued_packages_count = response.get("unqueued_packages_count", 0)
        unsupported_packages_count = response.get("unsupported_packages_count", 0)

        if queued_packages_count > 0:
            self.log(
                f"Successfully queued {queued_packages_count:,d} "
                f"PURLs for indexing in PurlDB"
            )

        if unqueued_packages_count > 0:
            self.log(
                f"{unqueued_packages_count:,d} PURLs were already "
                f"present in PurlDB index queue"
            )

        if unsupported_packages_count > 0:
            self.log(
                f"Couldn't index {unsupported_packages_count:,d} unsupported PURLs"
            )

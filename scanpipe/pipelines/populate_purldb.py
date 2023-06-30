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
from scanpipe.pipes.purldb import feed_purldb


class PopulatePurlDB(Pipeline):
    """Populate PurlDB with project packages."""

    @classmethod
    def steps(cls):
        return (
            cls.populate_purldb_discoveredpackage,
            cls.populate_purldb_discovereddependency,
        )

    def populate_purldb_discoveredpackage(self):
        """Add DiscoveredPackage to PurlDB."""
        packages = self.project.discoveredpackages.all().distinct()

        self.log(f"Populating PurlDB with {len(packages):,d} DiscoveredPackage")
        feed_purldb(packages=packages)

    def populate_purldb_discovereddependency(self):
        """Add DiscoveredDependency to PurlDB."""
        packages = self.project.discovereddependencies.all().distinct()

        self.log(f"Populating PurlDB with {len(packages):,d} DiscoveredDependency")
        feed_purldb(packages=packages)

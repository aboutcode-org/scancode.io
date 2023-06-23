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

from django.db.models import Q

from scanpipe.models import posix_regex_to_django_regex_lookup
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import purldb


class PopulatePurlDB(Pipeline):
    """
    Populate PurlDB with project packages.

    Ignore PURLs where namespace matches the pattern supplied
    under ``ignored_namespace`` in scancode-config.yml.
    """

    @classmethod
    def steps(cls):
        return (
            cls.populate_purldb_discoveredpackage,
            cls.populate_purldb_discovereddependency,
        )

    @property
    def ignored_namespaces(self):
        return self.env.get("ignored_namespaces", [])

    def populate_purldb_discoveredpackage(self):
        """Add DiscoveredPackage to PurlDB."""
        feed_purldb(
            package_object=self.project.discoveredpackages,
            ignored_namespaces=self.ignored_namespaces,
            logger=self.log,
        )

    def populate_purldb_discovereddependency(self):
        """Add DiscoveredDependency to PurlDB."""
        feed_purldb(
            package_object=self.project.discovereddependencies,
            ignored_namespaces=self.ignored_namespaces,
            logger=self.log,
        )


def feed_purldb(package_object, ignored_namespaces, logger):
    if not purldb.is_available():
        raise Exception("PurlDB is not configured.")

    combined_pattern = Q()
    for pattern in ignored_namespaces:
        combined_pattern |= Q(
            namespace__regex=posix_regex_to_django_regex_lookup(pattern)
        )

    packages = package_object.exclude(combined_pattern)

    logger(f"Populating PurlDB with {len(packages):,d} PURLs")
    for purl in list(set(packages)):
        purldb.index_package(purl)

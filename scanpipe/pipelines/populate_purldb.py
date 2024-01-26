#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import purldb
from scanpipe.pipes import scancode


class PopulatePurlDB(Pipeline):
    """Populate PurlDB with discovered project packages and their dependencies."""

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.populate_purldb_with_discovered_packages,
            cls.populate_purldb_with_discovered_dependencies,
            cls.populate_purldb_with_detected_purls,
        )

    def populate_purldb_with_discovered_packages(self):
        """Add DiscoveredPackage to PurlDB."""
        purldb.populate_purldb_with_discovered_packages(
            project=self.project, logger=self.log
        )

    def populate_purldb_with_discovered_dependencies(self):
        """Add DiscoveredDependency to PurlDB."""
        purldb.populate_purldb_with_discovered_dependencies(
            project=self.project, logger=self.log
        )

    def populate_purldb_with_detected_purls(self):
        """Add DiscoveredPackage to PurlDB."""
        no_packages_and_no_dependencies = all(
            [
                not self.project.discoveredpackages.exists(),
                not self.project.discovereddependencies.exists(),
            ]
        )
        # Even when there are no packages/dependencies, resource level
        # package data could be detected (i.e. when we detect packages,
        # but skip the assembly step that creates
        # package/dependency instances)
        if no_packages_and_no_dependencies:
            packages = scancode.get_packages_with_purl_from_resources(self.project)
            purls = [{"purl": package.purl} for package in packages]

            self.log(f"Populating PurlDB with {len(purls):,d} " "detected PURLs"),
            purldb.feed_purldb(
                packages=purls,
                chunk_size=100,
                logger=self.log,
            )

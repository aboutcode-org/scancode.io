#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import vulnerablecode


class FindVulnerabilities(Pipeline):
    """
    Find vulnerabilities for packages and dependencies in the VulnerableCode database.

    Vulnerability data is stored on each package and dependency instance.
    """

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.check_vulnerablecode_service_availability,
            cls.lookup_packages_vulnerabilities,
            cls.lookup_dependencies_vulnerabilities,
        )

    def check_vulnerablecode_service_availability(self):
        """Check if the VulnerableCode service if configured and available."""
        if not vulnerablecode.is_configured():
            raise Exception("VulnerableCode is not configured.")

        if not vulnerablecode.is_available():
            raise Exception("VulnerableCode is not available.")

    def lookup_packages_vulnerabilities(self):
        """Check for vulnerabilities for each of the project's discovered package."""
        packages = self.project.discoveredpackages.all()
        vulnerablecode.fetch_vulnerabilities(packages, logger=self.log)

    def lookup_dependencies_vulnerabilities(self):
        """Check for vulnerabilities for each of the project's discovered dependency."""
        dependencies = self.project.discovereddependencies.filter(is_resolved=True)
        vulnerablecode.fetch_vulnerabilities(dependencies, logger=self.log)

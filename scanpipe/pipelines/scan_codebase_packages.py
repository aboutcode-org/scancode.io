#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes import scancode


class ScanCodebasePackages(ScanCodebase):
    """
    Scan a codebase for PURLs without assembling full packages/dependencies.

    This Pipeline is intended for gathering PURL information from a
    codebase without the overhead of full package assembly.
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
        """Scan unknown resources for packages information."""
        # `assemble` is set to False because here in this pipeline we
        # only detect package_data in resources without creating
        # Package/Dependency instances, to get all the purls from a codebase.
        scancode.scan_for_application_packages(self.project, assemble=False)

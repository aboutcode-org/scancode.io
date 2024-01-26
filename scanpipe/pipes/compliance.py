#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.pipes import flag
from scanpipe.pipes import scancode

"""
A common compliance pattern for images is to store known licenses in a /licenses
directory and the corresponding source code archives, for packages that are
redistributable in source form, in a /sourcemirror directory; both at the root of
an image (VM or container image).

Usage example within a Pipeline:

def analyze_licenses_and_sources(self):
    util.flag_compliance_files(self.project)
    util.analyze_compliance_licenses(self.project)
"""


def flag_compliance_files(project):
    """Flag compliance files status for the provided `project`."""
    compliance_dirs = {
        "/licenses": flag.COMPLIANCE_LICENSES,
        "/sourcemirror": flag.COMPLIANCE_SOURCEMIRROR,
    }

    qs = project.codebaseresources.no_status()

    for path, status in compliance_dirs.items():
        qs.filter(rootfs_path__startswith=path).update(status=status)


def analyze_compliance_licenses(project):
    """Scan compliance licenses status for the provided `project`."""
    qs = project.codebaseresources.status(flag.COMPLIANCE_LICENSES)

    for codebase_resource in qs:
        scan_results, scan_errors = scancode.scan_file(codebase_resource.location)
        codebase_resource.set_scan_results(scan_results)

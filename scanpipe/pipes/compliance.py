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

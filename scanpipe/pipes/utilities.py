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

from scanpipe.models import CodebaseResource
from scanpipe.pipes import scan_file


"""
A common compliance pattern for images is to store known licenses in a /licenses
directory and the corresponding source code archives for packages that are
redistributable in source form in a /sourcemirror directory, both at the root of
an image (VM or container image).

Usage example within a Pipeline:

@step
def analyze_licenses_and_sources(self):
    utilities.tag_compliance_files(self.project)
    utilities.analyze_compliance_licenses(self.project)
    utilities.analyze_compliance_sourcemirror_for_packages(self.project)
    self.next(self.tag_uninteresting_codebase_resources)
"""


def tag_compliance_files(project):
    """
    Tag compliance files status for the provided `project`.
    """
    compliance_dirs = {
        "/licenses": "compliance-licenses",
        "/sourcemirror": "compliance-sourcemirror",
    }

    qs = project.codebaseresources.no_status()

    for path, status in compliance_dirs.items():
        qs.filter(rootfs_path__startswith=path).update(status=status)


def analyze_compliance_licenses(project):
    """
    Tag compliance licenses status for the provided `project`.
    """
    qs = CodebaseResource.objects.project(project).status("compliance-licenses")

    for codebase_resource in qs:
        scan_results = scan_file(codebase_resource.location)
        codebase_resource.set_scan_results(scan_results, save=True)


def analyze_compliance_sourcemirror_for_packages(project):
    qs = CodebaseResource.objects.project(project).status("compliance-sourcemirror")

    for codebase_resource in qs:
        # TODO:
        # 1. Extract all archive recursively in the sourcemirror dir
        # -> extractcode not shallow (default)
        # 2. Update inventory
        # -> make_codebase_resource
        # 3. Scan for everything in that:
        # -> scan for package, then set aside (status), then scan_file
        pass

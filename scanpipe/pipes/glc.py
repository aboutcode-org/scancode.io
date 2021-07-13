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


from LicenseClassifier.classifier import LicenseClassifier

from scanpipe.pipes import scancode


def scan_directory(location):
    """
    Run a license and copyright scan on directory at `location`,
    using golicense-classifier.
    """
    classifier = LicenseClassifier()
    result = classifier.scan_directory(location)
    return result


def scan_file_for_license(location):
    """
    Run a license and copyright scan on provided `location`,
    using golicense-classifier.
    """
    classifier = LicenseClassifier()
    result = classifier.scan_file(location)
    return result


def update_codebase_resources(project, scan_data):
    """
    Update CodebaseResource model with scan results from golicense-classifier
    """
    for resource in project.codebaseresources.no_status():
        scan_result = next(
            (result for result in scan_data if result["path"] == resource.location),
            None,
        )
        if scan_result:
            scancode.save_scan_file_results(
                codebase_resource=resource,
                scan_results=scan_result,
                scan_errors=scan_result.get("scan_errors", []),
            )

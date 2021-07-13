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

from scanpipe.pipelines import scan_codebase
from scanpipe.pipes import glc
from scanpipe.pipes import make_codebase_resource
from scanpipe.pipes import rootfs


class LicenseClassifierScan(scan_codebase.ScanCodebase):
    """
    A pipeline to scan a codebase with GoLicense-Classifier for Copyright and License Details
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.run_extractcode,
            cls.collect_and_create_codebase_resources,
            cls.run_license_classifier,
            cls.csv_output,
        )

    def collect_and_create_codebase_resources(self):
        """
        Collect and create all files as CodebaseResource.
        """
        for resource in rootfs.get_resources(str(self.project.codebase_path)):
            make_codebase_resource(
                project=self.project,
                location=resource.location,
            )

    def run_license_classifier(self):
        """
        Scan codebase for license and copyright details
        """
        data = glc.scan_directory(location=self.project.codebase_path)
        scan_data = data.get("files", [])
        glc.update_codebase_resources(self.project, scan_data)

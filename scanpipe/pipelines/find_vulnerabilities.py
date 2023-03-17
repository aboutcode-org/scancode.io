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
from scanpipe.pipes import vulnerablecode


class FindVulnerabilities(Pipeline):
    """
    Find vulnerabilities for discovered packages in the VulnerableCode database.

    Vulnerability data is stored in the extra_data field of each package.
    """

    @classmethod
    def steps(cls):
        return (
            cls.check_vulnerablecode_service_availability,
            cls.lookup_vulnerabilities,
        )

    def check_vulnerablecode_service_availability(self):
        """Check if the VulnerableCode service if configured and available."""
        if not vulnerablecode.is_configured():
            raise Exception("VulnerableCode is not configured.")

        if not vulnerablecode.is_available():
            raise Exception("VulnerableCode is not available.")

    def lookup_vulnerabilities(self):
        """Check for vulnerabilities on each of the project's discovered package."""
        packages = self.project.discoveredpackages.all()

        for package in packages:
            purl = vulnerablecode.get_base_purl(package.package_url)
            vulnerabilities = vulnerablecode.get_vulnerabilities_by_purl(purl)
            package.update_extra_data({"discovered_vulnerabilities": vulnerabilities})

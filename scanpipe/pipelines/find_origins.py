# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import scanoss


class FindOrigins(Pipeline):
    """
    Find the origin of the codebase files using origin detection tools.

    The candidate origin packages reported by each tool are stored as origin
    matches, to be combined and reviewed.

    Supported tools:
    - SCANOSS: the codebase files are fingerprinted locally, then their paths,
      checksums, sizes, and fingerprints are sent to the configured SCANOSS
      server. The file contents are not sent.
    """

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (cls.find_scanoss_origin_matches,)

    @classmethod
    def get_availability(cls):
        if not scanoss.is_configured():
            return "SCANOSS is not configured."

        if not scanoss.get_uvx_location():
            return "The uvx executable required to run SCANOSS is not available."

    def find_scanoss_origin_matches(self):
        """Scan the codebase with SCANOSS and store the reported origin matches."""
        results_location = self.project.get_output_file_path("scanoss", "json")
        scanoss.scan_codebase(self.project.codebase_path, results_location)

        origin_match_count = scanoss.load_scanoss_results_from_file(
            self.project, results_location
        )
        self.log(f"{origin_match_count:,d} SCANOSS origin matches processed.")

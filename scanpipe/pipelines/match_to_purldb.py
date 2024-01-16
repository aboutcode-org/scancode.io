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
from scanpipe.pipes import purldb


class MatchToPurlDB(Pipeline):
    """
    Check CodebaseResources of a Project against PurlDB for Package matches.

    This involves creating a JSON scan of the Project codebase, sending it to
    MatchCode on PurlDB, waiting for match results, creating DiscoveredPackages
    from the match results Package data and associating the proper
    CodebaseResources to those DiscoveredPackges.
    """

    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.check_purldb_service_availability,
            cls.send_project_json_to_matchcode,
            cls.poll_matching_results,
            cls.create_packages_from_match_results,
        )

    def check_purldb_service_availability(self):
        """Check if the PurlDB service if configured and available."""
        if not purldb.is_configured():
            raise Exception("PurlDB is not configured.")

        if not purldb.is_available():
            raise Exception("PurlDB is not available.")

    def send_project_json_to_matchcode(self):
        """Create a JSON scan of the project Codebase and send it to MatchCode."""
        self.run_url = purldb.send_project_json_to_matchcode(self.project)

    def poll_matching_results(self):
        """Wait until the match results are ready by polling the match run status."""
        purldb.poll_until_success(self.run_url)

    def create_packages_from_match_results(self):
        """Create DiscoveredPackages from match results."""
        match_results = purldb.get_match_results(self.run_url)
        purldb.create_packages_from_match_results(self.project, match_results)

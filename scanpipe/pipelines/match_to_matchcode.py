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
from scanpipe.pipes import flag
from scanpipe.pipes import matchcode


class MatchToMatchCode(Pipeline):
    """
    Match the codebase resources of a project against MatchCode.io to identify packages.

    This process involves:

    1. Generating a JSON scan of the project codebase
    2. Transmitting it to MatchCode.io and awaiting match results
    3. Creating discovered packages from the package data obtained
    4. Associating the codebase resources with those discovered packages

    Currently, MatchCode.io can only match for archives, directories, and files
    from Maven and npm Packages.

    This pipeline requires a MatchCode.io instance to be configured and available.
    There is currently no public instance of MatchCode.io. Reach out to nexB, Inc.
    for other arrangements.
    """

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?status=" + flag.MATCHED_TO_PURLDB_PACKAGE

    @classmethod
    def steps(cls):
        return (
            cls.check_matchcode_service_availability,
            cls.send_project_json_to_matchcode,
            cls.poll_matching_results,
            cls.create_packages_from_match_results,
        )

    def check_matchcode_service_availability(self):
        """Check if the MatchCode.io service if configured and available."""
        if not matchcode.is_configured():
            msg = (
                "MatchCode.io is not configured. Set the MatchCode.io "
                "related settings to a MatchCode.io instance or reach out "
                "to the maintainers for other arrangements."
            )
            raise matchcode.MatchCodeIOException(msg)

        if not matchcode.is_available():
            raise matchcode.MatchCodeIOException("MatchCode.io is not available.")

    def send_project_json_to_matchcode(self):
        """Create a JSON scan of the project Codebase and send it to MatchCode.io."""
        self.match_url, self.run_url = matchcode.send_project_json_to_matchcode(
            self.project
        )

    def poll_matching_results(self):
        """Wait until the match results are ready by polling the match run status."""
        matchcode.poll_run_url_status(self.run_url)

    def create_packages_from_match_results(self):
        """Create DiscoveredPackages from match results."""
        match_results = matchcode.get_match_results(self.match_url)
        matchcode.create_packages_from_match_results(self.project, match_results)

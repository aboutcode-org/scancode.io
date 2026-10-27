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

import subprocess

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import matchcode
from scanpipe.pipes import origin
from scanpipe.pipes import scanoss


class FindOrigins(Pipeline):
    """
    Find the origin of the codebase files using origin detection tools.

    The candidate origin packages reported by each configured tool are stored as
    origin matches, then combined to determine the origin of each matched file and
    directory. A tool that is not configured is skipped.

    Supported tools:
    - MatchCode.io: the codebase scan, including file and directory
      fingerprints, is sent to the configured MatchCode.io server.
    - SCANOSS: the codebase files are fingerprinted locally, then their paths,
      checksums, sizes, and fingerprints are sent to the configured SCANOSS
      server. The file contents are not sent.
    """

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.find_matchcode_origin_matches,
            cls.find_scanoss_origin_matches,
            cls.determine_origins,
        )

    @classmethod
    def get_availability(cls):
        if not matchcode.is_configured() and not scanoss.is_configured():
            return "No origin detection tool is configured: MatchCode.io or SCANOSS."

    def find_matchcode_origin_matches(self):
        """Match the codebase with MatchCode.io and store the origin matches."""
        if not matchcode.is_configured():
            self.log("MatchCode.io is not configured, skipping.")
            return

        # A tool failure is recorded and does not prevent running the other tools.
        with self.save_errors(matchcode.MatchCodeIOException):
            match_results = matchcode.match_codebase(self.project)
            matchcode.save_match_results(self.project, match_results)

            origin_match_count = matchcode.load_matchcode_results(
                self.project, match_results
            )
            self.log(f"{origin_match_count:,d} MatchCode.io origin matches processed.")

    def find_scanoss_origin_matches(self):
        """Scan the codebase with SCANOSS and store the reported origin matches."""
        if not scanoss.is_configured():
            self.log("SCANOSS is not configured, skipping.")
            return

        if not scanoss.get_uvx_location():
            message = "The uvx executable required by SCANOSS is missing, skipping."
            self.log(message)
            self.project.add_warning(
                description=message, model="find_scanoss_origin_matches"
            )
            return

        results_location = self.project.get_output_file_path("scanoss", "json")
        # A missing or invalid results file is recorded as a SCANOSS failure.
        with self.save_errors(subprocess.SubprocessError, OSError, ValueError):
            scanoss.scan_codebase(self.project.codebase_path, results_location)

            origin_match_count = scanoss.load_scanoss_results(
                self.project, results_location
            )
            self.log(f"{origin_match_count:,d} SCANOSS origin matches processed.")

    def determine_origins(self):
        """
        Determine the origin of each matched file and directory from the origin
        matches of all the tools. An origin is confirmed automatically when two
        tools report the same package, with at least one exact match. Otherwise,
        the origin needs a review. The origins confirmed by a user are kept.
        """
        determination_count = origin.determine_origins(self.project)
        self.log(f"{determination_count:,d} origin determinations created.")

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
from scanpipe.pipes import reachability
from scanpipe.pipes.symbols import TS_QUERIES


class SymbolReachability(Pipeline):
    """
    Determine the reachability of vulnerabilities identified in the project.

    Note: You must run `find_vulnerabilities` pipeline before running this pipeline.

    For every patch the git repository is cloned and extract the vulnerable and fixed
    symbols from the patch commit. These symbols are then matched against
    the project's codebase resources to determine if the vulnerable code
    is actually present and reachable.

    The analysis checks if vulnerable symbols are defined, imported, called,
    or exactly match a code within the project files. The results, including
    tool_details and a reachability status (yes, unknown, or no), are stored
    in the `extra_data` of the matching resources under the `symbols_reachability` key.

    Finally, a summary report is generated for each vulnerability
    advisory and saved as a JSON output file.
    """

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=symbol_reachability"

    @classmethod
    def steps(cls):
        return (
            cls.get_vulnerabilities_patches,
            cls.collect_resource_index,
            cls.collect_patch_symbols,
            cls.collect_and_match_resources,
            cls.generate_advisory_reachability_report,
        )

    def get_vulnerabilities_patches(self):
        """Get unique patch for all vulnerabilities."""
        self.patches = reachability.get_vulnerabilities_patches(
            package_vulnerabilities=self.project.package_vulnerabilities,
            dependency_vulnerabilities=self.project.dependency_vulnerabilities,
        )

    def collect_resource_index(self):
        """Collect resources symbols for each resource"""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False, is_archive=False, is_media=False,
            programming_language__in=TS_QUERIES.keys()
        )
        self.resource_indexes = reachability.collect_resource_index(
            candidate_resources=self.candidate_resources
        )

    def collect_patch_symbols(self):
        """Collect patch symbols for all related commits."""
        self.patch_symbols = reachability.collect_patch_symbols(patches=self.patches)

    def collect_and_match_resources(self):
        """Match resource symbols against patch symbols."""
        reachability.match_patches_to_resources(
            patches=self.patches,
            patch_symbols=self.patch_symbols,
            resource_indexes=self.resource_indexes,
            candidate_resources=self.candidate_resources,
        )

    def generate_advisory_reachability_report(self):
        """Generate a reachability report summarizing status by advisory."""
        reachability.generate_advisory_reachability_report(
            project=self.project,
            patches=self.patches,
            candidate_resources=self.candidate_resources,
        )

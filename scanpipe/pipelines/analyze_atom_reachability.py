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

from scanpipe.pipes import atom
from scanpipe.pipes.reachability_tools import ReachabilityPipeline


class AtomReachability(ReachabilityPipeline):
    """
    Determine the reachability of vulnerabilities using the atom tool.

    Note: You must run the ``find_vulnerabilities`` pipeline before running
    this pipeline.

    atom is run twice against the project codebase:

    - ``usages`` writes a usages slice of the code.
    - ``reachables`` writes a reachables slice of the symbols
     that can actually be reached.

    The vulnerable and fixed symbols of each patch are matched against those
    slices:

    - REACHABLE: the symbol has a call site in the code
    - UNKNOWN: the symbol is defined in the code
    - NOT_REACHABLE: the symbol is absent

    Results are stored in the ``extra_data`` of the matching resources under
    the ``symbols_reachability`` key.
    """

    reachability_tool = atom.AtomTool

    @classmethod
    def get_availability(cls):
        return cls.reachability_tool.get_availability()

    def get_candidate_resources(self):
        """Collect candidate resources for this pipeline."""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=list(self.reachability_tool.supported_languages),
        )

    def collect_resource_index(self):
        """Run the atom usages and reachables commands and load both slices."""
        self.resource_indexe_paths = self.reachability_tool.run(
            project=self.project, logger=self.log
        )
        indexes = self.reachability_tool.parsed_output(
            export_output_path=self.resource_indexe_paths, logger=self.log
        )
        self.resource_indexes_usages = indexes.get("usages") or {}
        self.resource_indexes_reachability = indexes.get("reachables") or {}

    def collect_and_match_resources(self):
        """Match patch symbols against the atom slices."""
        if not self.resource_indexes_usages and not self.resource_indexes_reachability:
            self.log("No atom usages or reachables slices available for matching.")
            return

        atom.collect_and_match_resources(
            tool_name=self.reachability_tool.tool_name,
            patches=self.patches,
            patch_symbols=self.patch_symbols,
            usages_slices=self.resource_indexes_usages,
            reachables_slices=self.resource_indexes_reachability,
            candidate_resources=self.candidate_resources,
            logger=self.log,
        )

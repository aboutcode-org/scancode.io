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

from scanpipe.pipelines.analyze_symbols_reachability import SymbolReachability
from scanpipe.pipes import cpg
from scanpipe.pipes.cpg import CPG_NEO4J_EXECUTABLE
from scanpipe.pipes.symbols import TS_QUERIES


class CPGSymbolReachability(SymbolReachability):
    """ """

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=symbols_reachability"

    @classmethod
    def steps(cls):
        return (
            cls.get_vulnerabilities_patches,
            cls.collect_resource_index,
            cls.collect_patch_symbols,
            cls.collect_and_match_resources,
            cls.generate_advisory_reachability_report,
            cls.apply_reachability_to_packages_and_dependencies,
        )

    @classmethod
    def get_availability(cls):
        if not CPG_NEO4J_EXECUTABLE:
            return "CPG is not configured."

    def collect_resource_index(self):
        """Collect resources symbols for each resource"""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=TS_QUERIES.keys(),
        )
        self.resource_indexes = cpg.collect_resource_index(
            project=self.project, logger=self.log
        )

    def collect_and_match_resources(self):
        cpg.match_patches_to_resources(
            patches=self.patches,
            patch_symbols=self.patch_symbols,
            resource_indexes=self.resource_indexes,
            candidate_resources=self.candidate_resources,
            logger=self.log,
        )

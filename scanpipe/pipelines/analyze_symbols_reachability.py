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


class SymbolReachability(Pipeline):
    """
    Patch reachability analysis for given vulnerability patches.

    For every patch we clone the git repository and extract
    the vulnerable and fixed symbols from the patch commit.

    These symbols are then matched against the project's codebase resources to
    determine if the vulnerable code is actually present and reachable.

    The analysis checks if vulnerable symbols are defined, imported, called, or
    exactly match a fingerprint within the project files. The results, including
    evidence and a reachability status (REACHABLE, POTENTIALLY_REACHABLE, or
    NOT_REACHABLE), are stored in the `extra_data` of the matching resources
    under the `symbols_reachability` key.
    """

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=symbol_reachability"

    @classmethod
    def steps(cls):
        return (cls.analyze_symbol_reachability,)

    def analyze_symbol_reachability(self):
        """
        Perform symbol-level reachability analysis for each patch. This step compares
        the AST of patched/vulnerable files against the codebase resources.
        Results are stored directly in the 'extra_data' of each CodebaseResource.
        """
        reachability.analyze_and_store_symbol_reachability_results(
            project=self.project, logger=self.log
        )

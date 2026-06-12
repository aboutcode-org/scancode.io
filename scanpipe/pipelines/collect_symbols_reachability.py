#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import reachability


class SymbolReachability(Pipeline):
    """Patch reachability analysis for given vulnerability patches."""

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=symbol_reachability"

    @classmethod
    def steps(cls):
        return (cls.analyze_and_store_symbol_reachability,)

    def analyze_and_store_symbol_reachability(self):
        """
        Perform symbol-level reachability analysis for each patch. This step compares
        the AST of patched/vulnerable files against the codebase resources.
        Results are stored directly in the 'extra_data' of each CodebaseResource.
        """
        reachability.collect_and_store_symbol_reachability_results(
            project=self.project, logger=self.log
        )

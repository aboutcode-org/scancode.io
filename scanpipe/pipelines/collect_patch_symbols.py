#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import symbols


class CollectPatchSymbols(Pipeline):
    """Collect Patch symbols using (ctags, pygments, tree_sitter)"""

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=patch_symbols"

    @classmethod
    def steps(cls):
        return (cls.collect_and_store_patch_symbols_and_strings,)

    def collect_and_store_patch_symbols_and_strings(self):
        """
        Pipeline(s) that can retrieve vulnerable/fixed symbols, collect local symbols (pur2sym) and match them
        """
        symbol_type = "tree_sitter"
        symbols.collect_and_store_patch_symbols(self.project, symbol_type, self.log)

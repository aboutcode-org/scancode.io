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
from scanpipe.pipes import symbols


class CollectSymbolsCtags(Pipeline):
    """Collect source symbols with Ctags."""

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=source_symbols"

    @classmethod
    def steps(cls):
        return (cls.collect_and_store_resource_symbols,)

    def collect_and_store_resource_symbols(self):
        """
        Collect symbols from codebase files using Ctags and store
        them in the extra data field.
        """
        symbols.collect_and_store_resource_symbols_ctags(self.project, self.log)

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

from source_inspector import symbols_ctags

from scanpipe.pipelines import Pipeline


class CollectSymbols(Pipeline):
    """Collect symbols from codebase files and keep them in extra data field."""

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (cls.collect_and_store_resource_symbols,)

    def collect_and_store_resource_symbols(self):
        """
        Collect symbols from codebase files using Ctags and store
        them in the extra data field.
        """
        if not symbols_ctags.is_ctags_installed():
            self.log(
                "``Universal Ctags`` missing."
                "Install ``Universal Ctags`` to use this pipeline."
            )
            return

        project_files = self.project.codebaseresources.files().filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
        )

        for file in project_files:
            symbols = symbols_ctags.collect_symbols(file.location)
            tags = [symbol["name"] for symbol in symbols if "name" in symbol]
            file.update_extra_data({"symbols": tags})

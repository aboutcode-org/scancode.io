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

from pathlib import Path

from elf_inspector.dwarf import get_dwarf_paths

from scanpipe.pipelines import Pipeline


class InspectElfBinaries(Pipeline):
    """Inspect ELF binaries and collect DWARF paths."""

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (cls.collect_dwarf_source_path_references,)

    def collect_dwarf_source_path_references(self):
        """
        Update ``extra_data`` of ELF files with
        dwarf data extracted from ELF files.
        """
        for elf in self.project.codebaseresources.elfs():
            dwarf_paths = get_dwarf_paths(Path(self.project.codebase_path / elf.path))
            elf.update_extra_data(dwarf_paths)

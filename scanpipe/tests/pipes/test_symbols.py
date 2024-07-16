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

import json
import sys
from pathlib import Path
from unittest import skipIf

from django.test import TestCase

from scanpipe import pipes
from scanpipe.models import Project
from scanpipe.pipes import symbols
from scanpipe.pipes.input import copy_input


@skipIf(sys.platform == "darwin", "Not supported on macOS")
class ScanPipeSymbolsPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_pipes_symbols_collect_and_store_resource_symbols_ctags(self):
        dir = self.project1.codebase_path / "codefile"
        dir.mkdir(parents=True)

        file_location = self.data / "d2d-javascript" / "from" / "main.js"
        copy_input(file_location, dir)

        pipes.collect_and_create_codebase_resources(self.project1)

        symbols.collect_and_store_resource_symbols_ctags(self.project1)

        main_file = self.project1.codebaseresources.files()[0]
        result_extra_data_symbols = main_file.extra_data.get("source_symbols")
        expected_extra_data_symbols = ["generatePassword", "passwordLength", "charSet"]
        self.assertCountEqual(expected_extra_data_symbols, result_extra_data_symbols)

    def test_scanpipe_pipes_collect_and_store_pygments_symbols_and_strings(self):
        dir = self.project1.codebase_path / "codefile"
        dir.mkdir(parents=True)

        file_location = self.data / "source-inspector" / "test3.cpp"
        copy_input(file_location, dir)

        pipes.collect_and_create_codebase_resources(self.project1)

        symbols.collect_and_store_pygments_symbols_and_strings(self.project1)

        main_file = self.project1.codebaseresources.files()[0]

        result_extra_data = main_file.extra_data

        expected_extra_data = (
            self.data / "source-inspector" / "test3.cpp-pygments-expected.json"
        )

        with open(expected_extra_data) as f:
            expected_extra_data = json.load(f)

        self.assertDictEqual(expected_extra_data, result_extra_data)

    def test_scanpipe_pipes_collect_and_store_tree_sitter_symbols_and_strings(self):
        dir = self.project1.codebase_path / "codefile"
        dir.mkdir(parents=True)

        file_location = self.data / "source-inspector" / "test3.cpp"
        copy_input(file_location, dir)

        pipes.collect_and_create_codebase_resources(self.project1)

        symbols.collect_and_store_tree_sitter_symbols_and_strings(self.project1)

        main_file = self.project1.codebaseresources.files()[0]

        result_extra_data = main_file.extra_data

        expected_extra_data = (
            self.data / "source-inspector" / "test3.cpp-tree-sitter-expected.json"
        )

        with open(expected_extra_data) as f:
            expected_extra_data = json.load(f)

        self.assertDictEqual(expected_extra_data, result_extra_data)

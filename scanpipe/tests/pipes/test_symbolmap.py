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
from pathlib import Path

from django.test import TestCase

from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import flag
from scanpipe.pipes import symbolmap


class ScanPipeSymbolmapPipesTest(TestCase):
    maxDiff = None
    data = Path(__file__).parent.parent / "data"

    def get_binary_symbols(self):
        binary_symbol_path = self.data / "d2d-rust/trustier-binary-symbols.json"
        with open(binary_symbol_path) as res:
            binary_symbols_data = json.load(res)

        return binary_symbols_data.get("rust_symbols")

    def test_match_source_symbols_to_binary_for_test_file(self):
        # tree-sitter symbols from https://github.com/devops-kung-fu/trustier/blob/main/tests/cli.rs
        rust_test_file_symbols = [
            "anyhow",
            "Ok",
            "Result",
            "assert_cmd",
            "Command",
            "predicates",
            "prelude",
            "test",
            "dies_no_args",
            "cmd",
            "Command",
            "cargo_bin",
            "cmd",
            "predicate",
            "str",
            "contains",
            "Ok",
        ]
        is_source_matched, _stats = symbolmap.match_source_symbols_to_binary(
            rust_test_file_symbols, self.get_binary_symbols()
        )
        self.assertFalse(is_source_matched)

    def test_match_source_symbols_to_binary_for_main_file(self):
        # tree-sitter symbols from https://github.com/devops-kung-fu/trustier/blob/main/src/main.rs
        rust_main_file_symbols = [
            "Args",
            "Bom",
            "Debug",
            "Duration",
            "FileOrStdin",
            "FromStr",
            "PackageUrl",
            "Parser",
            "Path",
            "TrustyResponse",
            "Vec",
            "about",
            "arg",
            "args",
            "async_std",
            "block_on",
            "body",
            "bold",
            "bom",
            "clap_stdin",
            "colored",
            "command",
            "component",
            "create_dir_all",
            "cyclonedx_bom",
            "derive",
            "error",
            "fetch_purl_bodies",
            "filter_purls",
            "format",
            "from_str",
            "fs",
            "get",
            "header",
            "is_file",
            "main",
            "models",
            "name",
            "new",
            "packageurl",
            "parse",
            "parse_from_json_v1_5",
            "path",
            "process_sbom",
            "purl",
            "serde_json",
            "sleep",
            "str",
            "surf",
            "task",
            "time",
            "url",
            "version",
            "write",
        ]
        is_source_matched, _stats = symbolmap.match_source_symbols_to_binary(
            rust_main_file_symbols, self.get_binary_symbols()
        )
        self.assertTrue(is_source_matched)

    def test_match_source_paths_to_binary(self):
        project1 = Project.objects.create(name="Analysis")
        extra_data = {"source_symbols": ["test_symbol1", "test_symbol2"]}
        CodebaseResource.objects.create(
            project=project1, path="src/main.rs", extra_data=extra_data
        )
        CodebaseResource.objects.create(
            project=project1, path="src/models.rs", extra_data=extra_data
        )
        binary_resource = CodebaseResource.objects.create(
            project=project1, path="binary"
        )
        items = symbolmap.match_source_paths_to_binary(
            to_resource=binary_resource,
            from_resources=CodebaseResource.objects.all().filter(path__endswith=".rs"),
            binary_symbols=["test_symbol1", "test_symbol2"],
            map_type="rust_symbols",
        )
        self.assertFalse(any([True for item in items if isinstance(item, str)]))
        self.assertTrue(
            all(
                [
                    True
                    for _rel_key, relation in items
                    if isinstance(relation, CodebaseRelation)
                ]
            )
        )

    def test_map_resources_with_symbols_source_to_binary(self):
        project1 = Project.objects.create(name="Analysis")
        extra_data = {"source_symbols": ["test_symbol1", "test_symbol2"]}
        CodebaseResource.objects.create(
            project=project1, path="src/main.rs", extra_data=extra_data
        )
        CodebaseResource.objects.create(
            project=project1, path="src/models.rs", extra_data=extra_data
        )
        binary_resource = CodebaseResource.objects.create(
            project=project1, path="binary"
        )
        symbolmap.map_resources_with_symbols(
            to_resource=binary_resource,
            from_resources=CodebaseResource.objects.all().filter(path__endswith=".rs"),
            binary_symbols=["test_symbol1", "test_symbol2"],
            map_type="rust_symbols",
        )
        self.assertNotEqual(binary_resource.status, flag.REQUIRES_REVIEW)
        relations = CodebaseRelation.objects.all()
        self.assertEqual(relations.count(), 2)
        self.assertTrue(
            all(True for relation in relations if relation.map_type == "rust_symbols")
        )
        self.assertTrue(
            all(
                [
                    True
                    for resource in CodebaseResource.objects.all().filter(
                        path__endswith=".rs"
                    )
                    if resource.status == flag.MAPPED_BY_SYMBOL
                ]
            )
        )

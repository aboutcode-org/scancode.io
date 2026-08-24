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

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import skipIf
from unittest.mock import MagicMock
from unittest.mock import PropertyMock
from unittest.mock import patch

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes.reachability import PatchAnalyzer
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import ResourceAnalyzer
from scanpipe.pipes.reachability import ResourcePatchMatcher
from scanpipe.pipes.reachability import classify_reachability
from scanpipe.pipes.symbols import TS_QUERIES
from scanpipe.pipes.symbols import SymbolExtractor


@skipIf(sys.platform == "darwin", "Not supported on macOS")
class SymbolReachabilityPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "reachability"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project1.codebase_path.mkdir(parents=True, exist_ok=True)

    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_end_to_end_symbol_reachability_pipeline(
        self, mock_package_vulnerabilities
    ):
        """
        Global end-to-end test for the symbol reachability pipeline.
        Sets up a local git repository with a vulnerable and fixed commit,
        then runs the full pipeline against a local codebase resource.
        """
        from git import Repo

        vcs_dir = tempfile.mkdtemp(prefix="test-vcs-")
        try:
            repo = Repo.init(vcs_dir)
            with repo.config_writer() as config:
                config.set_value("user", "email", "test@example.com")
                config.set_value("user", "name", "test")

            file_path = "app.py"
            vuln_code = (
                "def process_data(data):\n"
                "    # Vulnerable logic\n"
                "    return eval(data)\n"
            )
            fixed_code = (
                "def process_data(data):\n    # Fixed logic\n    return int(data)\n"
            )

            vuln_file = Path(vcs_dir) / file_path
            vuln_file.write_text(vuln_code)
            repo.index.add([file_path])
            repo.index.commit("Vulnerable commit")

            vuln_file.write_text(fixed_code)
            repo.index.add([file_path])
            fixed_commit = repo.index.commit("Fixed commit")

            resource_file = self.project1.codebase_path / "local_app.py"
            resource_file.write_text(vuln_code)
            collect_and_create_codebase_resources(self.project1)

            resource = self.project1.codebaseresources.get(path="local_app.py")
            resource.programming_language = "Python"
            resource.save()

            repo_url = Path(vcs_dir).as_uri()

            mock_package_vulnerabilities.return_value = [
                {
                    "fixed_in_patches": [
                        {
                            "vcs_url": repo_url,
                            "commit_hash": fixed_commit.hexsha,
                        }
                    ]
                }
            ]

            run = self.project1.add_pipeline("analyze_symbols_reachability")
            pipeline = run.make_pipeline_instance()
            pipeline.execute()

            resource.refresh_from_db()
            results = resource.extra_data.get("symbols_reachability")

            expected_results = [
                {
                    "patch": {
                        "vcs_url": repo_url,
                        "commit_hash": fixed_commit.hexsha,
                    },
                    "is_reachable": ReachabilityStatus.REACHABLE.value,
                    "tool_details": [
                        {
                            "is_exact": True,
                            "is_called": False,
                            "is_defined": True,
                            "is_imported": False,
                            "symbol_name": "process_data",
                            "reachable_from": [],
                        }
                    ],
                    "advisory_uids": [],
                    "fixed_symbols": ["process_data"],
                    "vulnerable_symbols": ["process_data"],
                }
            ]

            self.assertEqual(results, expected_results)
        finally:
            shutil.rmtree(vcs_dir, ignore_errors=True)

    def test_generate_advisory_reachability_report(self):
        """Test the generation of the advisory reachability report"""
        run = self.project1.add_pipeline("analyze_symbols_reachability")
        pipeline = run.make_pipeline_instance()

        pipeline.patches = [
            {"advisory_uids": ["AVID-1"]},
            {"advisory_uids": ["AVID-2"]},
        ]
        pipeline.project.purl = "pkg:pypi/test"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "reachability.json")
            pipeline.project.get_output_file_path = MagicMock(return_value=output_file)

            res1 = MagicMock()
            res1.path = "src/file1.py"
            res1.extra_data = {
                "symbols_reachability": [
                    {
                        "advisory_uids": ["AVID-1", "AVID-2"],
                        "reachability_status": ReachabilityStatus.REACHABLE.value,
                        "patch": {
                            "vcs_url": "https://example.com",
                            "commit_hash": "abc123",
                        },
                        "evidence": [
                            {
                                "symbol_name": "vuln_sym1",
                                "called": True,
                                "defined": False,
                                "imported": False,
                                "fingerprint": "88ad9e67c53aa5f7c4"
                                "3ec4aa52ed34b7930068c9",
                                "reachable_from": [],
                            }
                        ],
                        "vulnerable_symbols": ["vuln_sym1"],
                        "fixed_symbols": ["fixed_sym1"],
                    }
                ]
            }

            res2 = MagicMock()
            res2.path = "src/file2.py"
            res2.extra_data = {
                "symbols_reachability": [
                    {
                        "advisory_uids": ["AVID-1"],
                        "reachability_status": ReachabilityStatus.UNKNOWN.value,
                        "patch": {
                            "vcs_url": "https://example.com",
                            "commit_hash": "def456",
                        },
                        "evidence": [],
                        "vulnerable_symbols": [],
                        "fixed_symbols": [],
                    }
                ]
            }

            res3 = MagicMock()
            res3.path = "src/file3.py"
            res3.extra_data = {
                "symbols_reachability": [
                    {
                        "advisory_uids": ["AVID-2"],
                        "reachability_status": ReachabilityStatus.NOT_REACHABLE.value,
                        "patch": {
                            "vcs_url": "https://example2.com",
                            "commit_hash": "46a4asf",
                        },
                        "evidence": [],
                        "vulnerable_symbols": [],
                        "fixed_symbols": [],
                    }
                ]
            }

            res_empty = MagicMock()
            res_empty.path = "src/empty.py"
            res_empty.extra_data = {}

            pipeline.candidate_resources = [res2, res3, res_empty, res1]
            pipeline.generate_advisory_reachability_report()

            with open(output_file) as f:
                report = json.load(f)

            expected_report = {
                "purl": "pkg:pypi/test",
                "advisories": [
                    {
                        "advisory_uid": "AVID-1",
                        "is_reachable": ReachabilityStatus.NOT_REACHABLE.value,
                        "details": [
                            {
                                "resource_path": "src/file2.py",
                                "patch": {
                                    "vcs_url": "https://example.com",
                                    "commit_hash": "def456",
                                },
                                "is_reachable": None,
                                "tool_details": [],
                                "vulnerable_symbols": [],
                                "fixed_symbols": [],
                            },
                            {
                                "resource_path": "src/file1.py",
                                "patch": {
                                    "vcs_url": "https://example.com",
                                    "commit_hash": "abc123",
                                },
                                "is_reachable": None,
                                "tool_details": [],
                                "vulnerable_symbols": ["vuln_sym1"],
                                "fixed_symbols": ["fixed_sym1"],
                            },
                        ],
                    },
                    {
                        "advisory_uid": "AVID-2",
                        "is_reachable": "no",
                        "details": [
                            {
                                "resource_path": "src/file3.py",
                                "patch": {
                                    "vcs_url": "https://example2.com",
                                    "commit_hash": "46a4asf",
                                },
                                "is_reachable": None,
                                "tool_details": [],
                                "vulnerable_symbols": [],
                                "fixed_symbols": [],
                            },
                            {
                                "resource_path": "src/file1.py",
                                "patch": {
                                    "vcs_url": "https://example.com",
                                    "commit_hash": "abc123",
                                },
                                "is_reachable": None,
                                "tool_details": [],
                                "vulnerable_symbols": ["vuln_sym1"],
                                "fixed_symbols": ["fixed_sym1"],
                            },
                        ],
                    },
                ],
            }

            self.assertEqual(report, expected_report)

    def _run_reachability_pipeline(
        self,
        mock_package_vulnerabilities,
        mock_collect_symbols,
        mock_repo,
        file_path,
        app_text,
        vuln_text,
        fixed_text,
        expected_results,
    ):
        """Shared helper to run the end-to-end reachability pipeline."""
        analyzer = PatchAnalyzer(repo=MagicMock(), commit_hash="dummy")

        removed_lines, added_lines = analyzer.compute_changed_lines(
            vulnerable_text=vuln_text, fixed_text=fixed_text
        )
        vuln_meta, fixed_meta, lang = analyzer.analyze(
            vulnerable_text=vuln_text,
            fixed_text=fixed_text,
            removed_lines=removed_lines,
            added_lines=added_lines,
            file_path=file_path,
        )

        self.assertTrue(lang)
        self.assertTrue(vuln_meta or fixed_meta)

        mock_package_vulnerabilities.return_value = [
            {
                "fixed_in_patches": [
                    {
                        "vcs_url": "https://github.com/aboutcode-org/test",
                        "commit_hash": "07ec0de1964b14bf085a1c9a27ece2b61ab6105c",
                    }
                ]
            }
        ]

        mock_collect_symbols.return_value = {
            lang: {
                "vulnerable": {
                    f"{file_path}::{key}": metadata
                    for key, metadata in vuln_meta.items()
                },
                "fixed": {
                    f"{file_path}::{key}": metadata
                    for key, metadata in fixed_meta.items()
                },
            }
        }

        resource_file = self.project1.codebase_path / file_path
        resource_file.parent.mkdir(parents=True, exist_ok=True)
        resource_file.write_text(app_text)
        collect_and_create_codebase_resources(self.project1)

        resource = self.project1.codebaseresources.get(path=file_path)
        resource.programming_language = lang
        resource.save()

        run = self.project1.add_pipeline("analyze_symbols_reachability")
        pipeline = run.make_pipeline_instance()
        pipeline.execute()

        resource.refresh_from_db()
        results = resource.extra_data.get("symbols_reachability")
        self.assertEqual(results, expected_results)

    @patch("scanpipe.pipelines.analyze_symbols_reachability.Repo")
    @patch("scanpipe.pipes.reachability.PatchAnalyzer.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_python_get_symbol_reachability_results(
        self,
        mock_package_vulnerabilities,
        mock_collect_symbols,
        mock_repo,
    ):
        """Test the end-to-end reachability pipeline for Python."""
        file_path = "app.py"
        app_text = (self.data / "python" / file_path).read_text()
        vuln_text = (self.data / "python" / "vuln-app.py").read_text()
        fixed_text = (self.data / "python" / "fixed-app.py").read_text()

        expected_results = [
            {
                "patch": {
                    "vcs_url": "https://github.com/aboutcode-org/test",
                    "commit_hash": "07ec0de1964b14bf085a1c9a27ece2b61ab6105c",
                },
                "is_reachable": "yes",
                "tool_details": [
                    {
                        "is_exact": True,
                        "is_called": False,
                        "is_defined": True,
                        "is_imported": False,
                        "symbol_name": "debug",
                        "reachable_from": [],
                    },
                    {
                        "is_exact": True,
                        "is_called": True,
                        "is_defined": True,
                        "is_imported": False,
                        "symbol_name": "serve_report.build_file_path",
                        "reachable_from": ["serve_report"],
                    },
                    {
                        "is_exact": True,
                        "is_called": True,
                        "is_defined": True,
                        "is_imported": False,
                        "symbol_name": "serve_report",
                        "reachable_from": ["handle_request"],
                    },
                ],
                "advisory_uids": [],
                "fixed_symbols": [
                    "debug",
                    "serve_report",
                    "serve_report.build_file_path",
                ],
                "vulnerable_symbols": [
                    "debug",
                    "serve_report",
                    "serve_report.build_file_path",
                ],
            }
        ]

        self._run_reachability_pipeline(
            mock_package_vulnerabilities,
            mock_collect_symbols,
            mock_repo,
            file_path,
            app_text,
            vuln_text,
            fixed_text,
            expected_results,
        )

    @patch("scanpipe.pipelines.analyze_symbols_reachability.Repo")
    @patch("scanpipe.pipes.reachability.PatchAnalyzer.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_java_get_symbol_reachability_results(
        self,
        mock_package_vulnerabilities,
        mock_collect_symbols,
        mock_repo,
    ):
        """Test the end-to-end reachability pipeline for Java."""
        file_path = "app.java"
        app_text = (self.data / "java" / file_path).read_text()
        vuln_text = (self.data / "java" / "vuln-app.java").read_text()
        fixed_text = (self.data / "java" / "fixed-app.java").read_text()

        expected_results = [
            {
                "patch": {
                    "vcs_url": "https://github.com/aboutcode-org/test",
                    "commit_hash": "07ec0de1964b14bf085a1c9a27ece2b61ab6105c",
                },
                "is_reachable": "yes",
                "tool_details": [
                    {
                        "is_exact": False,
                        "is_called": False,
                        "is_defined": True,
                        "is_imported": False,
                        "symbol_name": "App",
                        "reachable_from": [],
                    },
                    {
                        "is_exact": True,
                        "is_called": False,
                        "is_defined": True,
                        "is_imported": False,
                        "symbol_name": "App.serveReport",
                        "reachable_from": [],
                    },
                    {
                        "is_exact": False,
                        "is_called": True,
                        "is_defined": True,
                        "is_imported": False,
                        "symbol_name": "App.buildFilePath",
                        "reachable_from": ["App.serveReport"],
                    },
                ],
                "advisory_uids": [],
                "fixed_symbols": ["App", "App.buildFilePath", "App.serveReport"],
                "vulnerable_symbols": ["App", "App.buildFilePath", "App.serveReport"],
            }
        ]

        self._run_reachability_pipeline(
            mock_package_vulnerabilities,
            mock_collect_symbols,
            mock_repo,
            file_path,
            app_text,
            vuln_text,
            fixed_text,
            expected_results,
        )

    def test_extract_definitions(self):
        """
        Test extracting functions, classes, and constant
        definitions from Python code.
        """
        source_code = """
price = 0
class OrderManager:
    def __init__(self, order_id):
        self.order_id = order_id

    def process_payment(self):
        print("Processing...")

def calculate_discount(price):
    return price * 0.10

class InventoryItem:
    pass
"""

        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(code_text=source_code)
        functions = list(lang_query.get_functions(tree.root_node))

        self.assertEqual(
            len(functions), 3
        )  # '__init__', 'process_payment', and 'calculate_discount'

        self.assertEqual(functions[0][0].type, "function_definition")
        first_func_text = functions[0][0].text.decode("utf-8")
        self.assertIn("def __init__", first_func_text)

        classes = list(lang_query.get_classes(tree.root_node))
        self.assertEqual(len(classes), 2)
        second_class_text = classes[1][0].text.decode("utf-8")
        self.assertIn("class InventoryItem", second_class_text)

        constants = list(lang_query.get_constants(tree.root_node))
        self.assertEqual(len(constants), 1)

    def test_extract_definitions_empty(self):
        """Test parsing empty or None source code"""
        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast("")

        self.assertIsNone(tree)

        tree_none, _ = lang_query.parse_code_to_ast(None)
        self.assertIsNone(tree_none)

    def test_get_qualified_name_functions(self):
        """Test building qualified names for nested and top-level functions."""
        source_code = """
class CoreService:
    class Validator:
        def validate_payload(self, data):
            return True

def global_utility():
    pass
        """

        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(source_code)

        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        index = extractor.extract_definitions_index()

        functions = list(lang_query.get_functions(tree.root_node))
        self.assertEqual(len(functions), 2)

        outer_function_name = extractor._build_qualified_name(functions[0][0], index)
        inner_function_name = extractor._build_qualified_name(functions[1][0], index)

        self.assertEqual(outer_function_name, "CoreService.Validator.validate_payload")
        self.assertEqual(inner_function_name, "global_utility")

    def test_get_qualified_classes(self):
        """Test building qualified names for nested class definitions."""
        source_code = """
class FleetManagement:
    class DroneController:
        pass
        """
        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(source_code)

        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        index = extractor.extract_definitions_index()

        classes = list(lang_query.get_classes(tree.root_node))
        self.assertEqual(len(classes), 2)

        outer_class_name = extractor._build_qualified_name(classes[0][0], index)
        inner_class_name = extractor._build_qualified_name(classes[1][0], index)

        self.assertEqual(outer_class_name, "FleetManagement")
        self.assertEqual(inner_class_name, "FleetManagement.DroneController")

    def test_classify_reachability(self):
        """
        Test reachability classification for fingerprint
        and evidence-based results.
        """
        self.assertEqual(classify_reachability(None), ReachabilityStatus.NOT_REACHABLE)
        self.assertEqual(classify_reachability({}), ReachabilityStatus.NOT_REACHABLE)
        self.assertEqual(
            classify_reachability({"tool_details": {}}),
            ReachabilityStatus.NOT_REACHABLE,
        )
        self.assertEqual(
            classify_reachability({"tool_details": {"is_exact": True}}),
            ReachabilityStatus.REACHABLE,
        )

        self.assertEqual(
            classify_reachability(
                {"tool_details": {"is_imported": True, "is_called": True}}
            ),
            ReachabilityStatus.REACHABLE,
        )
        self.assertEqual(
            classify_reachability(
                {"tool_details": {"is_imported": True, "is_called": False}}
            ),
            ReachabilityStatus.UNKNOWN,
        )
        self.assertEqual(
            classify_reachability(
                {"tool_details": {"is_imported": False, "is_called": False}}
            ),
            ReachabilityStatus.NOT_REACHABLE,
        )

    def test_build_symbol_metadata_processing(self):
        """Test building metadata for nested changed symbols with deduplication."""
        source_code = """
class Controller:
    def process_data(payload):
        def inner_helper():
            return True
        return payload.strip()

if True:
    def process_data(payload):
        return payload
"""
        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(source_code)
        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        vuln_nodes = extractor.extract_changed_symbols(
            changed_lines=[1, 2, 3, 4, 5, 6, 7, 8, 9]
        )
        metadata = PatchAnalyzer.build_symbol_metadata(
            nodes=vuln_nodes, extractor=extractor
        )
        self.assertEqual(
            metadata,
            {
                "Controller": {
                    "qualified_name": "Controller",
                    "text": "class Controller:\n"
                    "    def process_data(payload):\n"
                    "        def inner_helper():\n  "
                    "          return True\n    "
                    "    return payload.strip()",
                    "fingerprint": "de81abd637e27302d8e19c41eab8f4"
                    "fb6b8abdd9fc4f1fb31d354bc7b23f6d4d",
                    "start_line": 2,
                    "end_line": 6,
                    "node_type": "class_definition",
                },
                "Controller.process_data": {
                    "qualified_name": "Controller.process_data",
                    "text": "def process_data(payload):\n"
                    "        def inner_helper():\n"
                    "            return True\n"
                    "        return payload.strip()",
                    "fingerprint": "b0d0ad9a92209a6d79b84e932ce3"
                    "02a8bc9054a405131adf7dc21e06e2e7c0c1",
                    "start_line": 3,
                    "end_line": 6,
                    "node_type": "function_definition",
                },
                "Controller.process_data.inner_helper": {
                    "qualified_name": "Controller.process_data.inner_helper",
                    "text": "def inner_helper():\n            return True",
                    "fingerprint": "ee2e246e01e960826cb39a9466e58095"
                    "d209fdd1cbf8458630be430b3371d6a3",
                    "start_line": 4,
                    "end_line": 5,
                    "node_type": "function_definition",
                },
            },
        )

    def test_diff_changed_symbols(self):
        """Test that changed, added, and removed symbols are correctly identified."""
        vuln_meta = {
            "serve_report": {
                "qualified_name": "app.serve_report",
                "text": "def serve_report():\n    return os.path.join(base, filename)",
            },
            "sanitize_input": {
                "qualified_name": "app.sanitize_input",
                "text": "def sanitize_input(x):\n    return x.strip()",
            },
            "deprecated_logger": {
                "qualified_name": "app.deprecated_logger",
                "text": "def deprecated_logger():\n    print('legacy')",
            },
        }

        fixed_meta = {
            "serve_report": {
                "qualified_name": "app.serve_report",
                "text": "def serve_report():\n   "
                " if not target.startswith(base): "
                "raise ValueError\n "
                "   return target",
            },
            "sanitize_input": {
                "qualified_name": "app.sanitize_input",
                "text": "def sanitize_input(x):\n    return x.strip()",
            },
            "audit_trail": {
                "qualified_name": "app.audit_trail",
                "text": "def audit_trail():\n    log.info('action')",
            },
        }

        vuln_only, fixed_only = PatchAnalyzer.diff_changed_symbols(
            vuln_meta, fixed_meta
        )
        self.assertEqual(
            vuln_only,
            {
                "serve_report": {
                    "qualified_name": "app.serve_report",
                    "text": "def serve_report():\n "
                    "   return os.path.join(base, filename)",
                },
                "deprecated_logger": {
                    "qualified_name": "app.deprecated_logger",
                    "text": "def deprecated_logger():\n    print('legacy')",
                },
            },
        )
        self.assertEqual(
            fixed_only,
            {
                "serve_report": {
                    "qualified_name": "app.serve_report",
                    "text": "def serve_report():\n    if not target.startswith(base): "
                    "raise ValueError\n    return target",
                },
                "audit_trail": {
                    "qualified_name": "app.audit_trail",
                    "text": "def audit_trail():\n    log.info('action')",
                },
            },
        )

    def test_analyze_patched_file(self):
        """Test analyzing a patched file and extracting changed symbol metadata."""
        vuln_text = (self.data / "python" / "vuln-app.py").read_text(encoding="utf-8")
        fixed_text = (self.data / "python" / "fixed-app.py").read_text(encoding="utf-8")
        file_path = "python/app.py"
        removed_lines, added_lines = PatchAnalyzer.compute_changed_lines(
            vuln_text, fixed_text
        )

        vuln_meta, fixed_meta, lang = PatchAnalyzer.analyze(
            vulnerable_text=vuln_text,
            fixed_text=fixed_text,
            removed_lines=removed_lines,
            added_lines=added_lines,
            file_path=file_path,
        )

        self.assertEqual(
            vuln_meta,
            {
                "debug": {
                    "qualified_name": "debug",
                    "text": "debug = False",
                    "fingerprint": "336908735214468b103dbde11c3ff"
                    "bd2f76ac9212b8514f831cfa078a67892df",
                    "start_line": 3,
                    "end_line": 3,
                    "node_type": "assignment",
                },
                "serve_report.build_file_path": {
                    "qualified_name": "serve_report.build_file_path",
                    "text": "def build_file_path(filename):\n"
                    "        # VULNERABLE: Direct concatenation "
                    "allows Path Traversal\n "
                    '       # An attacker passing "../../etc/passwd" '
                    "could read system files.\n"
                    "        return os.path.join(generator.base_dir, filename)",
                    "fingerprint": "762e4f7d03b1bf4359c3ca364e55814"
                    "0239913bfabcc5aa77156460c2eb0a355",
                    "start_line": 19,
                    "end_line": 22,
                    "node_type": "function_definition",
                },
                "serve_report": {
                    "qualified_name": "serve_report",
                    "text": "def serve_report(request_payload):\n "
                    '   """Top-level function handling a request."""\n'
                    '    generator = ReportGenerator("/var/reports")\n'
                    '    requested_file = request_payload.get("file")\n\n'
                    "    # Helper function nested inside serve_report\n"
                    "    def build_file_path(filename):\n "
                    "       # VULNERABLE: Direct "
                    "concatenation allows Path Traversal\n "
                    "       # An attacker passing "
                    '"../../etc/passwd" could read system files.\n'
                    "        return os.path.join(generator.base_dir, filename)\n\n"
                    "    if not requested_file:\n   "
                    '     return "Error: No file specified"\n\n  '
                    "  target_path = build_file_path(requested_file)\n\n  "
                    "  if os.path.exists(target_path):\n      "
                    '  return f"Serving content of {target_path}"\n\n  '
                    '  return "Error: File not found"',
                    "fingerprint": "d7675efb263896da2a3c006795118"
                    "33553907e7e6ea619115a6dfc8625c3457e",
                    "start_line": 13,
                    "end_line": 32,
                    "node_type": "function_definition",
                },
            },
        )

        self.assertEqual(
            fixed_meta,
            {
                "debug": {
                    "qualified_name": "debug",
                    "text": "debug = True",
                    "fingerprint": "55d2e2010de610fd32f0c28bc49f535"
                    "3d6ac60afc70adc5713aa4b675646590e",
                    "start_line": 3,
                    "end_line": 3,
                    "node_type": "assignment",
                },
                "serve_report.build_file_path": {
                    "qualified_name": "serve_report.build_file_path",
                    "text": "def build_file_path(filename):\n "
                    "       # FIXED: Validate that the resolved"
                    " path stays within the base_dir\n "
                    "       base = os.path.abspath(generator.base_dir)\n  "
                    "      target = os.path.abspath(os.path.join(base, filename))\n    "
                    "    if not target.startswith(base):\n       "
                    '     raise ValueError("Path Traversal Detected")\n   '
                    "     return target",
                    "fingerprint": "646743b5d5497f6ea3b96f860bcbe"
                    "b38096ce008ad16d2b9a9c3f77a98faca80",
                    "start_line": 19,
                    "end_line": 25,
                    "node_type": "function_definition",
                },
                "serve_report": {
                    "qualified_name": "serve_report",
                    "text": "def serve_report(request_payload):\n "
                    '   """Top-level function handling a request."""\n '
                    '   generator = ReportGenerator("/var/reports")\n '
                    '   requested_file = request_payload.get("file")\n\n  '
                    "  # Helper function nested inside serve_report\n    "
                    "def build_file_path(filename):\n    "
                    "    # FIXED: Validate that the"
                    " resolved path stays within the base_dir\n "
                    "       base = os.path.abspath(generator.base_dir)\n   "
                    "     target = os.path.abspath(os.path.join(base, filename))\n"
                    "        if not target.startswith(base):\n     "
                    '       raise ValueError("Path Traversal Detected")\n    '
                    "    return target\n\n   "
                    " if not requested_file:\n     "
                    '   return "Error: No file specified"\n\n    try:\n    '
                    "    target_path = build_file_path(requested_file)\n"
                    "    except ValueError:\n  "
                    '      return "Error: Invalid path"\n\n  '
                    "  if os.path.exists(target_path):\n   "
                    '     return f"Serving content of {target_path}"\n\n '
                    '   return "Error: File not found"',
                    "fingerprint": "2deedb21d5f9b1409c59f0b1e55"
                    "12d73d9afdfc3f469ccf86e8835915d240e76",
                    "start_line": 13,
                    "end_line": 38,
                    "node_type": "function_definition",
                },
            },
        )

    def test_extract_symbols(self):
        """Test extracting only the nested function containing the changed line."""
        source_code = (
            "def serve_report(request):\n"  # Line 1 (Row 0)
            "    # Some processing here\n"  # Line 2 (Row 1)
            "    def build_path(filename):\n"  # Line 3 (Row 2)
            "        return filename.strip()\n"  # Line 4 (Row 3) <- Targeted Change
            "    return build_path(request)\n"  # Line 5 (Row 4)
        )

        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(source_code)

        changed_lines = [4]
        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        changed_symbols = extractor.extract_changed_symbols(changed_lines)

        self.assertEqual(len(changed_symbols), 1)
        target_node = changed_symbols[0]
        self.assertEqual(target_node.type, "function_definition")

        node_text = target_node.text.decode("utf-8")
        self.assertIn("def build_path", node_text)
        self.assertNotIn("def serve_report", node_text)

    def test_extract_symbols_deduplication(self):
        """
        Test that multiple changed lines within
        the same function produce only a single enclosing symbol.
        """
        source_code = (
            "def calculate_total(price, tax):\n"
            "    amount = price * tax\n"  # Line 2 -> Changed
            "    return price + amount\n"  # Line 3 -> Changed
        )

        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(source_code)

        changed_lines = [2, 3]
        symbol_extractor = SymbolExtractor(
            lang_query=lang_query, root_node=tree.root_node
        )
        enclosing_symbols = symbol_extractor.extract_changed_symbols(changed_lines)
        self.assertEqual(len(enclosing_symbols), 1)
        self.assertEqual(enclosing_symbols[0].type, "function_definition")

    def test_extract_direct(self):
        """
        Test that direct function calls are
        extracted from the syntax tree.
        """
        source_code = """
def hello():
    return 10
def clean_function():
    x = 10
    y = 20
    return hello() + x + y
        """.strip()

        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(code_text=source_code)
        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        result = extractor.extract_calls(node=tree.root_node)
        self.assertEqual(
            result,
            [(None, "hello")],
        )

    def test_extract_direct_calls(self):
        """Test extraction of direct function calls."""
        python_source = """
self.update()
process_data()
user.save()
        """.strip()

        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(code_text=python_source)
        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        python_calls = extractor.extract_calls(node=tree.root_node)

        expected_python = [
            ("self", "update"),
            (None, "process_data"),
            ("user", "save"),
        ]
        self.assertEqual(expected_python, python_calls)

    def test_extract_imports(self):
        """
        Test extraction of imported symbols and their
        fully qualified module paths.
        """
        source_code = """
from django.db import models
import os.path
import numpy as np
from a.b import c as d
from . import utils
from ..core import engine
from math import *
        """.strip()

        lang_query = TS_QUERIES["Python"]()
        tree, _ = lang_query.parse_code_to_ast(code_text=source_code)
        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        result = extractor.extract_imports()

        expected_map = {
            "models": "django.db.models",
            "os": "os.path",
            "np": "numpy",
            "d": "a.b.c",
            "utils": ".utils",
            "engine": "..core.engine",
            "*": ["math"],
        }

        self.assertEqual(result, expected_map)

    def test_resource_patch_matcher_python(self):
        """
        Test matching
        Python patch symbols against imports and calls.
        """
        vuln_text = """
def direct_func():
    return eval("1")

def aliased_func():
    return eval("2")

def wildcard_func():
    return eval("3")

def multiline_func():
    return eval("6")

def deep_func():
    return eval("7")

def relative_func():
    return eval("8")

class MyClass:
    def class_method(self):
        return eval("4")

class InnerClass:
    def deep_method(self):
        return eval("5")
    """.strip()

        fixed_text = """
def direct_func():
    return int("1")

def aliased_func():
    return int("2")

def wildcard_func():
    return int("3")

def multiline_func():
    return int("6")

def deep_func():
    return int("7")

def relative_func():
    return int("8")

class MyClass:
    def class_method(self):
        return int("4")

    class InnerClass:
        def deep_method(self):
            return int("5")
        """.strip()

        app_text = """
from my_module import direct_func
from my_module import aliased_func as af
from my_module import MyClass as C
from my_module import wildcard_func
from my_module import *
from a.b import deep_func
from .relative_module import relative_func
from my_module import (
    multiline_func,
)

def execute():
    direct_func()
    af()
    wildcard_func()
    multiline_func()
    deep_func()
    relative_func()

    c = C()
    c.class_method()

    inner = C.InnerClass()
    inner.deep_method()
""".strip()

        file_path = "my_module.py"
        analyzer = PatchAnalyzer(repo=MagicMock(), commit_hash="dummy")
        removed_lines, added_lines = analyzer.compute_changed_lines(
            vuln_text, fixed_text
        )

        vuln_meta, fixed_meta, lang = analyzer.analyze(
            vulnerable_text=vuln_text,
            fixed_text=fixed_text,
            removed_lines=removed_lines,
            added_lines=added_lines,
            file_path=file_path,
        )

        patch_symbols_by_language = {
            lang: {
                "vulnerable": {
                    f"{file_path}::{key}": metadata
                    for key, metadata in vuln_meta.items()
                },
                "fixed": {
                    f"{file_path}::{key}": metadata
                    for key, metadata in fixed_meta.items()
                },
            }
        }

        resource_analyzer = ResourceAnalyzer(resource_text=app_text, language=lang)
        resource_index = resource_analyzer.build_index()
        matcher = ResourcePatchMatcher(resource_index)

        vulnerable_symbols = patch_symbols_by_language[lang]["vulnerable"]
        fixed_symbols = patch_symbols_by_language[lang]["fixed"]

        vuln_details = matcher.match(vulnerable_symbols)
        fixed_details = matcher.match(fixed_symbols)

        matched = {**vuln_details, **fixed_details}
        self.assertIn("direct_func", matched)
        self.assertTrue(matched["direct_func"]["is_imported"])
        self.assertTrue(matched["direct_func"]["is_called"])
        self.assertEqual(matched["direct_func"]["reachable_from"], ["execute"])

        self.assertIn("aliased_func", matched)
        self.assertTrue(matched["aliased_func"]["is_imported"])
        self.assertTrue(matched["aliased_func"]["is_called"])
        self.assertEqual(matched["aliased_func"]["reachable_from"], ["execute"])

        self.assertIn("wildcard_func", matched)
        self.assertTrue(matched["wildcard_func"]["is_imported"])
        self.assertTrue(matched["wildcard_func"]["is_called"])
        self.assertEqual(matched["wildcard_func"]["reachable_from"], ["execute"])

        self.assertIn("MyClass.class_method", matched)
        self.assertTrue(matched["MyClass.class_method"]["is_imported"])
        self.assertTrue(matched["MyClass.class_method"]["is_called"])
        self.assertEqual(matched["MyClass.class_method"]["reachable_from"], ["execute"])

        self.assertIn("MyClass.InnerClass.deep_method", matched)
        self.assertTrue(matched["MyClass.InnerClass.deep_method"]["is_imported"])
        self.assertTrue(matched["MyClass.InnerClass.deep_method"]["is_called"])
        self.assertEqual(
            matched["MyClass.InnerClass.deep_method"]["reachable_from"], ["execute"]
        )

        self.assertIn("multiline_func", matched)
        self.assertTrue(matched["multiline_func"]["is_imported"])
        self.assertTrue(matched["multiline_func"]["is_called"])
        self.assertEqual(matched["multiline_func"]["reachable_from"], ["execute"])

        self.assertIn("deep_func", matched)
        self.assertTrue(matched["deep_func"]["is_imported"])
        self.assertTrue(matched["deep_func"]["is_called"])
        self.assertEqual(matched["deep_func"]["reachable_from"], ["execute"])

        self.assertIn("relative_func", matched)
        self.assertTrue(matched["relative_func"]["is_imported"])
        self.assertTrue(matched["relative_func"]["is_called"])
        self.assertEqual(matched["relative_func"]["reachable_from"], ["execute"])

    def test_resource_patch_matcher_java(self):
        """
        Test matching
        Java patch symbols against imports and calls.
        """
        vuln_text = """
package com.example;

public class Service {
    public void processRequest(String input) {
        Runtime.getRuntime().exec(input);
    }

    public void utilityMethod() {
        Runtime.getRuntime().exec("cmd");
    }
}
    """.strip()

        fixed_text = """
package com.example;

public class Service {
    public void processRequest(String input) {
        System.out.println(input);
    }

    public void utilityMethod() {
        System.out.println("cmd");
    }
}
    """.strip()

        app_text = """
package com.test;

import com.example.Service;
import com.example.*;

public class Main {
    public void execute(String data) {
        Service service = new Service();
        service.processRequest(data);

        service.utilityMethod();
    }
}
    """.strip()

        file_path = "Service.java"
        analyzer = PatchAnalyzer(repo=MagicMock(), commit_hash="dummy")
        removed_lines, added_lines = analyzer.compute_changed_lines(
            vuln_text, fixed_text
        )

        vuln_meta, fixed_meta, lang = analyzer.analyze(
            vulnerable_text=vuln_text,
            fixed_text=fixed_text,
            removed_lines=removed_lines,
            added_lines=added_lines,
            file_path=file_path,
        )

        patch_symbols_by_language = {
            lang: {
                "vulnerable": {
                    f"{file_path}::{key}": metadata
                    for key, metadata in vuln_meta.items()
                },
                "fixed": {
                    f"{file_path}::{key}": metadata
                    for key, metadata in fixed_meta.items()
                },
            }
        }

        resource_analyzer = ResourceAnalyzer(resource_text=app_text, language=lang)
        resource_index = resource_analyzer.build_index()
        matcher = ResourcePatchMatcher(resource_index)

        vulnerable_symbols = patch_symbols_by_language[lang]["vulnerable"]
        fixed_symbols = patch_symbols_by_language[lang]["fixed"]

        vuln_details = matcher.match(vulnerable_symbols)
        fixed_details = matcher.match(fixed_symbols)

        matched = {**vuln_details, **fixed_details}
        self.assertIn("Service.processRequest", matched)
        self.assertTrue(matched["Service.processRequest"]["is_imported"])
        self.assertTrue(matched["Service.processRequest"]["is_called"])
        self.assertEqual(
            matched["Service.processRequest"]["reachable_from"], ["Main.execute"]
        )

        self.assertIn("Service.utilityMethod", matched)
        self.assertTrue(matched["Service.utilityMethod"]["is_imported"])
        self.assertTrue(matched["Service.utilityMethod"]["is_called"])
        self.assertEqual(
            matched["Service.utilityMethod"]["reachable_from"], ["Main.execute"]
        )

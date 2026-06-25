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
from unittest.mock import PropertyMock
from unittest.mock import patch

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import analyze_patched_file
from scanpipe.pipes.reachability import build_symbol_metadata
from scanpipe.pipes.reachability import classify_reachability
from scanpipe.pipes.reachability import collect_imports
from scanpipe.pipes.reachability import compute_reachable_symbols
from scanpipe.pipes.reachability import diff_changed_symbols
from scanpipe.pipes.reachability import extract_direct_calls
from scanpipe.pipes.reachability import get_symbol_reachability_results
from scanpipe.pipes.reachability import parse_diff_lines
from scanpipe.pipes.symbols import collect_definitions
from scanpipe.pipes.symbols import extract_definitions
from scanpipe.pipes.symbols import extract_symbols
from scanpipe.pipes.symbols import parse_code_to_ast
from scanpipe.pipes.symbols import qualified_name_from_index


class SymbolReachabilityPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "reachability"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project1.codebase_path.mkdir(parents=True, exist_ok=True)

    @patch("scanpipe.pipes.reachability.clone_repo")
    @patch("scanpipe.pipes.reachability.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_get_symbol_reachability_results(
        self,
        mock_package_vulnerabilities,
        mock_collect_symbols,
        mock_clone_repo,
    ):
        app_text = (self.data / "app.py").read_text()
        vuln_text = (self.data / "vuln-app.py").read_text()
        fixed_text = (self.data / "fixed-app.py").read_text()
        diff_text = (self.data / "diff-app.patch").read_text()
        diff_line_map = parse_diff_lines(diff_text=diff_text)
        file_path = "app.py"
        removed_lines, added_lines = diff_line_map.get(file_path, ([], []))

        vuln_meta, fixed_meta, lang = analyze_patched_file(
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

        mock_clone_repo.return_value = str(self.project1.codebase_path)
        mock_collect_symbols.return_value = {
            lang: {
                "vulnerable": {
                    f"app.py::{key}": metadata for key, metadata in vuln_meta.items()
                },
                "fixed": {
                    f"app.py::{key}": metadata for key, metadata in fixed_meta.items()
                },
            }
        }

        resource_file = self.project1.codebase_path / "app.py"
        resource_file.write_text(app_text)
        collect_and_create_codebase_resources(self.project1)

        resource = self.project1.codebaseresources.get(path="app.py")
        resource.programming_language = lang
        resource.save()

        with patch("scanpipe.pipes.reachability.Repo"):
            get_symbol_reachability_results(self.project1)

        resource.refresh_from_db()
        results = resource.extra_data.get("symbols_reachability")

        self.assertEqual(
            results,
            {
                "symbols_reachability": {
                    "patch": {
                        "vcs_url": "https://github.com/aboutcode-org/test",
                        "commit_hash": "07ec0de1964b14bf085a1c9a27ece2b61ab6105c",
                    },
                    "evidence": [
                        {
                            "called": False,
                            "defined": True,
                            "imported": False,
                            "fingerprint": "d7675efb263896da2a3c00679511833"
                            "553907e7e6ea619115a6dfc8625c3457e",
                            "symbol_name": "serve_report",
                            "reachable_from": [],
                        },
                        {
                            "called": True,
                            "defined": True,
                            "imported": False,
                            "fingerprint": "762e4f7d03b1bf4359c3ca364"
                            "e558140239913bfabcc5aa77156460c2eb0a355",
                            "symbol_name": "serve_report.build_file_path",
                            "reachable_from": ["serve_report"],
                        },
                    ],
                    "fixed_symbols": ["serve_report", "serve_report.build_file_path"],
                    "vulnerable_symbols": [
                        "serve_report",
                        "serve_report.build_file_path",
                    ],
                    "reachability_status": "REACHABLE",
                }
            },
        )

    def test_extract_definitions(self):
        source_code = """
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
        tree, _ = parse_code_to_ast(source_code, "Python")
        functions = extract_definitions(tree, "Python", kinds=("functions",))
        self.assertEqual(
            len(functions), 3
        )  # '__init__', 'process_payment', and 'calculate_discount'

        self.assertEqual(functions[0].type, "function_definition")
        first_func_text = functions[0].text.decode("utf-8")
        self.assertIn("def __init__", first_func_text)

        classes = extract_definitions(tree, "Python", kinds=("classes",))
        self.assertEqual(len(classes), 2)
        second_class_text = classes[1].text.decode("utf-8")
        self.assertIn("class InventoryItem", second_class_text)

    def test_extract_definitions_empty(self):
        tree, _ = parse_code_to_ast("", "Python")
        self.assertEqual(extract_definitions(tree, "Python", kinds=("functions",)), [])
        self.assertEqual(extract_definitions(tree, "Python", kinds=("functions",)), [])
        self.assertEqual(extract_definitions(None, "Python", kinds=("classes",)), [])
        self.assertEqual(extract_definitions(None, "Python", kinds=("classes",)), [])

    def test_get_qualified_name_functions(self):
        source_code = """
class CoreService:
    class Validator:
        def validate_payload(self, data):
            return True

def global_utility():
    pass
        """

        tree, _ = parse_code_to_ast(source_code, "Python")
        index = collect_definitions(tree.root_node, "Python")

        functions = extract_definitions(tree, "Python", kinds=("functions",))
        self.assertEqual(len(functions), 2)

        outer_function_name = qualified_name_from_index(functions[0], index)
        inner_function_name = qualified_name_from_index(functions[1], index)

        self.assertEqual(outer_function_name, "CoreService.Validator.validate_payload")
        self.assertEqual(inner_function_name, "global_utility")

    def test_get_qualified_classes(self):
        source_code = """
class FleetManagement:
    class DroneController:
        pass
        """
        tree, _ = parse_code_to_ast(source_code, "Python")
        index = collect_definitions(tree.root_node, "Python")

        classes = extract_definitions(tree, "Python", kinds=("classes",))
        self.assertEqual(len(classes), 2)

        outer_class_name = qualified_name_from_index(classes[0], index)
        inner_class_name = qualified_name_from_index(classes[1], index)

        self.assertEqual(outer_class_name, "FleetManagement")
        self.assertEqual(inner_class_name, "FleetManagement.DroneController")

    def test_classify_reachability(self):
        self.assertEqual(classify_reachability(None), ReachabilityStatus.NOT_REACHABLE)
        self.assertEqual(classify_reachability({}), ReachabilityStatus.NOT_REACHABLE)
        self.assertEqual(
            classify_reachability({"evidence": {"fingerprint": "hash123"}}),
            ReachabilityStatus.REACHABLE,
        )

        self.assertEqual(
            classify_reachability({"evidence": {"imported": True, "called": True}}),
            ReachabilityStatus.REACHABLE,
        )
        self.assertEqual(
            classify_reachability({"evidence": {"imported": True, "called": False}}),
            ReachabilityStatus.POTENTIALLY_REACHABLE,
        )
        self.assertEqual(
            classify_reachability({"evidence": {"imported": False, "called": False}}),
            ReachabilityStatus.NOT_REACHABLE,
        )

    def test_build_symbol_metadata_processing(self):
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
        tree, _ = parse_code_to_ast(source_code, "Python")
        nodes = extract_definitions(tree, "Python", kinds=("functions",))

        metadata = build_symbol_metadata(nodes, "Python")
        self.assertEqual(
            metadata,
            {
                "Controller.process_data": {
                    "qualified_name": "Controller.process_data",
                    "text": "def process_data(payload):\n"
                    "        def inner_helper():\n"
                    "            return True\n       "
                    " return payload.strip()",
                    "fingerprint": "b0d0ad9a92209a6d79b84e932ce302"
                    "a8bc9054a405131adf7dc21e06e2e7c0c1",
                    "start_line": 3,
                    "end_line": 6,
                    "node_type": "function_definition",
                },
                "Controller.process_data.inner_helper": {
                    "qualified_name": "Controller.process_data.inner_helper",
                    "text": "def inner_helper():\n            return True",
                    "fingerprint": "ee2e246e01e960826cb39a9466e5"
                    "8095d209fdd1cbf8458630be430b3371d6a3",
                    "start_line": 4,
                    "end_line": 5,
                    "node_type": "function_definition",
                },
                "process_data": {
                    "qualified_name": "process_data",
                    "text": "def process_data(payload):\n        return payload",
                    "fingerprint": "9b2797712c9ab60ea8452a4413965"
                    "c94d1b2f63739cab7de695e7b1dc0cf439a",
                    "start_line": 9,
                    "end_line": 10,
                    "node_type": "function_definition",
                },
            },
        )

    def test_diff_changed_symbols(self):
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

        vuln_only, fixed_only = diff_changed_symbols(vuln_meta, fixed_meta)

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
        vuln_text = (self.data / "vuln-app.py").read_text(encoding="utf-8")
        fixed_text = (self.data / "fixed-app.py").read_text(encoding="utf-8")
        diff_text = (self.data / "diff-app.patch").read_text(encoding="utf-8")
        diff_line_map = parse_diff_lines(diff_text=diff_text)
        file_path = "app.py"
        removed_lines, added_lines = diff_line_map.get(file_path, ([], []))

        vuln_meta, fixed_meta, lang = analyze_patched_file(
            vulnerable_text=vuln_text,
            fixed_text=fixed_text,
            removed_lines=removed_lines,
            added_lines=added_lines,
            file_path="app.py",
        )

        self.assertEqual(
            vuln_meta,
            {
                "serve_report": {
                    "qualified_name": "serve_report",
                    "text": "def serve_report(request_payload):\n"
                    '    """Top-level function handling a request."""\n'
                    '    generator = ReportGenerator("/var/reports")\n'
                    '    requested_file = request_payload.get("file")\n\n'
                    "    # Helper function nested inside serve_report\n"
                    "    def build_file_path(filename):\n"
                    "        # VULNERABLE: Direct concatenation allows Path Traversal\n"
                    "        # An attacker passing "
                    '"../../etc/passwd" '
                    "could read system files.\n"
                    "        return os.path.join(generator.base_dir, filename)\n\n"
                    "    if not requested_file:\n"
                    '        return "Error: No file specified"\n\n'
                    "    target_path = build_file_path(requested_file)\n\n"
                    "    if os.path.exists(target_path):\n"
                    '        return f"Serving content of {target_path}"\n\n'
                    '    return "Error: File not found"',
                    "fingerprint": "d7675efb263896da2a3c006795118"
                    "33553907e7e6ea619115a6dfc8625c3457e",
                    "start_line": 11,
                    "end_line": 30,
                    "node_type": "function_definition",
                },
                "serve_report.build_file_path": {
                    "qualified_name": "serve_report.build_file_path",
                    "text": "def build_file_path(filename):\n"
                    "        # VULNERABLE: Direct concatenation allows Path Traversal\n"
                    '        # An attacker passing "../../etc/passwd"'
                    " could read system files.\n"
                    "        return os.path.join(generator.base_dir, filename)",
                    "fingerprint": "762e4f7d03b1bf4359c3ca364e5581"
                    "40239913bfabcc5aa77156460c2eb0a355",
                    "start_line": 17,
                    "end_line": 20,
                    "node_type": "function_definition",
                },
            },
        )

        self.assertEqual(
            fixed_meta,
            {
                "serve_report": {
                    "qualified_name": "serve_report",
                    "text": "def serve_report(request_payload):\n"
                    '    """Top-level function handling a request."""\n'
                    '    generator = ReportGenerator("/var/reports")\n'
                    '    requested_file = request_payload.get("file")\n\n'
                    "    # Helper function nested inside serve_report\n"
                    "    def build_file_path(filename):\n"
                    "        # FIXED: Validate that the resolved "
                    "path stays within the base_dir\n"
                    "        base = os.path.abspath(generator.base_dir)\n"
                    "        target = os.path.abspath(os.path.join(base, filename))\n"
                    "        if not target.startswith(base):\n"
                    '            raise ValueError("Path Traversal Detected")\n'
                    "        return target\n\n"
                    "    if not requested_file:\n"
                    '        return "Error: No file specified"\n\n'
                    "    try:\n"
                    "        target_path = build_file_path(requested_file)\n"
                    "    except ValueError:\n"
                    '        return "Error: Invalid path"\n\n'
                    "    if os.path.exists(target_path):\n"
                    '        return f"Serving content of {target_path}"\n\n'
                    '    return "Error: File not found"',
                    "fingerprint": "2deedb21d5f9b1409c59f0b1e5512d"
                    "73d9afdfc3f469ccf86e8835915d240e76",
                    "start_line": 11,
                    "end_line": 36,
                    "node_type": "function_definition",
                },
                "serve_report.build_file_path": {
                    "qualified_name": "serve_report.build_file_path",
                    "text": "def build_file_path(filename):\n"
                    "        # FIXED: Validate that the resolved path"
                    " stays within the base_dir\n"
                    "        base = os.path.abspath(generator.base_dir)\n"
                    "        target = os.path.abspath(os.path.join(base, filename))\n"
                    "        if not target.startswith(base):\n"
                    '            raise ValueError("Path Traversal Detected")\n'
                    "        return target",
                    "fingerprint": "646743b5d5497f6ea3b96f860bcbe"
                    "b38096ce008ad16d2b9a9c3f77a98faca80",
                    "start_line": 17,
                    "end_line": 23,
                    "node_type": "function_definition",
                },
            },
        )

    def test_extract_symbols(self):
        source_code = (
            "def serve_report(request):\n"  # Line 1 (Row 0)
            "    # Some processing here\n"  # Line 2 (Row 1)
            "    def build_path(filename):\n"  # Line 3 (Row 2)
            "        return filename.strip()\n"  # Line 4 (Row 3) <- Targeted Change
            "    return build_path(request)\n"  # Line 5 (Row 4)
        )

        tree, _ = parse_code_to_ast(source_code, "Python")

        changed_lines = [4]
        enclosing_symbols = extract_symbols(tree, changed_lines, "Python")

        self.assertEqual(len(enclosing_symbols), 1)
        target_node = enclosing_symbols[0]
        self.assertEqual(target_node.type, "function_definition")

        node_text = target_node.text.decode("utf-8")
        self.assertIn("def build_path", node_text)
        self.assertNotIn("def serve_report", node_text)

    def test_extract_symbols_deduplication(self):
        source_code = (
            "def calculate_total(price, tax):\n"
            "    amount = price * tax\n"  # Line 2 -> Changed
            "    return price + amount\n"  # Line 3 -> Changed
        )

        tree, _ = parse_code_to_ast(source_code, "Python")
        changed_lines = [2, 3]

        enclosing_symbols = extract_symbols(tree, changed_lines, "Python")
        self.assertEqual(len(enclosing_symbols), 1)
        self.assertEqual(enclosing_symbols[0].type, "function_definition")

    def test_compute_reachable_symbols(self):
        edges_qualified = {
            "app.main": {"app.helper", "app.safe_func"},
            "app.helper": {"app.vuln_func"},
            "app.direct_caller": {"app.vuln_func"},
            "app.unrelated": {"app.safe_func"},
        }

        target_qns = ["app.vuln_func"]
        reachable, has_direct = compute_reachable_symbols(edges_qualified, target_qns)

        self.assertTrue(has_direct)

        expected_reachable = {"app.main", "app.helper", "app.direct_caller"}
        self.assertEqual(reachable, expected_reachable)

    def test_collect_imports(self):
        source_code = """
from django.db import models
import os.path
import numpy as np
from a.b import c as d
from . import utils
from ..core import engine
from math import *
        """.strip()

        tree, _ = parse_code_to_ast(source_code, "Python")
        real_root_node = tree.root_node
        result = collect_imports(real_root_node, language="Python")

        expected_map = {
            "models": "django.db.models",
            "os": "os.path",
            "np": "numpy",
            "d": "a.b.c",
            "utils": "..utils",
            "engine": "..core.engine",
            "*": ["math"],
        }

        self.assertEqual(result, expected_map)

    def test_extract_direct(self):
        source_code = """
def hello():
    return 10
def clean_function():
    x = 10
    y = 20
    return hello() + x + y
        """.strip()

        tree, _ = parse_code_to_ast(source_code, "Python")
        functions = extract_definitions(tree, "Python", kinds=("functions",))

        result = extract_direct_calls(functions[1], "Python")
        self.assertEqual(
            result,
            [(None, "hello")],
        )

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
from unittest.mock import patch

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import analyze_patched_file
from scanpipe.pipes.reachability import build_call_graph
from scanpipe.pipes.reachability import classify_reachability
from scanpipe.pipes.reachability import collect_and_store_symbol_reachability_results
from scanpipe.pipes.symbols import collect_definitions
from scanpipe.pipes.symbols import extract_definitions
from scanpipe.pipes.symbols import parse_code_to_ast
from scanpipe.pipes.symbols import qualified_name_from_index


class SymbolReachabilityPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "reachability"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project1.codebase_path.mkdir(parents=True, exist_ok=True)

    @patch("scanpipe.pipes.reachability.Repo")
    @patch("scanpipe.pipes.reachability.clone_repo")
    @patch("scanpipe.pipes.reachability.api_mocker")
    @patch("scanpipe.pipes.reachability.collect_patch_symbols")
    def test_collect_and_store_symbol_reachability_results(
        self, mock_collect_symbols, mock_api, mock_clone_repo, mock_repo
    ):
        app_text = (self.data / "app.py").read_text()
        vuln_text = (self.data / "vuln-app.py").read_text()
        fixed_text = (self.data / "fixed-app.py").read_text()
        diff_text = (self.data / "diff-app.patch").read_text()

        vuln_meta, fixed_meta, lang = analyze_patched_file(
            vulnerable_text=vuln_text,
            fixed_text=fixed_text,
            diff_text=diff_text,
            file_path="app.py",
        )

        self.assertTrue(lang)
        self.assertTrue(vuln_meta or fixed_meta)
        mock_api.return_value = [
            {
                "vcs_url": "https://github.com/aboutcode-org/test",
                "commit_hash": "07ec0de1964b14bf085a1c9a27ece2b61ab6105c",
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

        collect_and_store_symbol_reachability_results(self.project1)

        resource.refresh_from_db()
        results = resource.extra_data.get("symbols_reachability")

        assert results == [
            {
                "patch": {
                    "vcs_url": "https://github.com/aboutcode-org/test",
                    "commit_hash": "07ec0de1964b14bf085a1c9a27ece2b61ab6105c",
                },
                "summary": {
                    "call_paths": {},
                    "fixed_symbols": ["serve_report"],
                    "vulnerable_symbols": ["serve_report"],
                },
                "evidence": {
                    "serve_report": {
                        "called": False,
                        "defined": True,
                        "reachable_from": [],
                        "exact_match_fingerprint": "000000556d322a47595af353274b000aa324e014",
                    }
                },
                "reachability_status": "POTENTIALLY_REACHABLE",
            }
        ]

    def test_build_call_graph(self):
        source_code = """
def calculate_total(price, tax):
    return price + get_tax_amount(price, tax)

def get_tax_amount(price, tax):
    return price * tax

def process_order():
    total = calculate_total(100, 0.05)
    print("Done")
"""
        tree, _ = parse_code_to_ast(source_code, "Python")
        result = build_call_graph(tree, "Python")

        assert result == {
            "nodes": {
                "calculate_total": {
                    "qualified_name": "calculate_total",
                    "simple_name": "calculate_total",
                    "text": "def calculate_total(price, tax):\n    return price + get_tax_amount(price, tax)",
                    "fingerprint": "00000008060105fd3624134884412006ce880936",
                    "start_line": 2,
                    "end_line": 3,
                    "node_type": "function_definition",
                },
                "get_tax_amount": {
                    "qualified_name": "get_tax_amount",
                    "simple_name": "get_tax_amount",
                    "text": "def get_tax_amount(price, tax):\n    return price * tax",
                    "fingerprint": "000000058f0ee87d9669f20b1f473137b665bb20",
                    "start_line": 5,
                    "end_line": 6,
                    "node_type": "function_definition",
                },
                "process_order": {
                    "qualified_name": "process_order",
                    "simple_name": "process_order",
                    "text": 'def process_order():\n    total = calculate_total(100, 0.05)\n    print("Done")',
                    "fingerprint": "000000071c3e6902da5c2b322386eff29068e3e2",
                    "start_line": 8,
                    "end_line": 10,
                    "node_type": "function_definition",
                },
            },
            "edges": {
                "calculate_total": {"get_tax_amount"},
                "get_tax_amount": set(),
                "process_order": {"print", "calculate_total"},
            },
            "by_simple_name": {
                "calculate_total": {"calculate_total"},
                "get_tax_amount": {"get_tax_amount"},
                "process_order": {"process_order"},
            },
        }

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
        assert (
            len(functions) == 3
        )  # '__init__', 'process_payment', and 'calculate_discount'

        assert functions[0].type == "function_definition"
        first_func_text = functions[0].text.decode("utf-8")
        assert "def __init__" in first_func_text

        classes = extract_definitions(tree, "Python", kinds=("classes",))
        assert len(classes) == 2  # OrderManager, InventoryItem
        second_class_text = classes[1].text.decode("utf-8")
        assert "class InventoryItem" in second_class_text

    def test_extract_definitions_empty(self):
        tree, _ = parse_code_to_ast("", "Python")
        assert extract_definitions(tree, "Python", kinds=("functions",)) == []
        assert extract_definitions(tree, "Python", kinds=("functions",)) == []
        assert extract_definitions(None, "Python", kinds=("classes",)) == []
        assert extract_definitions(None, "Python", kinds=("classes",)) == []

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
        assert len(functions) == 2

        outer_function_name = qualified_name_from_index(functions[0], index)
        inner_function_name = qualified_name_from_index(functions[1], index)

        assert outer_function_name == "CoreService.Validator.validate_payload"
        assert inner_function_name == "global_utility"

    def test_get_qualified_classes(self):
        source_code = """
class FleetManagement:
    class DroneController:
        pass
        """
        tree, _ = parse_code_to_ast(source_code, "Python")
        index = collect_definitions(tree.root_node, "Python")

        classes = extract_definitions(tree, "Python", kinds=("classes",))
        assert len(classes) == 2

        outer_class_name = qualified_name_from_index(classes[0], index)
        inner_class_name = qualified_name_from_index(classes[1], index)

        assert outer_class_name == "FleetManagement"
        assert inner_class_name == "FleetManagement.DroneController"

    def test_classify_reachability(self):
        assert classify_reachability(None) == ReachabilityStatus.NOT_REACHABLE
        assert classify_reachability({}) == ReachabilityStatus.NOT_REACHABLE
        assert (
            classify_reachability(
                {"sym1": {"exact_match_fingerprint": "hash123", "called": True}}
            )
            == ReachabilityStatus.REACHABLE
        )

        assert (
            classify_reachability(
                {
                    "sym1": {
                        "called": True,
                        "reachable_from": ["main_function", "api_handler"],
                    }
                }
            )
            == ReachabilityStatus.REACHABLE
        )
        assert (
            classify_reachability({"sym1": {"defined": True, "called": False}})
            == ReachabilityStatus.POTENTIALLY_REACHABLE
        )
        assert (
            classify_reachability(
                {"sym1": {"exact_match_fingerprint": "hash123", "called": False}}
            )
            == ReachabilityStatus.POTENTIALLY_REACHABLE
        )
        assert (
            classify_reachability({"sym1": {"file_path": "src/vulnerable.py"}})
            == ReachabilityStatus.NOT_REACHABLE
        )

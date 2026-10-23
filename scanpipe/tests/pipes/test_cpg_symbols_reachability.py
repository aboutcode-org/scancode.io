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

import shutil
import sys
from pathlib import Path
from unittest import skipIf
from unittest.mock import PropertyMock
from unittest.mock import patch

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes import cpg
from scanpipe.pipes.reachability import PatchAnalyzer
from scanpipe.pipes.reachability import ReachabilityStatus

TEST_DATA_PYTHON = Path(__file__).parent.parent / "data" / "cpg_reachability" / "python"
TEST_DATA_JAVA = Path(__file__).parent.parent / "data" / "cpg_reachability" / "java"

COMMIT_HASH = "07ec0de1964b14bf085a1c9a27ece2b61ab6105c"
VCS_URL = "https://github.com/aboutcode-org/test"


class CleanSymbolNameTests(TestCase):
    def test_clean_symbol_name(self):
        self.assertEqual("app.run", cpg.clean_symbol_name("app.run()"))
        self.assertEqual(
            "app.ReportGenerator.__init__",
            cpg.clean_symbol_name("__init__()app.ReportGenerator"),
        )
        self.assertEqual("app.serve_report", cpg.clean_symbol_name("app.serve_report"))


class PathHelpersTests(TestCase):
    def test_clean_path(self):
        self.assertEqual("src/app.py", cpg.clean_path("src\\app.py"))
        self.assertEqual("src/app", cpg.clean_path("src/app/"))
        self.assertEqual("/srv/app.py", cpg.clean_path("file:///srv/app.py"))
        self.assertEqual("/srv/app.py", cpg.clean_path("file:/srv/app.py"))
        self.assertEqual("app.py", cpg.clean_path("app.py"))

    def test_paths_match(self):
        self.assertTrue(cpg.paths_match("app.py", "app.py"))
        self.assertTrue(cpg.paths_match("src/app.py", "app.py"))
        self.assertTrue(cpg.paths_match("app.py", "src/app.py"))
        self.assertTrue(cpg.paths_match("src\\app.py", "app.py"))
        self.assertFalse(cpg.paths_match("app.py", "app.py.bak"))
        self.assertFalse(cpg.paths_match("app.py", "other.py"))


class ClassifyReachabilityTests(TestCase):
    def test_classify_reachability(self):
        self.assertEqual(
            ReachabilityStatus.NOT_REACHABLE, cpg.classify_reachability({})
        )
        self.assertEqual(
            ReachabilityStatus.NOT_REACHABLE, cpg.classify_reachability(None)
        )

        matched = {"symbol1": {"is_reachable": True, "is_defined": True}}
        self.assertEqual(
            ReachabilityStatus.REACHABLE, cpg.classify_reachability(matched)
        )

        matched = {"symbol1": {"is_reachable": False, "is_defined": True}}
        self.assertEqual(ReachabilityStatus.UNKNOWN, cpg.classify_reachability(matched))

        matched = {
            "symbol1": {"is_reachable": False, "is_defined": True},
            "symbol2": {"is_reachable": True, "is_defined": True},
        }
        self.assertEqual(
            ReachabilityStatus.REACHABLE, cpg.classify_reachability(matched)
        )


@skipIf(sys.platform == "darwin", "Not supported on macOS")
class CPGQueryReachabilityPipesTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project1.codebase_path.mkdir(parents=True, exist_ok=True)
        export_path = self.project1.get_output_file_path("cpg_reachability", "json")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text("{}")

    def get_patch_symbols(
        self, data_dir, vulnerable_filename, fixed_filename, file_path
    ):
        """
        Patch symbols of the fixture commit, computed with the real
        analyzer from the real vulnerable/fixed file contents.
        """
        vulnerable_file = data_dir / vulnerable_filename
        fixed_file = data_dir / fixed_filename
        vulnerable_text = vulnerable_file.read_text()
        fixed_text = fixed_file.read_text()
        removed_lines, added_lines = PatchAnalyzer.compute_changed_lines(
            vulnerable_text, fixed_text
        )
        return PatchAnalyzer.analyze(
            vulnerable_text=vulnerable_text,
            fixed_text=fixed_text,
            removed_lines=removed_lines,
            added_lines=added_lines,
            file_path=file_path,
        )

    @patch("scanpipe.pipes.cpg.check_symbol_reachability")
    @patch("neo4j.GraphDatabase.driver")
    @patch("scanpipe.pipelines.cpg_symbols_reachability.run_command_safely")
    @patch(
        "scanpipe.pipelines.cpg_symbols_reachability.CPG_NEO4J_EXECUTABLE",
        "cpg-neo4j",
    )
    @patch("scanpipe.pipes.reachability.Repo")
    @patch("scanpipe.pipes.reachability.PatchAnalyzer.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_end_to_end_query_reachability_pipeline(
        self,
        mock_vulnerabilities,
        mock_collect_symbols,
        mock_repo,
        mock_run_command,
        mock_driver,
        mock_check_reachability,
    ):
        python_dir = self.project1.codebase_path / "python"
        shutil.copytree(TEST_DATA_PYTHON, python_dir)

        collect_and_create_codebase_resources(self.project1)
        for codebase_resource in self.project1.codebaseresources.all():
            if codebase_resource.path.endswith(".py"):
                codebase_resource.programming_language = "Python"
                codebase_resource.save()
        resource = self.project1.codebaseresources.get(path="python/main/app.py")

        def check_reachability(session, target_name, file_path=None):
            if "build_file_path" in target_name:
                return {
                    "symbol_name": target_name,
                    "is_defined": True,
                    "is_reachable": True,
                    "eog_path": [
                        "app.handle_request",
                        "app.serve_report.build_file_path",
                    ],
                }
            return {
                "symbol_name": target_name,
                "is_defined": False,
                "is_reachable": False,
                "eog_path": [],
            }

        mock_check_reachability.side_effect = check_reachability

        vulnerable, fixed, language = self.get_patch_symbols(
            TEST_DATA_PYTHON, "vuln-app.py", "fixed-app.py", "app.py"
        )
        self.assertEqual("Python", language)

        mock_collect_symbols.return_value = {
            language: {
                "vulnerable": {
                    f"app.py::{key}": meta for key, meta in vulnerable.items()
                },
                "fixed": {f"app.py::{key}": meta for key, meta in fixed.items()},
            },
        }
        mock_vulnerabilities.return_value = [
            {
                "advisory_uid": "pypi/app/PYSEC-0001",
                "fixed_in_patches": [{"vcs_url": VCS_URL, "commit_hash": COMMIT_HASH}],
            }
        ]

        run = self.project1.add_pipeline("cpg_symbols_reachability")
        pipeline = run.make_pipeline_instance()
        pipeline.execute()

        run.refresh_from_db()
        mock_run_command.assert_called_once()
        resource.refresh_from_db()
        results = (resource.extra_data or {}).get("symbols_reachability") or []
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["is_reachable"], ReachabilityStatus.REACHABLE.value)
        self.assertEqual(results[0]["advisory_uids"], ["pypi/app/PYSEC-0001"])
        self.assertIn(
            "serve_report.build_file_path",
            [detail["symbol_name"] for detail in results[0]["tool_details"]],
        )

        build_file_path_calls = [
            call_args
            for call_args in mock_check_reachability.call_args_list
            if "build_file_path" in call_args.args[1]
        ]
        self.assertEqual(1, len(build_file_path_calls))
        self.assertEqual("app.py", build_file_path_calls[0].args[2])

        symbol_details = [
            detail
            for detail in results[0]["tool_details"]
            if detail["symbol_name"] == "serve_report.build_file_path"
        ]
        self.assertEqual(1, len(symbol_details))
        self.assertEqual(
            ["app.handle_request", "app.serve_report.build_file_path"],
            symbol_details[0]["eog_path"],
        )

    @patch("scanpipe.pipes.cpg.check_symbol_reachability")
    @patch("neo4j.GraphDatabase.driver")
    @patch("scanpipe.pipelines.cpg_symbols_reachability.run_command_safely")
    @patch(
        "scanpipe.pipelines.cpg_symbols_reachability.CPG_NEO4J_EXECUTABLE",
        "cpg-neo4j",
    )
    @patch("scanpipe.pipes.reachability.Repo")
    @patch("scanpipe.pipes.reachability.PatchAnalyzer.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_end_to_end_query_reachability_pipeline_java(
        self,
        mock_vulnerabilities,
        mock_collect_symbols,
        mock_repo,
        mock_run_command,
        mock_driver,
        mock_check_reachability,
    ):
        java_dir = self.project1.codebase_path / "java"
        shutil.copytree(TEST_DATA_JAVA, java_dir)

        collect_and_create_codebase_resources(self.project1)
        for codebase_resource in self.project1.codebaseresources.all():
            if codebase_resource.path.endswith(".java"):
                codebase_resource.programming_language = "Java"
                codebase_resource.save()
        resource = self.project1.codebaseresources.get(path="java/main/app.java")

        def check_reachability(session, target_name, file_path=None):
            if "buildFilePath" in target_name:
                return {
                    "symbol_name": target_name,
                    "is_defined": True,
                    "is_reachable": True,
                    "eog_path": ["App.serveReport", "App.buildFilePath"],
                }
            return {
                "symbol_name": target_name,
                "is_defined": False,
                "is_reachable": False,
                "eog_path": [],
            }

        mock_check_reachability.side_effect = check_reachability

        vulnerable, fixed, language = self.get_patch_symbols(
            TEST_DATA_JAVA, "vuln-app.java", "fixed-app.java", "app.java"
        )
        self.assertEqual("Java", language)

        mock_collect_symbols.return_value = {
            language: {
                "vulnerable": {
                    f"app.java::{key}": meta for key, meta in vulnerable.items()
                },
                "fixed": {f"app.java::{key}": meta for key, meta in fixed.items()},
            },
        }
        mock_vulnerabilities.return_value = [
            {
                "advisory_uid": "pypi/app/JAVA-0001",
                "fixed_in_patches": [{"vcs_url": VCS_URL, "commit_hash": COMMIT_HASH}],
            }
        ]

        run = self.project1.add_pipeline("cpg_symbols_reachability")
        pipeline = run.make_pipeline_instance()
        pipeline.execute()

        mock_run_command.assert_called_once()
        resource.refresh_from_db()
        run.refresh_from_db()
        results = (resource.extra_data or {}).get("symbols_reachability") or []
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["is_reachable"], ReachabilityStatus.REACHABLE.value)
        self.assertEqual(results[0]["advisory_uids"], ["pypi/app/JAVA-0001"])
        self.assertIn("app.java::App.buildFilePath", results[0]["vulnerable_symbols"])

        build_file_path_calls = [
            call_args
            for call_args in mock_check_reachability.call_args_list
            if "buildFilePath" in call_args.args[1]
        ]
        self.assertEqual(1, len(build_file_path_calls))
        self.assertEqual("app.java", build_file_path_calls[0].args[2])

        symbol_details = [
            detail
            for detail in results[0]["tool_details"]
            if detail["symbol_name"] == "App.buildFilePath"
        ]
        self.assertEqual(1, len(symbol_details))
        self.assertEqual(
            ["App.serveReport", "App.buildFilePath"],
            symbol_details[0]["eog_path"],
        )

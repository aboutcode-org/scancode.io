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
from scanpipe.pipes.reachability import PatchAnalyzer
from scanpipe.pipes.reachability import ReachabilityStatus

TEST_DATA_PYTHON = Path(__file__).parent.parent / "data" / "cpg_reachability" / "python"
TEST_DATA_JAVA = Path(__file__).parent.parent / "data" / "cpg_reachability" / "java"

COMMIT_HASH = "07ec0de1964b14bf085a1c9a27ece2b61ab6105c"
VCS_URL = "https://github.com/aboutcode-org/test"


@skipIf(sys.platform == "darwin", "Not supported on macOS")
class CPGQueryReachabilityPipesTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project1.codebase_path.mkdir(parents=True, exist_ok=True)

    def copy_cpg_export(self, cpg_fixture):
        """
        Copy the fixture CPG export to the output file path where the
        cpg_symbols_reachability pipeline expects it.
        """
        export_path = self.project1.get_output_file_path("cpg_reachability", "json")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cpg_fixture, export_path)
        return export_path

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

    @patch("scanpipe.pipelines.cpg_symbols_reachability.run_command_safely")
    @patch(
        "scanpipe.pipelines.cpg_symbols_reachability.CPG_NEO4J_EXECUTABLE", "cpg-neo4j"
    )
    @patch("scanpipe.pipes.reachability.Repo")
    @patch("scanpipe.pipes.reachability.PatchAnalyzer.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_end_to_end_query_reachability_pipeline(
        self, mock_vulnerabilities, mock_collect_symbols, mock_repo, mock_run_command
    ):
        python_dir = self.project1.codebase_path / "python"
        shutil.copytree(TEST_DATA_PYTHON, python_dir)

        collect_and_create_codebase_resources(self.project1)
        for codebase_resource in self.project1.codebaseresources.all():
            if codebase_resource.path.endswith(".py"):
                codebase_resource.programming_language = "Python"
                codebase_resource.save()
        resource = self.project1.codebaseresources.get(path="python/main/app.py")

        self.copy_cpg_export(python_dir / "python-cpg.json")

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

    @patch("scanpipe.pipelines.cpg_symbols_reachability.run_command_safely")
    @patch(
        "scanpipe.pipelines.cpg_symbols_reachability.CPG_NEO4J_EXECUTABLE", "cpg-neo4j"
    )
    @patch(
        "scanpipe.pipelines.cpg_symbols_reachability.CPGTool.supported_languages",
        ("Python", "Java"),
    )
    @patch("scanpipe.pipes.reachability.Repo")
    @patch("scanpipe.pipes.reachability.PatchAnalyzer.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_end_to_end_query_reachability_pipeline_java(
        self, mock_vulnerabilities, mock_collect_symbols, mock_repo, mock_run_command
    ):
        java_dir = self.project1.codebase_path / "java"
        shutil.copytree(TEST_DATA_JAVA, java_dir)

        collect_and_create_codebase_resources(self.project1)
        for codebase_resource in self.project1.codebaseresources.all():
            if codebase_resource.path.endswith(".java"):
                codebase_resource.programming_language = "Java"
                codebase_resource.save()
        resource = self.project1.codebaseresources.get(path="java/main/app.java")

        self.copy_cpg_export(java_dir / "java-cpg.json")
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

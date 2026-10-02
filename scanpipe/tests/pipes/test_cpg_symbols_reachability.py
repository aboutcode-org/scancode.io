import json
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

    def get_real_patch_symbols(
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
    @patch("scanpipe.pipelines.cpg_symbols_reachability.CPG_NEO4J_EXECUTABLE", "cpg-neo4j")
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

        export_path = self.project1.get_output_file_path("cpg_reachability", "json")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(python_dir / "python-cpg.json", export_path)

        vulnerable, fixed, language = self.get_real_patch_symbols(
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
    @patch("scanpipe.pipelines.cpg_symbols_reachability.CPG_NEO4J_EXECUTABLE", "cpg-neo4j")
    @patch("scanpipe.pipelines.cpg_symbols_reachability.CPGTool.supported_language", ("Python", "Java"))
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

        export_path = self.project1.get_output_file_path("cpg_reachability", "json")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": 1,
                            "labels": ["FileNode"],
                            "properties": {"name": "app.java", "path": "java/main/app.java"},
                        },
                        {
                            "id": 2,
                            "labels": ["ClassDeclaration"],
                            "properties": {"name": "App", "fullName": "App"},
                        },
                        {
                            "id": 3,
                            "labels": ["MethodDeclaration"],
                            "properties": {"name": "serveReport", "fullName": "App.serveReport"},
                        },
                        {
                            "id": 4,
                            "labels": ["MethodDeclaration"],
                            "properties": {"name": "buildFilePath", "fullName": "App.buildFilePath"},
                        },
                    ],
                    "edges": [
                        {"startNode": 1, "endNode": 2, "type": "CONTAINS"},
                        {"startNode": 2, "endNode": 3, "type": "DECLARATIONS"},
                        {"startNode": 2, "endNode": 4, "type": "DECLARATIONS"},
                        {"startNode": 3, "endNode": 4, "type": "EOG"},
                        {"startNode": 3, "endNode": 4, "type": "INVOKES"},
                    ],
                }
            )
        )

        vulnerable, fixed, language = self.get_real_patch_symbols(
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
        results = (resource.extra_data or {}).get("symbols_reachability") or []
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["is_reachable"], ReachabilityStatus.REACHABLE.value)
        self.assertEqual(results[0]["advisory_uids"], ["pypi/app/JAVA-0001"])
        self.assertIn("app.java::App.buildFilePath", results[0]["vulnerable_symbols"])

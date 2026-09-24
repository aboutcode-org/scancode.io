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
from scanpipe.pipes.cpg import ResourcePatchMatcher
from scanpipe.pipes.reachability import PatchAnalyzer
from scanpipe.pipes.reachability import ReachabilityStatus

TEST_DATA = Path(__file__).parent.parent / "data" / "cpg_reachability" / "python"
COMMIT_HASH = "07ec0de1964b14bf085a1c9a27ece2b61ab6105c"
VCS_URL = "https://github.com/aboutcode-org/test"


@skipIf(sys.platform == "darwin", "Not supported on macOS")
class CPGQueryReachabilityPipesTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project1.codebase_path.mkdir(parents=True, exist_ok=True)

    def get_real_patch_symbols(self):
        """
        Patch symbols of the fixture commit, computed with the real
        analyzer from the real vulnerable/fixed file contents.
        """
        vulnerable_text = (TEST_DATA / "vuln-app.py").read_text()
        fixed_text = (TEST_DATA / "fixed-app.py").read_text()
        removed_lines, added_lines = PatchAnalyzer.compute_changed_lines(
            vulnerable_text, fixed_text
        )
        return PatchAnalyzer.analyze(
            vulnerable_text=vulnerable_text,
            fixed_text=fixed_text,
            removed_lines=removed_lines,
            added_lines=added_lines,
            file_path="app.py",
        )

    @staticmethod
    def get_symbol_key(symbols, ending="build_file_path"):
        """
        The analyzer's key for the vulnerable helper, tolerating
        qualified-name variations in the real extraction.
        """
        for key in symbols:
            if key.endswith(ending):
                return key
        return None

    @patch("scanpipe.pipes.cpg.run_command_safely")
    @patch("scanpipe.pipes.cpg.CPG_NEO4J_EXECUTABLE", "cpg-neo4j")
    @patch("scanpipe.pipes.reachability.Repo")
    @patch("scanpipe.pipes.reachability.PatchAnalyzer.collect_patch_symbols")
    @patch.object(Project, "package_vulnerabilities", new_callable=PropertyMock)
    def test_end_to_end_query_reachability_pipeline(
        self, mock_vulnerabilities, mock_collect_symbols, mock_repo, mock_run_command
    ):
        python_dir = self.project1.codebase_path / "python"
        shutil.copytree(TEST_DATA, python_dir)

        collect_and_create_codebase_resources(self.project1)
        for codebase_resource in self.project1.codebaseresources.all():
            if codebase_resource.path.endswith(".py"):
                codebase_resource.programming_language = "Python"
                codebase_resource.save()
        resource = self.project1.codebaseresources.get(path="python/main/app.py")

        export_path = self.project1.get_output_file_path("cpg_reachability", "json")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(python_dir / "python-cpg.json", export_path)

        vulnerable, fixed, language = self.get_real_patch_symbols()
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

        mock_collect_symbols.assert_called_once()
        mock_run_command.assert_called_once()
        resource.refresh_from_db()
        results = (resource.extra_data or {}).get("symbols_reachability") or []
        self.assertEqual(
            results,
            [
                {
                    "patch": {
                        "vcs_url": "https://github.com/aboutcode-org/test",
                        "commit_hash": "07ec0de1964b14bf085a1c9a27ece2b61ab6105c",
                    },
                    "is_reachable": ReachabilityStatus.REACHABLE.value,
                    "tool_details": [
                        {
                            "eog_path": [
                                "app.handle_request",
                                "app.serve_report",
                                "app.build_file_path",
                            ],
                            "is_defined": True,
                            "symbol_name": "serve_report.build_file_path",
                            "is_reachable": True,
                        },
                        {
                            "eog_path": ["app.handle_request", "app.serve_report"],
                            "is_defined": True,
                            "symbol_name": "serve_report",
                            "is_reachable": True,
                        },
                    ],
                    "advisory_uids": ["pypi/app/PYSEC-0001"],
                    "fixed_symbols": [
                        "app.py::serve_report",
                        "app.py::serve_report.build_file_path",
                    ],
                    "vulnerable_symbols": [
                        "app.py::serve_report",
                        "app.py::serve_report.build_file_path",
                    ],
                }
            ],
        )

    def test_resource_patch_matcher(self):
        graph = json.loads((TEST_DATA / "python-cpg.json").read_text())
        vulnerable, _, _ = self.get_real_patch_symbols()
        build_key = self.get_symbol_key(vulnerable)
        matcher = ResourcePatchMatcher(graph)
        results = matcher.match(vulnerable, file_path="python/main/app.py")
        detail = results.get(build_key)
        self.assertEqual(
            detail,
            {
                "symbol_name": "serve_report.build_file_path",
                "is_defined": True,
                "is_reachable": True,
                "eog_path": [
                    "app.handle_request",
                    "app.serve_report",
                    "app.build_file_path",
                ],
            },
        )

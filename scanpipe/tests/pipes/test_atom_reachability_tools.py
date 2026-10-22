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
import shutil
from pathlib import Path

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes.atom import ReachablesMatcher
from scanpipe.pipes.atom import UsagesMatcher
from scanpipe.pipes.atom import collect_and_match_resources
from scanpipe.pipes.atom import normalize_file_path
from scanpipe.pipes.atom import normalize_symbol_name
from scanpipe.pipes.reachability import ReachabilityStatus

TEST_DATA_PYTHON = (
    Path(__file__).parent.parent / "data" / "atom_reachability" / "python"
)

USAGES_JSON = "atom_reachability.python.usages.slices.json"
REACHABLES_JSON = "atom_reachability.python.reachables.slices.json"

COMMIT_HASH = "07ec0de1964b14bf085a1c9a27ece2b61ab6105c"
VCS_URL = "https://github.com/aboutcode-org/test"


class UsagesMatcherTests(TestCase):
    """Match patch symbols against the real atom ``usages`` slice for ``app.py``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slices = json.loads((TEST_DATA_PYTHON / USAGES_JSON).read_text())
        cls.matcher = UsagesMatcher(cls.slices)
        cls.names = cls.matcher.by_file.get("app.py") or set()

    def test_matches_expected_app_py_symbols(self):
        self.assertIn("app.py", self.matcher.by_file)

        self.assertIn("app.handle_request.build_file_path", self.names)
        self.assertIn("app.handle_request", self.names)
        self.assertIn("app.ReportGenerator", self.names)
        self.assertIn("app.unrelated_top_level_function", self.names)

        self.assertIn(
            "build_file_path",
            self.matcher.match_symbols({"build_file_path"}, "app.py"),
        )
        self.assertIn(
            "handle_request.build_file_path",
            self.matcher.match_symbols({"handle_request.build_file_path"}, "app.py"),
        )
        self.assertIn(
            "app.py::handle_request.build_file_path",
            self.matcher.match_symbols(
                {"app.py::handle_request.build_file_path"}, "app.py"
            ),
        )
        self.assertIn(
            "app.py::ReportGenerator",
            self.matcher.match_symbols({"app.py::ReportGenerator"}, "app.py"),
        )
        self.assertIn(
            "app.py::ReportGenerator.__init__",
            self.matcher.match_symbols({"app.py::ReportGenerator.__init__"}, "app.py"),
        )
        self.assertIn(
            "build_file_path",
            self.matcher.match_symbols({"build_file_path"}, "python/app.py"),
        )
        self.assertFalse(
            self.matcher.match_symbols({"symbol_that_does_not_exist"}, "app.py")
        )


class ReachablesMatcherTests(TestCase):
    """Match patch symbols against the real atom ``reachables`` slice for ``app.py``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slices = json.loads((TEST_DATA_PYTHON / REACHABLES_JSON).read_text())
        cls.matcher = ReachablesMatcher(cls.slices)

    def test_matches_expected_app_py_symbols(self):
        self.assertIn("app.py", self.matcher.by_file)

        self.assertIn(
            "build_file_path",
            self.matcher.match_symbols({"build_file_path"}, "app.py"),
        )
        self.assertIn(
            "handle_request.build_file_path",
            self.matcher.match_symbols({"handle_request.build_file_path"}, "app.py"),
        )
        self.assertIn(
            "build_file_path",
            self.matcher.match_symbols({"build_file_path"}, "python/app.py"),
        )
        self.assertFalse(
            self.matcher.match_symbols({"symbol_that_does_not_exist"}, "app.py")
        )

        orphan = ReachablesMatcher(
            [{"flows": [{"parentMethodName": "x"}], "purls": []}]
        )
        self.assertEqual(0, orphan.file_count)


class NormalizeTests(TestCase):
    """``normalize_file_path`` and ``normalize_symbol_name``."""

    def test_normalize_file_path(self):
        self.assertEqual("app.py", normalize_file_path("app.py"))
        self.assertEqual("python/app.py", normalize_file_path("python/app.py"))
        self.assertEqual("app.py", normalize_file_path("./app.py"))
        self.assertEqual("app.py", normalize_file_path("./././app.py"))
        self.assertEqual("pkg/app.py", normalize_file_path("./pkg/app.py"))
        self.assertEqual("pkg/app.py", normalize_file_path("/pkg/app.py"))
        self.assertEqual("pkg/app.py", normalize_file_path("//pkg/app.py"))
        self.assertEqual("pkg/app.py", normalize_file_path(r"pkg\app.py"))
        self.assertEqual("pkg/app.py", normalize_file_path(r".\pkg\app.py"))
        self.assertEqual("", normalize_file_path(""))
        self.assertEqual("", normalize_file_path(None))

    def test_normalize_symbol_name(self):
        self.assertEqual("build_file_path", normalize_symbol_name("build_file_path"))
        self.assertEqual(
            "serve_report.build_file_path",
            normalize_symbol_name("serve_report.build_file_path"),
        )
        self.assertEqual(
            "app.handle_request.build_file_path",
            normalize_symbol_name("app.py:<module>.handle_request.build_file_path"),
        )
        self.assertEqual(
            "pkg.app.ReportGenerator.__init__",
            normalize_symbol_name("pkg/app.py:<module>.ReportGenerator.__init__"),
        )

        self.assertEqual(
            "ReportGenerator.__init__",
            normalize_symbol_name("app.py::ReportGenerator.__init__"),
        )

        self.assertEqual(
            "app.ReportGenerator.__init__",
            normalize_symbol_name("app.py:<module>.ReportGenerator<fakeNew>.__init__"),
        )
        self.assertEqual(
            "app.ReportGenerator.__init__",
            normalize_symbol_name(
                "app.py:<module>.ReportGenerator<metaClassAdapter>.__init__"
            ),
        )
        self.assertEqual(
            "app.ReportGenerator.__init__",
            normalize_symbol_name(
                "app.py:<module>.ReportGenerator<metaClassCallHandler>.__init__"
            ),
        )
        self.assertEqual(
            "app.ReportGenerator",
            normalize_symbol_name("app.py:<module>.ReportGenerator.<body>"),
        )
        self.assertEqual("def ", normalize_symbol_name("def <body>"))

        self.assertEqual("", normalize_symbol_name("<module>"))
        self.assertEqual("", normalize_symbol_name("<body>"))
        self.assertEqual("", normalize_symbol_name("<fakeNew>"))
        self.assertEqual("", normalize_symbol_name("<metaClassCallHandler>"))

        self.assertEqual("", normalize_symbol_name("<operator>.equals"))
        self.assertEqual("", normalize_symbol_name("<operators>.equals"))
        self.assertEqual("", normalize_symbol_name("<operator>"))
        self.assertEqual("", normalize_symbol_name("<operator>.assignment"))
        self.assertEqual("", normalize_symbol_name("<operator>.alloc"))


class CollectAndMatchResourcesTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Analysis")
        self.project.codebase_path.mkdir(parents=True, exist_ok=True)

    def _prepare_resources(self):
        shutil.copytree(TEST_DATA_PYTHON, self.project.codebase_path / "python")
        collect_and_create_codebase_resources(self.project)
        for resource in self.project.codebaseresources.all():
            if resource.path.endswith(".py"):
                resource.programming_language = "Python"
                resource.save()

    def _load_atom_slices(self):
        """Load both atom slice fixtures: usages and reachables."""
        usages = json.loads((TEST_DATA_PYTHON / USAGES_JSON).read_text())
        reachables = json.loads((TEST_DATA_PYTHON / REACHABLES_JSON).read_text())
        return usages, reachables

    def _run_atom(
        self,
        resources,
        usages_slices,
        reachables_slices,
        vulnerable,
        fixed,
        advisory_uid,
    ):
        patch_symbols = {
            COMMIT_HASH: {
                "Python": {
                    "vulnerable": {
                        f"app.py::{key}": meta for key, meta in vulnerable.items()
                    },
                    "fixed": {f"app.py::{key}": meta for key, meta in fixed.items()},
                }
            }
        }
        patches = [
            {
                "vcs_url": VCS_URL,
                "commit_hash": COMMIT_HASH,
                "advisory_uids": [advisory_uid],
            }
        ]

        collect_and_match_resources(
            tool_name="atom",
            patches=patches,
            patch_symbols=patch_symbols,
            usages_slices=usages_slices,
            reachables_slices=reachables_slices,
            candidate_resources=resources,
        )

        for resource in resources:
            resource.refresh_from_db()
        return resources

    @staticmethod
    def _get_reports(resource):
        return (resource.extra_data or {}).get("symbols_reachability") or []

    def test_build_file_path_reachable_through_reachables_slice(self):
        """
        ``build_file_path`` is indexed in the real usages slice and marked
        reachable by the real reachables slice, so the report is REACHABLE.
        """
        self._prepare_resources()
        resource = self.project.codebaseresources.get(path="python/app.py")
        self.assertEqual("Python", resource.programming_language)

        usages_slices, reachables_slices = self._load_atom_slices()
        self.assertTrue(usages_slices.get("objectSlices"))
        self.assertTrue(reachables_slices)

        vulnerable = {
            "build_file_path": {
                "qualified_name": "handle_request.build_file_path",
                "text": "return os.path.join(generator.base_dir, filename)",
            }
        }
        fixed = {
            "build_file_path": {
                "qualified_name": "handle_request.build_file_path",
                "text": (
                    "return os.path.join("
                    "generator.base_dir, os.path.basename(filename))"
                ),
            }
        }

        self._run_atom(
            [resource],
            usages_slices,
            reachables_slices,
            vulnerable,
            fixed,
            advisory_uid="pypi/app/PYSEC-0003",
        )

        results = self._get_reports(resource)
        self.assertEqual(1, len(results))
        result = results[0]

        self.assertEqual(["pypi/app/PYSEC-0003"], result["advisory_uids"])
        self.assertEqual(COMMIT_HASH, result["patch"]["commit_hash"])
        self.assertEqual(VCS_URL, result["patch"]["vcs_url"])

        symbol_key = "app.py::build_file_path"
        self.assertEqual([symbol_key], result["vulnerable_symbols"])
        self.assertEqual([symbol_key], result["fixed_symbols"])
        self.assertEqual(ReachabilityStatus.REACHABLE.value, result["is_reachable"])

        self.assertEqual(1, len(result["tool_details"]))
        detail = result["tool_details"][0]

        self.assertEqual(symbol_key, detail["symbol_name"])
        self.assertTrue(detail["in_usage"])
        self.assertTrue(detail["in_reachable"])

        self.assertTrue(detail["calls"])
        call_names = {call["call_name"] for call in detail["calls"]}
        self.assertIn("build_file_path", call_names)
        self.assertIn("open", call_names)
        self.assertNotIn("is_test", result)

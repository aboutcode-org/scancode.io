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

from django.test import SimpleTestCase
from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes.atom import classify_reachability
from scanpipe.pipes.atom import collect_and_match_resources
from scanpipe.pipes.atom import ResourcePatchMatcher
from scanpipe.pipes.reachability import ReachabilityStatus

TEST_DATA_PYTHON = (
    Path(__file__).parent.parent / "data" / "atom_reachability" / "python"
)
SLICES_JSON = "atom_reachability.python.usages.slices.json"

COMMIT_HASH = "07ec0de1964b14bf085a1c9a27ece2b61ab6105c"
VCS_URL = "https://github.com/aboutcode-org/test"


class ClassifyReachabilityTests(SimpleTestCase):
    """Unit tests for the atom reachability classifier.

    ``classify_reachability`` is a pure function of occurrence data
    (``is_call`` / ``is_reachable``); it makes no production-vs-test
    distinction and occurrences carry no ``is_test`` field.
    """

    def test_empty_inputs_are_not_reachable(self):
        self.assertEqual(
            ReachabilityStatus.NOT_REACHABLE, classify_reachability({}, {})
        )
        self.assertEqual(
            ReachabilityStatus.NOT_REACHABLE, classify_reachability(None, None)
        )

    def test_reachable_when_vulnerable_symbol_is_called(self):
        vuln = {"sym": [{"is_call": True, "is_reachable": False}]}
        self.assertEqual(
            ReachabilityStatus.REACHABLE, classify_reachability(vuln, {})
        )

    def test_reachable_when_vulnerable_symbol_flagged_reachable(self):
        vuln = {"sym": [{"is_call": False, "is_reachable": True}]}
        self.assertEqual(
            ReachabilityStatus.REACHABLE, classify_reachability(vuln, {})
        )

    def test_unknown_when_defined_but_uncalled(self):
        vuln = {"sym": [{"is_call": False, "is_reachable": False}]}
        self.assertEqual(
            ReachabilityStatus.UNKNOWN, classify_reachability(vuln, {})
        )

    def test_not_reachable_when_only_fixed_symbols_match(self):
        fixed = {"sym": [{"is_call": True, "is_reachable": True}]}
        self.assertEqual(
            ReachabilityStatus.NOT_REACHABLE, classify_reachability({}, fixed)
        )

    def test_fixed_details_do_not_change_verdict(self):
        vuln = {"sym": [{"is_call": False, "is_reachable": False}]}
        fixed = {"sym": [{"is_call": True, "is_reachable": True}]}
        self.assertEqual(
            ReachabilityStatus.UNKNOWN, classify_reachability(vuln, fixed)
        )


class ResourcePatchMatcherTests(SimpleTestCase):
    """Unit tests for atom's patch-symbol matcher.

    Includes regressions for the ``path::QualifiedName`` keys produced by the
    patch analyzer, e.g.
    ``b2sdk/account_info/sqlite_account_info.py::SqliteAccountInfo._create_database``.
    """

    @staticmethod
    def _make_index(*names, file_name="python/app.py"):
        return {
            "objectSlices": [
                {
                    "fileName": file_name,
                    "name": name,
                    "reachable": False,
                    "usages": [],
                }
                for name in names
            ],
            "userDefinedTypes": [],
        }

    def test_matches_bare_symbol_name(self):
        matcher = ResourcePatchMatcher(self._make_index("build_file_path"))
        self.assertIn("build_file_path", matcher.match({"build_file_path": {}}))

    def test_matches_dotted_symbol_name(self):
        matcher = ResourcePatchMatcher(
            self._make_index("serve_report.build_file_path")
        )
        matched = matcher.match({"serve_report.build_file_path": {}})
        self.assertIn("serve_report.build_file_path", matched)

    def test_matches_path_prefixed_method_symbol(self):
        """Regression: ``path::QualifiedName`` method keys must match."""
        matcher = ResourcePatchMatcher(
            self._make_index("serve_report.build_file_path")
        )
        symbol = "app.py::serve_report.build_file_path"
        self.assertIn(symbol, matcher.match({symbol: {}}))

    def test_matches_path_prefixed_class_symbol(self):
        """Regression: ``path::Class`` (no dot) must match a bare class name."""
        matcher = ResourcePatchMatcher(self._make_index("ReportGenerator"))
        symbol = "app.py::ReportGenerator"
        self.assertIn(symbol, matcher.match({symbol: {}}))

    def test_no_match_for_unrelated_symbol(self):
        matcher = ResourcePatchMatcher(self._make_index("unrelated_top_level_function"))
        self.assertFalse(matcher.match({"build_file_path": {}}))

    def test_occurrence_has_no_is_test_field(self):
        """Occurrences produced by the matcher must not carry ``is_test``."""
        matcher = ResourcePatchMatcher(self._make_index("some_function"))
        matched = matcher.match({"some_function": {}})
        occurrence = matched["some_function"][0]
        self.assertNotIn("is_test", occurrence)
        self.assertIn("is_call", occurrence)
        self.assertIn("is_reachable", occurrence)
        self.assertIn("names", occurrence)
        self.assertIn("fileName", occurrence)


class CollectAndMatchResourcesTests(TestCase):
    """End-to-end tests for atom's ``collect_and_match_resources`` entry point.

    Each test builds a real Django project from the ``atom_reachability/python``
    fixture, feeds the atom matcher the real ``objectSlices``/``userDefinedTypes``
    captured in ``atom_reachability.python.usages.slices.json``, and asserts on
    the report persisted by ``save_resource_reachability_report``.

    No candidate is skipped based on its path: files under ``test``/``tests``
    directories are analyzed exactly like production files.
    """

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
        """Load the real atom slices fixture produced for ``app.py``."""
        return json.loads((TEST_DATA_PYTHON / SLICES_JSON).read_text())

    def _run_atom(self, resources, resource_indexes, vulnerable, fixed, advisory_uid):
        patch_symbols = {
            COMMIT_HASH: {
                "Python": {
                    "vulnerable": {
                        f"app.py::{key}": meta
                        for key, meta in vulnerable.items()
                    },
                    "fixed": {
                        f"app.py::{key}": meta
                        for key, meta in fixed.items()
                    },
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
            resource_indexes=resource_indexes,
            candidate_resources=resources,
        )

        for resource in resources:
            resource.refresh_from_db()
        return resources

    @staticmethod
    def _get_reports(resource):
        return (resource.extra_data or {}).get("symbols_reachability") or []

    def test_python_path_traversal_reachable_via_nested_call(self):
        """``build_file_path`` (path traversal) is reachable through
        ``handle_request`` -> ``serve_report`` -> ``build_file_path`` using
        the real atom slices fixture.
        """
        self._prepare_resources()
        resource = self.project.codebaseresources.get(path="python/app.py")
        self.assertEqual("Python", resource.programming_language)

        resource_indexes = self._load_atom_slices()
        self.assertIn("objectSlices", resource_indexes)
        self.assertTrue(resource_indexes["objectSlices"])

        vulnerable = {
            "build_file_path": {
                "qualified_name": "serve_report.build_file_path",
                "text": "return os.path.join(generator.base_dir, filename)",
            }
        }
        fixed = {
            "build_file_path": {
                "qualified_name": "serve_report.build_file_path",
                "text": (
                    "return os.path.join("
                    "generator.base_dir, os.path.basename(filename))"
                ),
            }
        }

        self._run_atom(
            [resource],
            resource_indexes,
            vulnerable,
            fixed,
            advisory_uid="pypi/app/PYSEC-0003",
        )

        results = self._get_reports(resource)
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual(ReachabilityStatus.REACHABLE.value, result["is_reachable"])
        self.assertEqual(["pypi/app/PYSEC-0003"], result["advisory_uids"])
        self.assertEqual(COMMIT_HASH, result["patch"]["commit_hash"])
        self.assertEqual(VCS_URL, result["patch"]["vcs_url"])
        self.assertEqual("atom", result["tool_name"])

        symbol_key = "app.py::build_file_path"
        self.assertIn(symbol_key, result["vulnerable_symbols"])
        self.assertIn(symbol_key, result["tool_details"])

        occurrences = result["tool_details"][symbol_key]
        self.assertTrue(occurrences)
        self.assertTrue(
            any(o["is_call"] or o["is_reachable"] for o in occurrences),
            f"expected a live call occurrence, got {occurrences!r}",
        )
        for occurrence in occurrences:
            self.assertNotIn("is_test", occurrence)
            self.assertEqual("app.py", occurrence["fileName"])
            self.assertTrue(
                any("build_file_path" in name for name in occurrence["names"])
            )

    def test_unrelated_top_level_function_is_not_reported(self):
        """A symbol that is not in the patch symbols is never matched.

        ``unrelated_top_level_function`` exists in the fixture but is not part
        of the patch, so it must not appear in ``tool_details``.
        """
        self._prepare_resources()
        resource = self.project.codebaseresources.get(path="python/app.py")

        resource_indexes = self._load_atom_slices()

        self._run_atom(
            [resource],
            resource_indexes,
            vulnerable={
                "build_file_path": {
                    "qualified_name": "serve_report.build_file_path",
                    "text": "return os.path.join(generator.base_dir, filename)",
                }
            },
            fixed={},
            advisory_uid="pypi/app/PYSEC-0004",
        )

        results = self._get_reports(resource)
        self.assertEqual(1, len(results))
        details = results[0]["tool_details"]
        self.assertNotIn(
            "app.py::unrelated_top_level_function", details
        )

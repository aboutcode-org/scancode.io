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
from unittest import mock

from django.test import TestCase

from scanpipe.models import OriginMatch
from scanpipe.pipes import scanoss
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_file


class ScanOSSPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "find-origins"

    def setUp(self):
        self.project1 = make_project()
        scanoss_results_location = self.data / "scanoss-results.json"
        self.scanoss_results = json.loads(scanoss_results_location.read_text())

    def test_scanpipe_pipes_scanoss_is_configured(self):
        with mock.patch.object(scanoss, "SCANOSS_URL", ""):
            self.assertFalse(scanoss.is_configured())

        with mock.patch.object(scanoss, "SCANOSS_URL", "https://api.osskb.org"):
            self.assertTrue(scanoss.is_configured())

    @mock.patch("shutil.which")
    def test_scanpipe_pipes_scanoss_get_uvx_location(self, mock_which):
        mock_which.return_value = "/usr/bin/uvx"
        self.assertEqual("/usr/bin/uvx", scanoss.get_uvx_location())
        mock_which.assert_called_once_with("uvx")

    @mock.patch("scanpipe.pipes.scanoss.run_command_safely")
    @mock.patch("scanpipe.pipes.scanoss.get_uvx_location")
    def test_scanpipe_pipes_scanoss_scan_codebase(
        self, mock_get_uvx_location, mock_run_command_safely
    ):
        mock_get_uvx_location.return_value = "/usr/bin/uvx"
        mock_run_command_safely.return_value = ""

        with (
            mock.patch.object(scanoss, "SCANOSS_URL", "https://api.osskb.org"),
            mock.patch.object(scanoss, "SCANOSS_API_KEY", "secret-key"),
        ):
            scanoss.scan_codebase("/codebase", "/output/scanoss.json")

        command_args = mock_run_command_safely.call_args.args[0]
        scanoss_env = mock_run_command_safely.call_args.kwargs["env"]
        self.assertEqual("/usr/bin/uvx", command_args[0])
        self.assertIn(f"--from=scanoss=={scanoss.SCANOSS_PY_VERSION}", command_args)
        self.assertIn("--apiurl=https://api.osskb.org", command_args)
        self.assertIn("--flags=256", command_args)
        self.assertEqual(
            ["--output=/output/scanoss.json", "/codebase"], command_args[-2:]
        )
        self.assertNotIn("secret-key", " ".join(command_args))
        self.assertEqual(["HOME", "PATH", "SCANOSS_API_KEY"], sorted(scanoss_env))
        self.assertEqual("secret-key", scanoss_env["SCANOSS_API_KEY"])

    def test_scanpipe_pipes_scanoss_to_line_range(self):
        self.assertEqual([40, 326], scanoss.to_line_range("40-326"))

    def test_scanpipe_pipes_scanoss_parse_line_ranges(self):
        self.assertEqual([], scanoss.parse_line_ranges("all", "all"))

        expected = [
            {"lines": [1, 37], "origin_lines": [5, 41]},
            {"lines": [40, 326], "origin_lines": [44, 330]},
        ]
        line_ranges = scanoss.parse_line_ranges("1-37,40-326", "5-41,44-330")
        self.assertEqual(expected, line_ranges)

    def test_scanpipe_pipes_scanoss_parse_similarity(self):
        self.assertEqual(94, scanoss.parse_similarity("94%"))

    def test_scanpipe_pipes_scanoss_get_versioned_purl(self):
        component = {"purl": ["pkg:github/benjaminp/six", "pkg:pypi/six"]}
        component["version"] = "1.17.0"
        self.assertEqual(
            "pkg:github/benjaminp/six@1.17.0", scanoss.get_versioned_purl(component)
        )

        component = {"purl": ["pkg:pypi/six@1.16.0"], "version": "1.17.0"}
        self.assertEqual("pkg:pypi/six@1.16.0", scanoss.get_versioned_purl(component))

        self.assertEqual("", scanoss.get_versioned_purl({"version": "1.0"}))

        component = {"purl": ["not-a-purl"], "version": "1.0"}
        self.assertEqual("", scanoss.get_versioned_purl(component))

    def test_scanpipe_pipes_scanoss_get_components(self):
        best_match = {"id": "file", "purl": ["pkg:pypi/six"]}
        self.assertEqual([best_match], scanoss.get_components(best_match))

        components = [{"purl": ["pkg:pypi/six"]}, {"purl": ["pkg:pypi/urllib3"]}]
        scanoss_match = {"id": "file", "components": components}
        self.assertEqual(components, scanoss.get_components(scanoss_match))

    def test_scanpipe_pipes_scanoss_get_origin_match_extra_data(self):
        scanoss_match = self.scanoss_results["exact-copy/myapp/_vendor/six.py"][0]
        extra_data = scanoss.get_origin_match_extra_data(scanoss_match, scanoss_match)

        expected = {
            "purls": [
                "pkg:github/benjaminp/six",
                "pkg:pypi/six",
                "pkg:golang/github.com/benjaminp/six",
                "pkg:conda/six",
            ],
            "release_date": "2024-12-03",
            "url": "https://github.com/benjaminp/six",
            "licenses": [{"name": "MIT", "source": "component_declared"}],
            "file_hash": "71e8581c332473a17735159487901fb5",
            "source_hash": "71e8581c332473a17735159487901fb5",
            "hits": None,
            "kb_version": {"daily": "26.10.19", "monthly": "26.09"},
        }
        self.assertEqual(expected, extra_data)

    def test_scanpipe_pipes_scanoss_make_origin_matches(self):
        resource = make_resource_file(self.project1, "modified-copy/src/inih/ini.c")
        scanoss_matches = self.scanoss_results["modified-copy/src/inih/ini.c"]

        origin_matches = list(scanoss.make_origin_matches(resource, scanoss_matches))
        self.assertEqual(1, len(origin_matches))
        origin_match = origin_matches[0]
        self.assertEqual("pkg:github/benhoyt/inih@498f34b", origin_match.purl)
        self.assertEqual(OriginMatch.MatchType.SNIPPET, origin_match.match_type)
        self.assertEqual("scanoss", origin_match.tool)
        self.assertEqual("5.4.27", origin_match.tool_version)
        self.assertEqual("ini.c", origin_match.origin_path)
        expected_line_ranges = [{"lines": [7, 324], "origin_lines": [7, 324]}]
        self.assertEqual(expected_line_ranges, origin_match.line_ranges)
        self.assertEqual(94, origin_match.similarity)

        no_match = self.scanoss_results["no-origin/src/greenhouse_watering.py"]
        self.assertEqual([], list(scanoss.make_origin_matches(resource, no_match)))

    def test_scanpipe_pipes_scanoss_load_scanoss_results(self):
        six_resource = make_resource_file(
            self.project1, "exact-copy/myapp/_vendor/six.py"
        )
        make_resource_file(self.project1, "modified-copy/src/inih/ini.c")
        results_location = self.data / "scanoss-results.json"

        origin_match_count = scanoss.load_scanoss_results(
            self.project1, results_location
        )
        self.assertEqual(2, origin_match_count)
        six_origin_match = six_resource.origin_matches.get()
        self.assertEqual("pkg:github/benjaminp/six@1.17.0", six_origin_match.purl)
        self.assertEqual(OriginMatch.MatchType.FILE, six_origin_match.match_type)
        self.assertEqual(100, six_origin_match.similarity)
        self.assertEqual([], six_origin_match.line_ranges)

        message = self.project1.projectmessages.get()
        self.assertEqual(
            "SCANOSS results for paths missing from the codebase", message.description
        )
        self.assertEqual(
            {"paths": ["no-origin/src/greenhouse_watering.py"]}, message.details
        )

        scanoss.load_scanoss_results(self.project1, results_location)
        self.assertEqual(2, self.project1.originmatchs.count())

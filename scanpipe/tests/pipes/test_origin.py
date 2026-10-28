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
import shutil
from pathlib import Path

from django.test import TestCase

from scanpipe.models import OriginDetermination
from scanpipe.models import OriginMatch
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes import matchcode
from scanpipe.pipes import origin
from scanpipe.pipes import scanoss
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_directory
from scanpipe.tests import make_resource_file

SCANOSS_SIX_PURLS = ["pkg:github/benjaminp/six", "pkg:pypi/six", "pkg:conda/six"]


def make_unsaved_origin_match(purl, tool="matchcode", match_type="file", purls=None):
    extra_data = {"purls": purls} if purls else {}
    return OriginMatch(
        purl=purl, tool=tool, match_type=match_type, extra_data=extra_data
    )


def make_origin(purl, tool="matchcode", match_type="file", purls=None):
    origin_match = make_unsaved_origin_match(purl, tool, match_type, purls)
    return origin.Origin.from_origin_match(origin_match)


def make_scanoss_six_origin():
    return make_origin(
        "pkg:github/benjaminp/six@1.17.0", tool="scanoss", purls=SCANOSS_SIX_PURLS
    )


class ScanPipeOriginPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "code-genetics"

    def setUp(self):
        self.project1 = make_project()

    def make_origin_match(self, resource, purl, tool="matchcode", match_type="file"):
        return OriginMatch.objects.create(
            project=self.project1,
            resource=resource,
            purl=purl,
            match_type=match_type,
            tool=tool,
        )

    def load_data_set_case(self, case_name):
        """Return a project with the codebase and tool results of a data set case."""
        case_path = self.data / case_name
        project = make_project(case_name)
        shutil.copytree(
            case_path / "codebase", project.codebase_path, dirs_exist_ok=True
        )
        collect_and_create_codebase_resources(project)

        match_results = json.loads((case_path / "matchcode-results.json").read_text())
        matchcode.load_matchcode_results(project, match_results)
        scanoss.load_scanoss_results(project, case_path / "scanoss-results.json")
        return project

    def get_expected_purls_by_path(self, case_name):
        """Return the expected origin PURL of each file and package directory."""
        expected_location = self.data / case_name / "expected.json"
        expected_data = json.loads(expected_location.read_text())
        expected_purls_by_path = {
            package["path"]: package["purl"]
            for package in expected_data.get("packages", [])
        }
        for resource in expected_data["resources"]:
            if resource["origin"]:
                expected_purls_by_path[resource["path"]] = resource["origin"]["purl"]
        return expected_purls_by_path

    def test_scanpipe_pipes_origin_get_package_purl(self):
        purl = "pkg:pypi/six@1.17.0?file_name=six-1.17.0.tar.gz#six.py"
        self.assertEqual("pkg:pypi/six@1.17.0", origin.get_package_purl(purl, "1.17.0"))
        self.assertEqual(
            "pkg:npm/ms@2.1.3", origin.get_package_purl("pkg:npm/ms", "2.1.3")
        )

    def test_scanpipe_pipes_origin_get_versioned_purls(self):
        purls = ["pkg:npm/ms", "pkg:github/vercel/ms", "not-a-purl"]
        expected = {"pkg:npm/ms@2.1.3", "pkg:github/vercel/ms@2.1.3"}
        self.assertEqual(expected, origin.get_versioned_purls(purls, "2.1.3"))
        self.assertEqual(set(), origin.get_versioned_purls([], "2.1.3"))

    def test_scanpipe_pipes_origin_origin_from_origin_match(self):
        origin_match = make_unsaved_origin_match(
            "pkg:github/benjaminp/six@1.17.0", tool="scanoss", purls=SCANOSS_SIX_PURLS
        )
        six_origin = origin.Origin.from_origin_match(origin_match)

        self.assertEqual(["pkg:github/benjaminp/six@1.17.0"], six_origin.reported_purls)
        expected_purls = {
            "pkg:github/benjaminp/six@1.17.0",
            "pkg:pypi/six@1.17.0",
            "pkg:conda/six@1.17.0",
        }
        self.assertEqual(expected_purls, six_origin.equivalent_purls)
        self.assertEqual(expected_purls, six_origin.common_purls)
        self.assertEqual({"scanoss"}, six_origin.tools)
        self.assertTrue(six_origin.has_exact_match)

        snippet_origin = make_origin("pkg:npm/lodash@4.17.21", match_type="snippet")
        self.assertFalse(snippet_origin.has_exact_match)

    def test_scanpipe_pipes_origin_origin_purl(self):
        scanoss_origin = make_scanoss_six_origin()
        self.assertEqual("pkg:github/benjaminp/six@1.17.0", scanoss_origin.purl)

        scanoss_origin.merge(make_origin("pkg:pypi/six@1.17.0"))
        self.assertEqual("pkg:pypi/six@1.17.0", scanoss_origin.purl)

    def test_scanpipe_pipes_origin_origin_is_same_package(self):
        scanoss_origin = make_scanoss_six_origin()
        self.assertTrue(
            scanoss_origin.is_same_package(make_origin("pkg:pypi/six@1.17.0"))
        )
        self.assertFalse(
            scanoss_origin.is_same_package(make_origin("pkg:pypi/six@1.16.0"))
        )

    def test_scanpipe_pipes_origin_origin_merge(self):
        matchcode_origin = make_origin("pkg:npm/ms@2.1.3", match_type="directory")
        scanoss_origin = make_origin(
            "pkg:github/vercel/ms@2.1.3",
            tool="scanoss",
            purls=["pkg:github/vercel/ms", "pkg:npm/ms"],
        )
        matchcode_origin.merge(scanoss_origin)

        expected_reported_purls = ["pkg:npm/ms@2.1.3", "pkg:github/vercel/ms@2.1.3"]
        self.assertEqual(expected_reported_purls, matchcode_origin.reported_purls)
        expected_equivalent_purls = {"pkg:npm/ms@2.1.3", "pkg:github/vercel/ms@2.1.3"}
        self.assertEqual(expected_equivalent_purls, matchcode_origin.equivalent_purls)
        self.assertEqual({"pkg:npm/ms@2.1.3"}, matchcode_origin.common_purls)
        self.assertEqual({"matchcode", "scanoss"}, matchcode_origin.tools)
        self.assertTrue(matchcode_origin.has_exact_match)

    def test_scanpipe_pipes_origin_get_same_package_origins(self):
        six_origin = make_origin("pkg:pypi/six@1.17.0")
        scanoss_origin = make_scanoss_six_origin()
        urllib3_origin = make_origin("pkg:pypi/urllib3@1.26.20")

        same_package_origins = origin.get_same_package_origins(
            six_origin, [scanoss_origin, urllib3_origin]
        )
        self.assertEqual([scanoss_origin], same_package_origins)
        self.assertEqual([], origin.get_same_package_origins(six_origin, []))

    def test_scanpipe_pipes_origin_group_origin_matches(self):
        origin_matches = [
            make_unsaved_origin_match("pkg:pypi/six@1.17.0"),
            make_unsaved_origin_match("pkg:pypi/urllib3@1.26.20"),
            make_unsaved_origin_match(
                "pkg:github/benjaminp/six@1.17.0",
                tool="scanoss",
                purls=SCANOSS_SIX_PURLS,
            ),
        ]

        origins = origin.group_origin_matches(origin_matches)
        origin_purls = [grouped_origin.purl for grouped_origin in origins]
        self.assertEqual(
            ["pkg:pypi/urllib3@1.26.20", "pkg:pypi/six@1.17.0"], origin_purls
        )
        self.assertEqual({"matchcode", "scanoss"}, origins[1].tools)

    def test_scanpipe_pipes_origin_iter_resource_origins(self):
        six_resource = make_resource_file(self.project1, path="six.py")
        ini_resource = make_resource_file(self.project1, path="ini.c")
        self.make_origin_match(six_resource, "pkg:pypi/six@1.17.0")
        self.make_origin_match(six_resource, "pkg:pypi/six@1.16.0")
        self.make_origin_match(ini_resource, "pkg:github/benhoyt/inih@r62")

        origin_matches = self.project1.originmatchs.order_by("resource__path")
        resource_origins = [
            (resource.path, len(origins))
            for resource, origins in origin.iter_resource_origins(origin_matches)
        ]
        self.assertEqual([("ini.c", 1), ("six.py", 2)], resource_origins)

    def test_scanpipe_pipes_origin_get_ancestor_paths(self):
        expected = ["vendor/ms", "vendor"]
        self.assertEqual(expected, origin.get_ancestor_paths("vendor/ms/index.js"))
        self.assertEqual([], origin.get_ancestor_paths("six.py"))

    def test_scanpipe_pipes_origin_remove_ancestor_directory_origins(self):
        vendor_ms_origin = make_origin("pkg:npm/ms@2.1.3", match_type="directory")
        vendor_lodash_origin = make_origin(
            "pkg:npm/lodash@4.17.21", match_type="directory"
        )
        origins_by_directory_path = {
            "vendor": [vendor_ms_origin, vendor_lodash_origin],
            "vendor/ms": [make_origin("pkg:npm/ms@2.1.3", match_type="directory")],
        }

        origin.remove_ancestor_directory_origins(origins_by_directory_path)
        self.assertEqual([vendor_lodash_origin], origins_by_directory_path["vendor"])
        self.assertEqual(1, len(origins_by_directory_path["vendor/ms"]))

    def test_scanpipe_pipes_origin_get_closest_directory_origins(self):
        vendor_origin = make_origin("pkg:npm/ms@2.1.3", match_type="directory")
        origins_by_directory_path = {"vendor": [vendor_origin], "vendor/ms": []}

        closest_directory_origins = origin.get_closest_directory_origins(
            "vendor/ms/index.js", origins_by_directory_path
        )
        self.assertEqual([vendor_origin], closest_directory_origins)

        closest_directory_origins = origin.get_closest_directory_origins(
            "src/index.js", origins_by_directory_path
        )
        self.assertEqual([], closest_directory_origins)

    def test_scanpipe_pipes_origin_is_directory_origin(self):
        directory_origins = [make_origin("pkg:npm/ms@2.1.3", match_type="directory")]
        ms_origin = make_origin("pkg:npm/ms@2.1.3")
        lodash_origin = make_origin("pkg:npm/lodash@4.17.21")

        self.assertTrue(origin.is_directory_origin([ms_origin], directory_origins))
        self.assertFalse(
            origin.is_directory_origin([ms_origin, lodash_origin], directory_origins)
        )
        self.assertFalse(origin.is_directory_origin([ms_origin], []))

    def test_scanpipe_pipes_origin_get_status_and_rule(self):
        needs_review = OriginDetermination.Status.NEEDS_REVIEW

        snippet_origin = make_origin("pkg:npm/lodash@4.17.21", match_type="snippet")
        expected = (needs_review, origin.NO_EXACT_MATCH_RULE)
        self.assertEqual(expected, origin.get_status_and_rule(snippet_origin))

        six_origin = make_origin("pkg:pypi/six@1.17.0")
        expected = (needs_review, origin.SINGLE_TOOL_RULE)
        self.assertEqual(expected, origin.get_status_and_rule(six_origin))

        six_origin.merge(make_scanoss_six_origin())
        expected = (
            OriginDetermination.Status.AUTO_CONFIRMED,
            origin.CONFIRMED_BY_TWO_TOOLS_RULE,
        )
        self.assertEqual(expected, origin.get_status_and_rule(six_origin))

    def test_scanpipe_pipes_origin_make_origin_determination(self):
        resource = make_resource_file(self.project1, path="six.py")
        six_origin = make_origin("pkg:pypi/six@1.17.0")
        urllib3_origin = make_origin("pkg:pypi/urllib3@1.26.20")

        determination = origin.make_origin_determination(
            self.project1, resource, [six_origin]
        )
        self.assertEqual(resource, determination.resource)
        self.assertEqual("pkg:pypi/six@1.17.0", determination.purl)
        self.assertEqual("needs-review", determination.status)
        self.assertEqual(origin.SINGLE_TOOL_RULE, determination.rule)

        determination = origin.make_origin_determination(
            self.project1, resource, [six_origin, urllib3_origin]
        )
        self.assertEqual("", determination.purl)
        self.assertEqual("needs-review", determination.status)
        self.assertEqual(origin.CONFLICTING_CANDIDATES_RULE, determination.rule)

    def test_scanpipe_pipes_origin_iter_origin_determinations(self):
        vendor = make_resource_directory(self.project1, path="vendor")
        vendor_ms = make_resource_directory(self.project1, path="vendor/ms")
        index_js = make_resource_file(self.project1, path="vendor/ms/index.js")
        debounce_js = make_resource_file(self.project1, path="vendor/ms/debounce.js")
        self.make_origin_match(vendor, "pkg:npm/ms@2.1.3", match_type="directory")
        self.make_origin_match(vendor_ms, "pkg:npm/ms@2.1.3", match_type="directory")
        self.make_origin_match(index_js, "pkg:npm/ms@2.1.3", tool="scanoss")
        self.make_origin_match(debounce_js, "pkg:npm/lodash@4.17.21")

        origin_matches = self.project1.originmatchs.order_by("resource__path")
        determinations = origin.iter_origin_determinations(
            self.project1, origin_matches
        )
        values = [
            (determination.resource.path, determination.purl, determination.rule)
            for determination in determinations
        ]
        expected = [
            (
                "vendor/ms/debounce.js",
                "pkg:npm/lodash@4.17.21",
                origin.SINGLE_TOOL_RULE,
            ),
            ("vendor/ms", "pkg:npm/ms@2.1.3", origin.CONFIRMED_BY_TWO_TOOLS_RULE),
        ]
        self.assertEqual(expected, values)

    def test_scanpipe_pipes_origin_determine_origins(self):
        six_resource = make_resource_file(self.project1, path="six.py")
        ini_resource = make_resource_file(self.project1, path="ini.c")
        self.make_origin_match(six_resource, "pkg:pypi/six@1.17.0")
        self.make_origin_match(ini_resource, "pkg:github/benhoyt/inih@498f34b")
        user_determination = OriginDetermination.objects.create(
            project=self.project1,
            resource=ini_resource,
            purl="pkg:github/benhoyt/inih@r62",
            status=OriginDetermination.Status.CONFIRMED,
        )

        self.assertEqual(1, origin.determine_origins(self.project1))
        self.assertEqual(1, origin.determine_origins(self.project1))

        determinations = self.project1.origindeterminations.order_by("resource__path")
        values = determinations.values_list("resource__path", "purl", "status", "rule")
        expected = [
            ("ini.c", "pkg:github/benhoyt/inih@r62", "confirmed", ""),
            ("six.py", "pkg:pypi/six@1.17.0", "needs-review", origin.SINGLE_TOOL_RULE),
        ]
        self.assertEqual(expected, list(values))
        self.assertEqual(user_determination, determinations[0])

    def test_scanpipe_pipes_origin_determine_origins_code_genetics_data_set(self):
        expected_by_case = {
            "exact-copy": [
                (
                    "myapp/_vendor/six.py",
                    "pkg:pypi/six@1.17.0",
                    "auto-confirmed",
                    origin.CONFIRMED_BY_TWO_TOOLS_RULE,
                ),
            ],
            "vendored-copy": [
                (
                    "myapp/_vendor/urllib3/packages/six.py",
                    "",
                    "needs-review",
                    origin.CONFLICTING_CANDIDATES_RULE,
                ),
            ],
            "modified-copy": [
                (
                    "src/inih/ini.c",
                    "",
                    "needs-review",
                    origin.CONFLICTING_CANDIDATES_RULE,
                ),
                (
                    "src/inih/ini.h",
                    "pkg:github/benhoyt/inih@r62",
                    "auto-confirmed",
                    origin.CONFIRMED_BY_TWO_TOOLS_RULE,
                ),
            ],
            "snippet": [
                (
                    "src/scheduler.js",
                    "pkg:npm/lodash@4.17.21",
                    "needs-review",
                    origin.NO_EXACT_MATCH_RULE,
                ),
            ],
            "embedded-package": [
                (
                    "vendor/ms",
                    "pkg:npm/ms@2.1.3",
                    "auto-confirmed",
                    origin.CONFIRMED_BY_TWO_TOOLS_RULE,
                ),
            ],
            "no-origin": [],
        }

        for case_name, expected in expected_by_case.items():
            with self.subTest(case_name):
                project = self.load_data_set_case(case_name)
                origin.determine_origins(project)

                determinations = project.origindeterminations.order_by("resource__path")
                values = determinations.values_list(
                    "resource__path", "purl", "status", "rule"
                )
                self.assertEqual(expected, list(values))

                # Every automatic confirmation matches the ground truth.
                expected_purls_by_path = self.get_expected_purls_by_path(case_name)
                auto_confirmed = determinations.filter(status="auto-confirmed")
                for path, purl in auto_confirmed.values_list("resource__path", "purl"):
                    self.assertEqual(expected_purls_by_path[path], purl)

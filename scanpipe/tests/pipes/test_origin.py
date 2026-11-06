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
from datetime import date
from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe.models import OriginDetermination
from scanpipe.models import OriginMatch
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes import matchcode
from scanpipe.pipes import origin
from scanpipe.pipes import purldb
from scanpipe.pipes import scanoss
from scanpipe.tests import make_package
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_directory
from scanpipe.tests import make_resource_file

SCANOSS_SIX_PURLS = ["pkg:github/benjaminp/six", "pkg:pypi/six", "pkg:conda/six"]


def make_unsaved_origin_match(
    purl,
    tool="matchcode",
    match_type="file",
    purls=None,
    similarity=None,
    origin_path="",
    release_date="",
):
    extra_data = {"purls": purls} if purls else {}
    if release_date:
        extra_data["release_date"] = release_date
    return OriginMatch(
        purl=purl,
        tool=tool,
        match_type=match_type,
        origin_path=origin_path,
        similarity=similarity,
        extra_data=extra_data,
    )


def make_origin(
    purl,
    tool="matchcode",
    match_type="file",
    purls=None,
    similarity=None,
    origin_path="",
    release_date="",
):
    origin_match = make_unsaved_origin_match(
        purl, tool, match_type, purls, similarity, origin_path, release_date
    )
    return origin.Origin.from_origin_match(origin_match)


def make_scanoss_license_match(*license_names_and_sources):
    licenses = [
        {"name": license_name, "source": source}
        for license_name, source in license_names_and_sources
    ]
    return OriginMatch(tool="scanoss", extra_data={"licenses": licenses})


def make_scanoss_six_origin():
    return make_origin(
        "pkg:github/benjaminp/six@1.17.0", tool="scanoss", purls=SCANOSS_SIX_PURLS
    )


class ScanPipeOriginPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "code-genetics"

    def setUp(self):
        self.project1 = make_project()

    def make_origin_match(
        self,
        resource,
        purl,
        tool="matchcode",
        match_type="file",
        extra_data=None,
        line_ranges=None,
    ):
        return OriginMatch.objects.create(
            project=self.project1,
            resource=resource,
            purl=purl,
            match_type=match_type,
            tool=tool,
            extra_data=extra_data or {},
            line_ranges=line_ranges or [],
        )

    @staticmethod
    def get_purldb_resources(case_path):
        """Return the PurlDB resources of the files matched by MatchCode.io."""
        resources_location = case_path / "purldb-resources.json"
        if not resources_location.exists():
            return []
        return json.loads(resources_location.read_text())

    def load_data_set_case(self, case_name, tools=None):
        """
        Return a project with the codebase and the results of the ``tools`` of a
        data set case, all the tools by default.
        """
        tools = tools or [matchcode.TOOL_NAME, scanoss.TOOL_NAME]
        case_path = self.data / case_name
        project = make_project()
        shutil.copytree(
            case_path / "codebase", project.codebase_path, dirs_exist_ok=True
        )
        collect_and_create_codebase_resources(project)

        if matchcode.TOOL_NAME in tools:
            results_location = case_path / "matchcode-results.json"
            match_results = json.loads(results_location.read_text())
            purldb_resources = self.get_purldb_resources(case_path)
            with (
                mock.patch.object(purldb, "is_configured", return_value=True),
                mock.patch.object(
                    purldb, "match_resources", return_value=purldb_resources
                ),
            ):
                matchcode.load_matchcode_results(project, match_results)

        if scanoss.TOOL_NAME in tools:
            results_location = case_path / "scanoss-results.json"
            scanoss.load_scanoss_results(project, results_location)

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
        self.assertEqual("pkg:pypi/six@1.17.0", origin.get_package_purl(purl))

    def test_scanpipe_pipes_origin_get_versioned_purls(self):
        purls = ["pkg:npm/ms", "pkg:github/vercel/ms", "not-a-purl"]
        expected = {"pkg:npm/ms@2.1.3", "pkg:github/vercel/ms@2.1.3"}
        self.assertEqual(expected, origin.get_versioned_purls(purls, "2.1.3"))
        self.assertEqual(set(), origin.get_versioned_purls([], "2.1.3"))

    def test_scanpipe_pipes_origin_get_equivalent_purls(self):
        origin_match = make_unsaved_origin_match(
            "pkg:github/benjaminp/six@1.17.0", tool="scanoss", purls=SCANOSS_SIX_PURLS
        )
        expected = {
            "pkg:github/benjaminp/six@1.17.0",
            "pkg:pypi/six@1.17.0",
            "pkg:conda/six@1.17.0",
        }
        self.assertEqual(expected, origin.get_equivalent_purls(origin_match))

        origin_match = make_unsaved_origin_match("pkg:pypi/six@1.17.0?file_name=six.py")
        expected = {"pkg:pypi/six@1.17.0"}
        self.assertEqual(expected, origin.get_equivalent_purls(origin_match))

    def test_scanpipe_pipes_origin_is_release_version(self):
        self.assertFalse(origin.is_release_version("498f34b"))
        self.assertFalse(
            origin.is_release_version("498f34b4c6b5d8a0e3f1a2b7c9d0e1f2a3b4c5d6")
        )
        self.assertFalse(origin.is_release_version(None))
        self.assertFalse(origin.is_release_version(""))
        self.assertTrue(origin.is_release_version("r62"))
        self.assertTrue(origin.is_release_version("1.17.0"))
        self.assertTrue(origin.is_release_version("v1.0.3"))
        self.assertTrue(origin.is_release_version("20240101"))
        self.assertTrue(origin.is_release_version("abc12"))

    def test_scanpipe_pipes_origin_normalize_name(self):
        self.assertEqual(
            "typing_extensions", origin.normalize_name("Typing-Extensions")
        )

    def test_scanpipe_pipes_origin_get_path_names(self):
        path = "pip-24.0.tar.gz-extract/pip-24.0/src/pip/_vendor/six.py"
        expected = {
            "pip_24.0.tar.gz_extract",
            "pip_24.0",
            "src",
            "pip",
            "_vendor",
            "six",
        }
        self.assertEqual(expected, origin.get_path_names(path))
        self.assertEqual({"six"}, origin.get_path_names("six.py"))

    def test_scanpipe_pipes_origin_get_release_date(self):
        origin_match = make_unsaved_origin_match("pkg:pypi/six@1.16.0")
        self.assertIsNone(origin.get_release_date(origin_match))

        origin_match.extra_data["release_date"] = "2021-05-05"
        self.assertEqual(date(2021, 5, 5), origin.get_release_date(origin_match))

        origin_match.extra_data["release_date"] = "May 5, 2021"
        self.assertIsNone(origin.get_release_date(origin_match))

    def test_scanpipe_pipes_origin_get_versionless_purl(self):
        purl = "pkg:pypi/six@1.17.0?file_name=six-1.17.0.tar.gz#six.py"
        self.assertEqual("pkg:pypi/six", origin.get_versionless_purl(purl))

    def test_scanpipe_pipes_origin_origin_from_origin_match(self):
        origin_match = make_unsaved_origin_match(
            "pkg:github/benjaminp/six@1.17.0", tool="scanoss", purls=SCANOSS_SIX_PURLS
        )
        six_origin = origin.Origin.from_origin_match(origin_match)

        self.assertEqual([origin_match], six_origin.origin_matches)
        expected_purls = {
            "pkg:github/benjaminp/six@1.17.0",
            "pkg:pypi/six@1.17.0",
            "pkg:conda/six@1.17.0",
        }
        self.assertEqual(expected_purls, six_origin.equivalent_purls)
        self.assertEqual({"scanoss"}, six_origin.tools)
        self.assertTrue(six_origin.has_exact_match)

        snippet_origin = make_origin("pkg:npm/lodash@4.17.21", match_type="snippet")
        self.assertFalse(snippet_origin.has_exact_match)

    def test_scanpipe_pipes_origin_origin_purl(self):
        scanoss_origin = make_scanoss_six_origin()
        self.assertEqual("pkg:github/benjaminp/six@1.17.0", scanoss_origin.purl)

        scanoss_origin.merge(make_origin("pkg:pypi/six@1.17.0"))
        self.assertEqual("pkg:pypi/six@1.17.0", scanoss_origin.purl)

    def test_scanpipe_pipes_origin_origin_versionless_purls(self):
        expected = {"pkg:github/benjaminp/six", "pkg:pypi/six", "pkg:conda/six"}
        self.assertEqual(expected, make_scanoss_six_origin().versionless_purls)

    def test_scanpipe_pipes_origin_origin_package_names(self):
        self.assertEqual({"six"}, make_scanoss_six_origin().package_names)
        typing_origin = make_origin("pkg:pypi/Typing-Extensions@4.9.0")
        self.assertEqual({"typing_extensions"}, typing_origin.package_names)

    def test_scanpipe_pipes_origin_origin_origin_path_names(self):
        pip_origin = make_origin("pkg:pypi/pip@24.0")
        self.assertEqual(set(), pip_origin.origin_path_names)

        pip_origin.merge(
            make_origin("pkg:pypi/pip@24.0", origin_path="pip-24.0/_vendor/six.py")
        )
        expected = {"pip_24.0", "_vendor", "six"}
        self.assertEqual(expected, pip_origin.origin_path_names)

    def test_scanpipe_pipes_origin_origin_is_release_version(self):
        commit_origin = make_origin("pkg:github/benhoyt/inih@498f34b", tool="scanoss")
        self.assertFalse(commit_origin.is_release_version)
        self.assertTrue(make_origin("pkg:github/benhoyt/inih@r62").is_release_version)
        versionless_origin = make_origin("pkg:github/benhoyt/inih", tool="scanoss")
        self.assertFalse(versionless_origin.is_release_version)

    def test_scanpipe_pipes_origin_origin_similarity(self):
        six_origin = make_origin("pkg:pypi/six@1.17.0")
        self.assertIsNone(six_origin.similarity)

        six_origin.merge(make_origin("pkg:pypi/six@1.17.0", similarity=94))
        six_origin.merge(make_origin("pkg:pypi/six@1.17.0", similarity=95))
        self.assertEqual(95, six_origin.similarity)

    def test_scanpipe_pipes_origin_origin_release_date(self):
        six_origin = make_origin("pkg:pypi/six@1.16.0")
        self.assertIsNone(six_origin.release_date)

        six_origin.merge(make_origin("pkg:pypi/six@1.16.0", release_date="2021-06-01"))
        six_origin.merge(make_origin("pkg:pypi/six@1.16.0", release_date="2021-05-05"))
        self.assertEqual(date(2021, 5, 5), six_origin.release_date)

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

        self.assertEqual(2, len(matchcode_origin.origin_matches))
        expected_equivalent_purls = {"pkg:npm/ms@2.1.3", "pkg:github/vercel/ms@2.1.3"}
        self.assertEqual(expected_equivalent_purls, matchcode_origin.equivalent_purls)
        self.assertEqual("pkg:npm/ms@2.1.3", matchcode_origin.purl)
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

    def test_scanpipe_pipes_origin_iter_resource_origins_short_snippet_matches(self):
        header_resource = make_resource_file(self.project1, path="header.py")
        debounce_resource = make_resource_file(self.project1, path="debounce.js")
        self.make_origin_match(
            header_resource,
            "pkg:pypi/six@1.16.0",
            match_type="snippet",
            line_ranges=[{"lines": [3, 19]}],
        )
        self.make_origin_match(
            debounce_resource,
            "pkg:npm/lodash@4.17.21",
            match_type="snippet",
            line_ranges=[{"lines": [26, 140]}],
        )
        self.make_origin_match(
            debounce_resource,
            "pkg:pypi/six@1.16.0",
            match_type="snippet",
            line_ranges=[{"lines": [1, 5]}],
        )

        origin_matches = self.project1.originmatchs.order_by("resource__path")
        resource_origins = [
            (resource.path, [resource_origin.purl for resource_origin in origins])
            for resource, origins in origin.iter_resource_origins(origin_matches)
        ]
        self.assertEqual(
            [("debounce.js", ["pkg:npm/lodash@4.17.21"])], resource_origins
        )

    def test_scanpipe_pipes_origin_get_matched_line_count(self):
        origin_match = OriginMatch(line_ranges=[])
        self.assertEqual(0, origin.get_matched_line_count(origin_match))

        origin_match.line_ranges = [{"lines": [3, 19]}]
        self.assertEqual(17, origin.get_matched_line_count(origin_match))

        # Overlapping ranges count each line once.
        origin_match.line_ranges = [
            {"lines": [1, 36], "origin_lines": [1, 36]},
            {"lines": [30, 40], "origin_lines": [30, 40]},
        ]
        self.assertEqual(40, origin.get_matched_line_count(origin_match))

    def test_scanpipe_pipes_origin_is_short_snippet_match(self):
        origin_match = OriginMatch(match_type="snippet", line_ranges=[])
        self.assertTrue(origin.is_short_snippet_match(origin_match))

        origin_match.line_ranges = [{"lines": [1, 19]}]
        self.assertTrue(origin.is_short_snippet_match(origin_match))

        origin_match.line_ranges = [{"lines": [1, 20]}]
        self.assertFalse(origin.is_short_snippet_match(origin_match))

        # Only the snippet matches have a minimum length.
        file_match = OriginMatch(match_type="file", line_ranges=[])
        self.assertFalse(origin.is_short_snippet_match(file_match))

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

    def test_scanpipe_pipes_origin_is_same_package_versions(self):
        six_17_origin = make_scanoss_six_origin()
        six_16_origin = make_origin("pkg:pypi/six@1.16.0")
        urllib3_origin = make_origin("pkg:pypi/urllib3@1.26.20")

        self.assertTrue(origin.is_same_package_versions([six_17_origin, six_16_origin]))
        self.assertFalse(
            origin.is_same_package_versions([six_16_origin, urllib3_origin])
        )

    def test_scanpipe_pipes_origin_is_carrier_origin(self):
        six_origin = make_origin("pkg:pypi/six@1.16.0", origin_path="six-1.16.0/six.py")
        pip_origin = make_origin(
            "pkg:pypi/pip@24.0", origin_path="pip-24.0/src/pip/_vendor/six.py"
        )
        urllib3_origin = make_origin(
            "pkg:pypi/urllib3@1.26.20",
            origin_path="urllib3-1.26.20/src/urllib3/packages/six.py",
        )

        self.assertTrue(origin.is_carrier_origin(pip_origin, [six_origin]))
        self.assertFalse(origin.is_carrier_origin(six_origin, [pip_origin]))
        self.assertFalse(origin.is_carrier_origin(urllib3_origin, [pip_origin]))
        # Without origin path, the content of a package is unknown.
        self.assertFalse(
            origin.is_carrier_origin(make_origin("pkg:pypi/pip@24.0"), [six_origin])
        )

    def test_scanpipe_pipes_origin_get_contained_origin(self):
        six_origin = make_origin("pkg:pypi/six@1.16.0", origin_path="six-1.16.0/six.py")
        pip_origin = make_origin(
            "pkg:pypi/pip@24.0", origin_path="pip-24.0/src/pip/_vendor/six.py"
        )
        virtualenv_origin = make_origin(
            "pkg:pypi/virtualenv@20.0.0",
            origin_path="virtualenv-20.0.0/src/virtualenv/six.py",
        )
        # SCANOSS reports the file name only.
        anime365_origin = make_origin(
            "pkg:github/piotrmasek/anime365@0.1-Ryucon",
            tool="scanoss",
            origin_path="six.py",
        )
        lodash_origin = make_origin(
            "pkg:npm/lodash@4.17.21", origin_path="package/debounce.js"
        )

        self.assertEqual(
            six_origin, origin.get_contained_origin([pip_origin, six_origin])
        )
        contained_origin = origin.get_contained_origin(
            [pip_origin, virtualenv_origin, six_origin]
        )
        self.assertEqual(six_origin, contained_origin)
        contained_origin = origin.get_contained_origin([anime365_origin, six_origin])
        self.assertEqual(six_origin, contained_origin)

        # No carrier.
        self.assertIsNone(origin.get_contained_origin([lodash_origin, six_origin]))
        # Several origins that do not carry another.
        self.assertIsNone(
            origin.get_contained_origin([pip_origin, six_origin, lodash_origin])
        )

    def test_scanpipe_pipes_origin_get_earliest_release_origin(self):
        six_origin = make_origin("pkg:pypi/six@1.16.0", release_date="2021-05-05")
        pip_origin = make_origin("pkg:pypi/pip@24.0", release_date="2024-02-03")
        urllib3_origin = make_origin("pkg:pypi/urllib3@1.26.20")

        earliest_origin = origin.get_earliest_release_origin([pip_origin, six_origin])
        self.assertEqual(six_origin, earliest_origin)

        # A copy is not dated without the release date of all the candidates.
        earliest_origin = origin.get_earliest_release_origin(
            [pip_origin, six_origin, urllib3_origin]
        )
        self.assertIsNone(earliest_origin)

        same_day_origin = make_origin("pkg:pypi/ms@2.1.3", release_date="2021-05-05")
        earliest_origin = origin.get_earliest_release_origin(
            [pip_origin, six_origin, same_day_origin]
        )
        self.assertIsNone(earliest_origin)

    def test_scanpipe_pipes_origin_get_most_similar_origin(self):
        lodash_origin = make_origin("pkg:npm/lodash@4.17.21", similarity=75)
        underscore_origin = make_origin("pkg:npm/underscore@1.13.7", similarity=40)
        debounce_origin = make_origin("pkg:npm/debounce@2.2.0", similarity=60)

        most_similar_origin = origin.get_most_similar_origin(
            [underscore_origin, lodash_origin]
        )
        self.assertEqual(lodash_origin, most_similar_origin)

        # The second highest similarity is within the margin.
        most_similar_origin = origin.get_most_similar_origin(
            [underscore_origin, lodash_origin, debounce_origin]
        )
        self.assertIsNone(most_similar_origin)

        exact_six_origin = make_origin("pkg:pypi/six@1.16.0", similarity=100)
        exact_pip_origin = make_origin("pkg:pypi/pip@24.0", similarity=100)
        most_similar_origin = origin.get_most_similar_origin(
            [exact_six_origin, exact_pip_origin]
        )
        self.assertIsNone(most_similar_origin)

        # A directory match has no similarity.
        directory_origin = make_origin("pkg:npm/ms@2.1.3", match_type="directory")
        most_similar_origin = origin.get_most_similar_origin(
            [lodash_origin, directory_origin]
        )
        self.assertIsNone(most_similar_origin)

    def test_scanpipe_pipes_origin_get_preferred_version_origin(self):
        r62_origin = make_origin("pkg:github/benhoyt/inih@r62", similarity=90)
        commit_origin = make_origin(
            "pkg:github/benhoyt/inih@498f34b", tool="scanoss", similarity=94
        )
        r61_origin = make_origin("pkg:github/benhoyt/inih@r61", similarity=60)
        other_commit_origin = make_origin(
            "pkg:github/benhoyt/inih@577ae2d", tool="scanoss", similarity=60
        )

        # The release is preferred over a commit with a higher similarity.
        preferred_origin = origin.get_preferred_version_origin(
            [r62_origin, commit_origin]
        )
        self.assertEqual(r62_origin, preferred_origin)

        # Between releases, the clearly most similar.
        preferred_origin = origin.get_preferred_version_origin(
            [r61_origin, r62_origin, commit_origin]
        )
        self.assertEqual(r62_origin, preferred_origin)

        # Between commits only, the clearly most similar.
        preferred_origin = origin.get_preferred_version_origin(
            [other_commit_origin, commit_origin]
        )
        self.assertEqual(commit_origin, preferred_origin)

        # No preference within the margin, or on unknown similarities.
        r60_origin = make_origin("pkg:github/benhoyt/inih@r60", similarity=80)
        self.assertIsNone(origin.get_preferred_version_origin([r60_origin, r62_origin]))
        six_17_origin = make_origin("pkg:pypi/six@1.17.0")
        six_16_origin = make_origin("pkg:pypi/six@1.16.0")
        self.assertIsNone(
            origin.get_preferred_version_origin([six_17_origin, six_16_origin])
        )

        # Regression test: a versionless candidate raised a TypeError.
        versionless_origin = make_origin("pkg:pypi/six", tool="scanoss")
        preferred_origin = origin.get_preferred_version_origin(
            [versionless_origin, six_16_origin]
        )
        self.assertEqual(six_16_origin, preferred_origin)
        versionless_inih_origin = make_origin("pkg:github/benhoyt/inih", tool="scanoss")
        rule_and_candidate = origin.get_conflict_rule_and_candidate(
            [versionless_inih_origin, commit_origin]
        )
        self.assertEqual((origin.CONFLICTING_VERSIONS_RULE, None), rule_and_candidate)

    def test_scanpipe_pipes_origin_get_conflict_rule_and_candidate(self):
        r62_origin = make_origin("pkg:github/benhoyt/inih@r62", similarity=95)
        commit_origin = make_origin(
            "pkg:github/benhoyt/inih@498f34b", tool="scanoss", similarity=94
        )
        six_17_origin = make_origin("pkg:pypi/six@1.17.0")
        six_16_origin = make_origin("pkg:pypi/six@1.16.0")
        urllib3_origin = make_origin("pkg:pypi/urllib3@1.26.20")

        rule_and_candidate = origin.get_conflict_rule_and_candidate(
            [six_16_origin, urllib3_origin]
        )
        self.assertEqual((origin.CONFLICTING_CANDIDATES_RULE, None), rule_and_candidate)

        pip_origin = make_origin(
            "pkg:pypi/pip@24.0", origin_path="pip-24.0/src/pip/_vendor/six.py"
        )
        rule_and_candidate = origin.get_conflict_rule_and_candidate(
            [pip_origin, six_16_origin]
        )
        self.assertEqual((origin.CONTAINMENT_RULE, six_16_origin), rule_and_candidate)

        dated_six_origin = make_origin("pkg:pypi/six@1.16.0", release_date="2021-05-05")
        dated_pip_origin = make_origin("pkg:pypi/pip@24.0", release_date="2024-02-03")
        rule_and_candidate = origin.get_conflict_rule_and_candidate(
            [dated_pip_origin, dated_six_origin]
        )
        expected = (origin.EARLIEST_RELEASE_RULE, dated_six_origin)
        self.assertEqual(expected, rule_and_candidate)

        lodash_origin = make_origin("pkg:npm/lodash@4.17.21", similarity=75)
        underscore_origin = make_origin("pkg:npm/underscore@1.13.7", similarity=40)
        rule_and_candidate = origin.get_conflict_rule_and_candidate(
            [underscore_origin, lodash_origin]
        )
        expected = (origin.HIGHEST_SIMILARITY_RULE, lodash_origin)
        self.assertEqual(expected, rule_and_candidate)

        rule_and_candidate = origin.get_conflict_rule_and_candidate(
            [r62_origin, commit_origin]
        )
        self.assertEqual(
            (origin.PREFERRED_VERSION_RULE, r62_origin), rule_and_candidate
        )

        rule_and_candidate = origin.get_conflict_rule_and_candidate(
            [six_17_origin, six_16_origin]
        )
        self.assertEqual((origin.CONFLICTING_VERSIONS_RULE, None), rule_and_candidate)

    def test_scanpipe_pipes_origin_get_single_origin_rule(self):
        six_origin = make_origin("pkg:pypi/six@1.17.0")
        snippet_origin = make_origin("pkg:npm/lodash@4.17.21", match_type="snippet")

        rule = origin.get_single_origin_rule(snippet_origin)
        self.assertEqual(origin.NO_EXACT_MATCH_RULE, rule)
        self.assertEqual(
            origin.SINGLE_TOOL_RULE, origin.get_single_origin_rule(six_origin)
        )

        six_origin.merge(make_scanoss_six_origin())
        rule = origin.get_single_origin_rule(six_origin)
        self.assertEqual(origin.CONFIRMED_BY_TWO_TOOLS_RULE, rule)

    def test_scanpipe_pipes_origin_get_rule_and_candidate(self):
        six_origin = make_origin("pkg:pypi/six@1.17.0")
        urllib3_origin = make_origin("pkg:pypi/urllib3@1.26.20")

        rule_and_candidate = origin.get_rule_and_candidate([six_origin])
        self.assertEqual((origin.SINGLE_TOOL_RULE, six_origin), rule_and_candidate)

        rule_and_candidate = origin.get_rule_and_candidate([six_origin, urllib3_origin])
        self.assertEqual((origin.CONFLICTING_CANDIDATES_RULE, None), rule_and_candidate)

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

        # The preferred version is proposed for review.
        r62_origin = make_origin("pkg:github/benhoyt/inih@r62", similarity=95)
        commit_origin = make_origin(
            "pkg:github/benhoyt/inih@498f34b", tool="scanoss", similarity=94
        )
        determination = origin.make_origin_determination(
            self.project1, resource, [r62_origin, commit_origin]
        )
        self.assertEqual("pkg:github/benhoyt/inih@r62", determination.purl)
        self.assertEqual("needs-review", determination.status)
        self.assertEqual(origin.PREFERRED_VERSION_RULE, determination.rule)

        six_origin.merge(make_scanoss_six_origin())
        determination = origin.make_origin_determination(
            self.project1, resource, [six_origin]
        )
        self.assertEqual("pkg:pypi/six@1.17.0", determination.purl)
        self.assertEqual("auto-confirmed", determination.status)

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

        self.assertEqual((1, 1), origin.determine_origins(self.project1))
        self.assertEqual((1, 1), origin.determine_origins(self.project1))

        determinations = self.project1.origindeterminations.order_by("resource__path")
        values = determinations.values_list("resource__path", "purl", "status", "rule")
        expected = [
            ("ini.c", "pkg:github/benhoyt/inih@r62", "confirmed", ""),
            ("six.py", "pkg:pypi/six@1.17.0", "needs-review", origin.SINGLE_TOOL_RULE),
        ]
        self.assertEqual(expected, list(values))
        self.assertEqual(user_determination, determinations[0])

        package = self.project1.discoveredpackages.get()
        self.assertEqual("pkg:github/benhoyt/inih@r62", package.purl)
        self.assertQuerySetEqual(package.codebase_resources.all(), [ini_resource])

    def test_scanpipe_pipes_origin_determine_origins_user_directory(self):
        vendor_ms = make_resource_directory(self.project1, path="vendor/ms")
        index_js = make_resource_file(self.project1, path="vendor/ms/index.js")
        self.make_origin_match(index_js, "pkg:npm/lodash@4.17.21")
        OriginDetermination.objects.create(
            project=self.project1,
            resource=vendor_ms,
            purl="pkg:npm/ms@2.1.3",
            status=OriginDetermination.Status.CONFIRMED,
        )

        self.assertEqual((0, 1), origin.determine_origins(self.project1))
        self.assertEqual(1, self.project1.origindeterminations.count())
        package = self.project1.discoveredpackages.get()
        self.assertEqual("pkg:npm/ms@2.1.3", package.purl)
        self.assertQuerySetEqual(
            package.codebase_resources.order_by("path"), [vendor_ms, index_js]
        )

    def test_scanpipe_pipes_origin_determine_origins_scan_package(self):
        scan_package = make_package(self.project1, "pkg:pypi/six@1.17.0")
        setup_py = make_resource_file(self.project1, path="setup.py")
        scan_package.add_resources([setup_py])
        six_resource = make_resource_file(self.project1, path="six.py")
        self.make_origin_match(six_resource, "pkg:pypi/six@1.17.0")
        self.make_origin_match(six_resource, "pkg:pypi/six@1.17.0", tool="scanoss")

        self.assertEqual((1, 1), origin.determine_origins(self.project1))
        self.assertEqual((1, 1), origin.determine_origins(self.project1))
        self.assertQuerySetEqual(self.project1.discoveredpackages.all(), [scan_package])
        package_resources = scan_package.codebase_resources.order_by("path")
        self.assertQuerySetEqual(package_resources, [setup_py, six_resource])

        self.project1.originmatchs.all().delete()
        self.assertEqual((0, 0), origin.determine_origins(self.project1))
        self.assertQuerySetEqual(scan_package.codebase_resources.all(), [setup_py])
        scan_package.refresh_from_db()
        self.assertEqual({}, scan_package.extra_data)

    def test_scanpipe_pipes_origin_assign_origin_package_resources(self):
        setup_py = make_resource_file(self.project1, path="setup.py")
        six_resource = make_resource_file(self.project1, path="six.py")
        resources = self.project1.codebaseresources.all()
        scan_package = make_package(self.project1, "pkg:pypi/six@1.17.0")
        scan_package.add_resources([setup_py])

        origin.assign_origin_package_resources(scan_package, resources)
        package_resources = scan_package.codebase_resources.order_by("path")
        self.assertQuerySetEqual(package_resources, [setup_py, six_resource])
        expected = {origin.ORIGIN_RESOURCE_PATHS_KEY: ["six.py"]}
        self.assertEqual(expected, scan_package.extra_data)

        origin_package = make_package(
            self.project1,
            "pkg:npm/ms@2.1.3",
            datasource_ids=[origin.ORIGIN_DATASOURCE_ID],
        )
        origin.assign_origin_package_resources(origin_package, resources)
        self.assertEqual(2, origin_package.codebase_resources.count())
        self.assertEqual({}, origin_package.extra_data)

    def test_scanpipe_pipes_origin_unassign_scan_package_resources(self):
        setup_py = make_resource_file(self.project1, path="setup.py")
        six_resource = make_resource_file(self.project1, path="six.py")
        scan_package = make_package(
            self.project1,
            "pkg:pypi/six@1.17.0",
            extra_data={origin.ORIGIN_RESOURCE_PATHS_KEY: ["six.py"]},
        )
        scan_package.add_resources([setup_py, six_resource])

        origin.unassign_scan_package_resources(self.project1)
        self.assertQuerySetEqual(scan_package.codebase_resources.all(), [setup_py])
        scan_package.refresh_from_db()
        self.assertEqual({}, scan_package.extra_data)

    def test_scanpipe_pipes_origin_get_first_extra_data_value(self):
        origin_matches = [
            make_unsaved_origin_match("pkg:npm/ms@2.1.3"),
            OriginMatch(extra_data={"release_date": "2020-12-08"}),
        ]
        value = origin.get_first_extra_data_value(origin_matches, "release_date")
        self.assertEqual("2020-12-08", value)
        value = origin.get_first_extra_data_value(origin_matches, "download_url")
        self.assertEqual("", value)

    def test_scanpipe_pipes_origin_get_license_names(self):
        origin_matches = [
            make_scanoss_license_match(("MIT", "component_declared")),
            make_scanoss_license_match(
                ("MIT", "license_file"),
                ("ISC", "license_file"),
                ("GPL-2.0-only", "file_header"),
            ),
            OriginMatch(extra_data={}),
        ]
        self.assertEqual(["MIT", "ISC"], origin.get_license_names(origin_matches))

    def test_scanpipe_pipes_origin_get_origin_license_data(self):
        scanoss_match = make_scanoss_license_match(
            ("MIT", "license_file"), ("BSD-2-Clause", "license_file")
        )
        expected = {
            "declared_license_expression": "mit AND bsd-simplified",
            "declared_license_expression_spdx": "MIT AND BSD-2-Clause",
        }
        self.assertEqual(expected, origin.get_origin_license_data([scanoss_match]))

        matchcode_match = OriginMatch(extra_data={"declared_license_expression": "mit"})
        expected = {"declared_license_expression": "mit"}
        license_data = origin.get_origin_license_data([scanoss_match, matchcode_match])
        self.assertEqual(expected, license_data)

        self.assertEqual({}, origin.get_origin_license_data([OriginMatch()]))

    def test_scanpipe_pipes_origin_get_origin_package_data(self):
        origin_matches = [
            OriginMatch(
                extra_data={
                    "download_url": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
                    "declared_license_expression": "mit",
                }
            ),
            OriginMatch(
                extra_data={
                    "url": "https://github.com/vercel/ms",
                    "release_date": "2020-12-08",
                }
            ),
        ]
        expected = {
            "download_url": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
            "homepage_url": "https://github.com/vercel/ms",
            "release_date": "2020-12-08",
            "declared_license_expression": "mit",
        }
        self.assertEqual(expected, origin.get_origin_package_data(origin_matches))

    def test_scanpipe_pipes_origin_get_purl_origin_matches(self):
        resource = make_resource_file(self.project1, path="six.py")
        matchcode_match = self.make_origin_match(resource, "pkg:pypi/six@1.17.0")
        scanoss_match = self.make_origin_match(
            resource,
            "pkg:github/benjaminp/six@1.17.0",
            tool="scanoss",
            extra_data={"purls": SCANOSS_SIX_PURLS},
        )
        self.make_origin_match(resource, "pkg:pypi/six@1.16.0")

        resources = self.project1.codebaseresources.all()
        origin_matches = origin.get_purl_origin_matches(
            self.project1, "pkg:pypi/six@1.17.0", resources
        )
        self.assertEqual({matchcode_match, scanoss_match}, set(origin_matches))

    def test_scanpipe_pipes_origin_get_origin_packages(self):
        make_package(self.project1, "pkg:npm/ms@2.1.3")
        origin_package = make_package(
            self.project1,
            "pkg:pypi/six@1.17.0",
            datasource_ids=[origin.ORIGIN_DATASOURCE_ID],
        )
        self.assertQuerySetEqual(
            origin.get_origin_packages(self.project1), [origin_package]
        )

    def test_scanpipe_pipes_origin_get_scan_package(self):
        purl = "pkg:maven/org.slf4j/slf4j-nop@2.0.16"
        self.assertIsNone(origin.get_scan_package(self.project1, purl))

        make_package(
            self.project1,
            "pkg:maven/org.slf4j/slf4j-nop@2.0.16",
            datasource_ids=[origin.ORIGIN_DATASOURCE_ID],
        )
        make_package(self.project1, "pkg:maven/org.slf4j/slf4j-nop@2.0.15")
        self.assertIsNone(origin.get_scan_package(self.project1, purl))

        sources_package = make_package(
            self.project1, "pkg:maven/org.slf4j/slf4j-nop@2.0.16?classifier=sources"
        )
        self.assertEqual(sources_package, origin.get_scan_package(self.project1, purl))

        jar_package = make_package(
            self.project1, "pkg:maven/org.slf4j/slf4j-nop@2.0.16?type=jar"
        )
        no_qualifiers_package = make_package(
            self.project1, "pkg:maven/org.slf4j/slf4j-nop@2.0.16"
        )
        self.assertEqual(
            no_qualifiers_package, origin.get_scan_package(self.project1, purl)
        )

        jar_purl = "pkg:maven/org.slf4j/slf4j-nop@2.0.16?type=jar"
        self.assertEqual(jar_package, origin.get_scan_package(self.project1, jar_purl))

    def test_scanpipe_pipes_origin_get_or_create_origin_package(self):
        scan_package = make_package(self.project1, "pkg:npm/ms@2.1.3")
        resources = self.project1.codebaseresources.all()
        package = origin.get_or_create_origin_package(
            self.project1, "pkg:npm/ms@2.1.3", resources
        )
        self.assertEqual(scan_package, package)

        # Regression test: the scan package with qualifiers was not found.
        sources_package = make_package(
            self.project1, "pkg:maven/org.slf4j/slf4j-nop@2.0.16?classifier=sources"
        )
        package = origin.get_or_create_origin_package(
            self.project1, "pkg:maven/org.slf4j/slf4j-nop@2.0.16", resources
        )
        self.assertEqual(sources_package, package)

        resource = make_resource_file(self.project1, path="six.py")
        self.make_origin_match(
            resource,
            "pkg:pypi/six@1.17.0",
            extra_data={"declared_license_expression": "mit"},
        )
        package = origin.get_or_create_origin_package(
            self.project1, "pkg:pypi/six@1.17.0", resources
        )
        self.assertEqual("pkg:pypi/six@1.17.0", package.purl)
        self.assertEqual("mit", package.declared_license_expression)
        self.assertEqual([origin.ORIGIN_DATASOURCE_ID], package.datasource_ids)

    def test_scanpipe_pipes_origin_get_determined_resources(self):
        vendor_ms = make_resource_directory(self.project1, path="vendor/ms")
        index_js = make_resource_file(self.project1, path="vendor/ms/index.js")
        debounce_js = make_resource_file(self.project1, path="vendor/ms/debounce.js")
        make_resource_file(self.project1, path="vendor/other.js")
        directory_determination = OriginDetermination.objects.create(
            project=self.project1,
            resource=vendor_ms,
            purl="pkg:npm/ms@2.1.3",
            status=OriginDetermination.Status.AUTO_CONFIRMED,
        )
        OriginDetermination.objects.create(
            project=self.project1,
            resource=debounce_js,
            status=OriginDetermination.Status.NEEDS_REVIEW,
        )

        resources = origin.get_determined_resources(
            self.project1, [directory_determination], ["vendor/ms"]
        )
        self.assertQuerySetEqual(resources.order_by("path"), [vendor_ms, index_js])

    def test_scanpipe_pipes_origin_get_determined_resources_nested_directories(self):
        vendor = make_resource_directory(self.project1, path="vendor")
        foo_js = make_resource_file(self.project1, path="vendor/foo.js")
        vendor_ms = make_resource_directory(self.project1, path="vendor/ms")
        make_resource_file(self.project1, path="vendor/ms/index.js")
        vendor_determination = OriginDetermination.objects.create(
            project=self.project1,
            resource=vendor,
            purl="pkg:npm/foo@1.0.0",
            status=OriginDetermination.Status.AUTO_CONFIRMED,
        )
        OriginDetermination.objects.create(
            project=self.project1,
            resource=vendor_ms,
            status=OriginDetermination.Status.NEEDS_REVIEW,
        )

        resources = origin.get_determined_resources(
            self.project1, [vendor_determination], ["vendor", "vendor/ms"]
        )
        self.assertQuerySetEqual(resources.order_by("path"), [vendor, foo_js])

    def test_scanpipe_pipes_origin_get_descendants_filter(self):
        make_resource_directory(self.project1, path="vendor")
        foo_js = make_resource_file(self.project1, path="vendor/foo.js")
        index_js = make_resource_file(self.project1, path="src/index.js")
        resources = self.project1.codebaseresources.order_by("path")

        descendants_filter = origin.get_descendants_filter(["vendor", "src"])
        self.assertQuerySetEqual(
            resources.filter(descendants_filter), [index_js, foo_js]
        )
        self.assertQuerySetEqual(
            resources.filter(origin.get_descendants_filter([])), []
        )
        self.assertEqual(
            3, resources.exclude(origin.get_descendants_filter([])).count()
        )

    def test_scanpipe_pipes_origin_get_determined_directory_paths(self):
        vendor = make_resource_directory(self.project1, path="vendor")
        make_resource_directory(self.project1, path="src")
        six_resource = make_resource_file(self.project1, path="six.py")
        for resource in [vendor, six_resource]:
            OriginDetermination.objects.create(
                project=self.project1,
                resource=resource,
                status=OriginDetermination.Status.NEEDS_REVIEW,
            )

        paths = origin.get_determined_directory_paths(self.project1)
        self.assertEqual(["vendor"], paths)

    def test_scanpipe_pipes_origin_assign_origin_packages(self):
        vendor_ms = make_resource_directory(self.project1, path="vendor/ms")
        index_js = make_resource_file(self.project1, path="vendor/ms/index.js")
        six_resource = make_resource_file(self.project1, path="six.py")
        ini_resource = make_resource_file(self.project1, path="ini.c")
        OriginDetermination.objects.create(
            project=self.project1,
            resource=vendor_ms,
            purl="pkg:npm/ms@2.1.3",
            status=OriginDetermination.Status.AUTO_CONFIRMED,
        )
        OriginDetermination.objects.create(
            project=self.project1,
            resource=six_resource,
            purl="pkg:pypi/six@1.17.0",
            status=OriginDetermination.Status.CONFIRMED,
        )
        OriginDetermination.objects.create(
            project=self.project1,
            resource=ini_resource,
            purl="pkg:github/benhoyt/inih@r62",
            status=OriginDetermination.Status.NEEDS_REVIEW,
        )

        self.assertEqual(2, origin.assign_origin_packages(self.project1))
        packages = self.project1.discoveredpackages.order_by("type")
        package_resources = [
            (
                package.purl,
                sorted(package.codebase_resources.values_list("path", flat=True)),
            )
            for package in packages
        ]
        expected = [
            ("pkg:npm/ms@2.1.3", [vendor_ms.path, index_js.path]),
            ("pkg:pypi/six@1.17.0", [six_resource.path]),
        ]
        self.assertEqual(expected, package_resources)

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
            # The r62 release is preferred over the 498f34b commit.
            "modified-copy": [
                (
                    "src/inih/ini.c",
                    "pkg:github/benhoyt/inih@r62",
                    "needs-review",
                    origin.PREFERRED_VERSION_RULE,
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
            # The origin six and pip, which vendors six, are both reported.
            "shared-copy": [
                (
                    "third_party/six.py",
                    "pkg:pypi/six@1.16.0",
                    "needs-review",
                    origin.CONTAINMENT_RULE,
                ),
            ],
            "embedded-archive": [
                (
                    "jars/slf4j-nop-2.0.16.jar",
                    "pkg:maven/org.slf4j/slf4j-nop@2.0.16",
                    "auto-confirmed",
                    origin.CONFIRMED_BY_TWO_TOOLS_RULE,
                ),
            ],
            "single-tool-copy": [
                (
                    "static/js/escape-html.js",
                    "pkg:github/component/escape-html@v1.0.3",
                    "needs-review",
                    origin.SINGLE_TOOL_RULE,
                ),
            ],
            # The license header snippet matches are too short to count.
            "license-header": [],
        }

        expected_packages_by_case = {
            "exact-copy": [("pkg:pypi/six@1.17.0", "mit", ["myapp/_vendor/six.py"])],
            "modified-copy": [
                ("pkg:github/benhoyt/inih@r62", "bsd-new", ["src/inih/ini.h"])
            ],
            "embedded-package": [
                (
                    "pkg:npm/ms@2.1.3",
                    "mit",
                    [
                        "vendor/ms",
                        "vendor/ms/index.js",
                        "vendor/ms/license.md",
                        "vendor/ms/package.json",
                        "vendor/ms/readme.md",
                    ],
                )
            ],
            "embedded-archive": [
                (
                    "pkg:maven/org.slf4j/slf4j-nop@2.0.16",
                    "mit",
                    ["jars/slf4j-nop-2.0.16.jar"],
                )
            ],
        }

        for case_name, expected in expected_by_case.items():
            with self.subTest(case_name):
                project = self.load_data_set_case(case_name)
                origin.determine_origins(project)

                packages = [
                    (
                        package.purl,
                        package.declared_license_expression,
                        sorted(
                            package.codebase_resources.values_list("path", flat=True)
                        ),
                    )
                    for package in project.discoveredpackages.all()
                ]
                self.assertEqual(expected_packages_by_case.get(case_name, []), packages)

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

    def test_scanpipe_pipes_origin_determine_origins_data_set_single_tool(self):
        expected_by_tool = {
            matchcode.TOOL_NAME: {
                "exact-copy": [
                    ("myapp/_vendor/six.py", "pkg:pypi/six@1.17.0", "single-tool"),
                ],
                # The vendoring package is reported instead of the six origin.
                "vendored-copy": [
                    (
                        "myapp/_vendor/urllib3/packages/six.py",
                        "pkg:pypi/urllib3@1.26.20",
                        "single-tool",
                    ),
                ],
                "modified-copy": [
                    ("src/inih/ini.c", "pkg:github/benhoyt/inih@r62", "no-exact-match"),
                    ("src/inih/ini.h", "pkg:github/benhoyt/inih@r62", "single-tool"),
                ],
                "snippet": [
                    ("src/scheduler.js", "pkg:npm/lodash@4.17.21", "no-exact-match"),
                ],
                "embedded-package": [
                    ("vendor/ms", "pkg:npm/ms@2.1.3", "no-exact-match"),
                ],
                "no-origin": [],
                "shared-copy": [
                    ("third_party/six.py", "pkg:pypi/six@1.16.0", "containment"),
                ],
                "embedded-archive": [
                    (
                        "jars/slf4j-nop-2.0.16.jar",
                        "pkg:maven/org.slf4j/slf4j-nop@2.0.16",
                        "single-tool",
                    ),
                ],
                # Not in the MatchCode.io index.
                "single-tool-copy": [],
                "license-header": [],
            },
            scanoss.TOOL_NAME: {
                "exact-copy": [
                    (
                        "myapp/_vendor/six.py",
                        "pkg:github/benjaminp/six@1.17.0",
                        "single-tool",
                    ),
                ],
                "vendored-copy": [
                    (
                        "myapp/_vendor/urllib3/packages/six.py",
                        "pkg:github/piotrmasek/anime365@0.1-Ryucon",
                        "single-tool",
                    ),
                ],
                "modified-copy": [
                    (
                        "src/inih/ini.c",
                        "pkg:github/benhoyt/inih@498f34b",
                        "no-exact-match",
                    ),
                    ("src/inih/ini.h", "pkg:github/benhoyt/inih@r62", "single-tool"),
                ],
                "snippet": [],
                "embedded-package": [
                    ("vendor/ms/index.js", "pkg:github/vercel/ms@2.1.3", "single-tool"),
                ],
                "no-origin": [],
                "shared-copy": [
                    (
                        "third_party/six.py",
                        "pkg:github/benjaminp/six@1.16.0",
                        "single-tool",
                    ),
                ],
                "embedded-archive": [
                    (
                        "jars/slf4j-nop-2.0.16.jar",
                        "pkg:maven/org.slf4j/slf4j-nop@2.0.16",
                        "single-tool",
                    ),
                ],
                "single-tool-copy": [
                    (
                        "static/js/escape-html.js",
                        "pkg:github/component/escape-html@v1.0.3",
                        "single-tool",
                    ),
                ],
                "license-header": [],
            },
        }

        for tool, expected_by_case in expected_by_tool.items():
            for case_name, expected in expected_by_case.items():
                with self.subTest(tool=tool, case_name=case_name):
                    project = self.load_data_set_case(case_name, tools=[tool])
                    origin.determine_origins(project)

                    determinations = project.origindeterminations.order_by(
                        "resource__path"
                    )
                    values = determinations.values_list(
                        "resource__path", "purl", "rule"
                    )
                    self.assertEqual(expected, list(values))
                    # A single tool can miss a conflicting candidate.
                    statuses = set(determinations.values_list("status", flat=True))
                    self.assertNotIn("auto-confirmed", statuses)
                    self.assertFalse(project.discoveredpackages.exists())

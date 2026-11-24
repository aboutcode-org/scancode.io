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

import tempfile
from pathlib import Path
from unittest import mock
from unittest import skipIf

from django.test import TestCase

from packageurl import PackageURL

from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import flag
from scanpipe.pipes import yara
from scanpipe.pipes.yara import MatchedString
from scanpipe.pipes.yara import MatchResult
from scanpipe.tests import make_resource_file


@skipIf(not yara.is_available(), "yara-python is required to run YARA tests.")
class ScanPipeYaraPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="yara_test_project")
        self.rules_dir = yara.DEFAULT_RULES_DIR

    def test_scanpipe_pipes_yara_is_available(self):
        self.assertTrue(yara.is_available())
        with mock.patch("scanpipe.pipes.yara.yara", None):
            self.assertFalse(yara.is_available())

    def test_scanpipe_pipes_yara_compile_rules(self):
        rules = yara.compile_rules()
        expected_identifiers = {
            "jq_detection",
            "libass_detection",
            "libcurl_detection",
            "openssl_detection",
        }
        self.assertEqual(expected_identifiers, {rule.identifier for rule in rules})

        with self.assertRaises(yara.InvalidYaraRules):
            yara.compile_rules(rules_directory="/nonexistent/rules_dir")

        with self.assertRaises(yara.InvalidYaraRules):
            yara.compile_rules(rules_directory=self.rules_dir / "jq.yar")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test empty rules directory
            with self.assertRaisesMessage(
                yara.InvalidYaraRules, "No .yar rule files found in directory"
            ):
                yara.compile_rules(rules_directory=temp_path)

            rule_file = temp_path / "test.yar"

            # Test syntax error
            rule_file.write_text("rule bad { strings: $a = /regex[ condition: $a }")
            with self.assertRaisesMessage(
                yara.InvalidYaraRules, "Failed to compile YARA rules"
            ):
                yara.compile_rules(rules_directory=temp_path)

            # Test missing base_purl
            rule_file.write_text('rule zlib { strings: $a = "zlib" condition: $a }')
            with self.assertRaisesMessage(
                yara.InvalidYaraRules, "Rule zlib is missing base_purl."
            ):
                yara.compile_rules(rules_directory=temp_path)

            # Test invalid base_purl
            rule_file.write_text(
                'rule zlib { meta: base_purl = "invalid-purl" condition: true }'
            )
            with self.assertRaisesMessage(
                yara.InvalidYaraRules, "Rule zlib has an invalid base_purl"
            ):
                yara.compile_rules(rules_directory=temp_path)

    def test_scanpipe_pipes_yara_scan_file_error(self):
        mock_rules = mock.Mock()
        mock_rules.match.side_effect = yara.yara.Error("Matching failed")
        with self.assertRaisesMessage(yara.yara.Error, "Matching failed"):
            yara.scan_file(location="src/error.c", rules=mock_rules)

    def test_scanpipe_pipes_yara_extract_version(self):
        extract = yara.extract_version
        self.assertEqual(
            "1.1.1x",
            extract(['define OPENSSL_VERSION_TEXT  "OpenSSL 1.1.1x  25 Jan 2024"']),
        )
        self.assertEqual("7.55.1", extract(['#define LIBCURL_VERSION "7.55.1"']))
        self.assertEqual(
            "1.10.5",
            extract(["project(cpr VERSION 1.10.5 LANGUAGES CXX)"]),
        )
        self.assertIsNone(extract(["constant string with no digits"]))
        self.assertIsNone(extract([]))

    @mock.patch("scanpipe.pipes.yara.compile_rules")
    def test_scanpipe_pipes_yara_match_resources_by_yara_empty_codebase(
        self, mock_compile_rules
    ):
        yara.match_resources_by_yara(self.project1)
        mock_compile_rules.assert_not_called()

    def test_scanpipe_pipes_yara_match_resources_by_yara(self):
        jq_code = (
            "/* jq - commandline JSON processor */\n"
            "/* jq-1.7.1 */\n"
            "void jq_init() {}\n"
            "void jq_compile() {}\n"
        )
        (self.project1.codebase_path / "jq_main.c").write_text(jq_code)
        (self.project1.codebase_path / "other.c").write_text(
            "int add(int a, int b) { return a + b; }\n"
        )

        matching_resource = make_resource_file(self.project1, "jq_main.c")
        other_resource = make_resource_file(self.project1, "other.c")

        mock_logger = mock.Mock()
        yara.match_resources_by_yara(self.project1, logger=mock_logger)

        matching_resource.refresh_from_db()
        other_resource.refresh_from_db()

        # Verify resource flags & extra_data
        self.assertEqual(flag.MATCHED_BY_YARA_RULE, matching_resource.status)
        self.assertEqual("yara", matching_resource.extra_data["matched_by"])
        self.assertEqual(["jq_detection"], matching_resource.extra_data["yara_rules"])
        self.assertIn(
            "$sym1",
            matching_resource.extra_data["matched_strings"]["jq_detection"],
        )

        self.assertEqual("", other_resource.status)
        self.assertNotIn("matched_by", other_resource.extra_data)

        # Verify discovered package creation and resource relationship
        packages = self.project1.discoveredpackages.all()
        self.assertEqual(1, packages.count())
        package = packages.first()
        self.assertEqual("generic", package.type)
        self.assertEqual("jq", package.name)
        self.assertEqual("1.7.1", package.version)
        self.assertEqual("pkg:generic/jq@1.7.1", package.package_url)
        self.assertNotIn("matched_by", package.extra_data)
        self.assertIn(matching_resource, package.codebase_resources.all())
        self.assertNotIn(other_resource, package.codebase_resources.all())

    @mock.patch("scanpipe.pipes.yara.scan_file")
    def test_scanpipe_pipes_yara_match_resources_by_yara_multiple_matches(
        self, mock_scan_file
    ):
        mock_scan_file.return_value = [
            MatchResult(
                rule="libcurl_detection",
                purl=PackageURL.from_string("pkg:generic/libcurl@1.0.0"),
                version="1.0.0",
                matched_strings=[MatchedString("$s1", "str1")],
            ),
            MatchResult(
                rule="openssl_detection",
                purl=PackageURL.from_string("pkg:generic/openssl@2.0.0"),
                version="2.0.0",
                matched_strings=[MatchedString("$s2", "str2")],
            ),
        ]
        resource = make_resource_file(self.project1, "src/multiple_matches.c")

        yara.match_resources_by_yara(self.project1)

        resource.refresh_from_db()
        self.assertEqual(flag.MATCHED_BY_YARA_RULE, resource.status)
        self.assertEqual(
            ["libcurl_detection", "openssl_detection"],
            resource.extra_data["yara_rules"],
        )
        self.assertIn(
            "$s1", resource.extra_data["matched_strings"]["libcurl_detection"]
        )
        self.assertIn(
            "$s2", resource.extra_data["matched_strings"]["openssl_detection"]
        )

        packages = self.project1.discoveredpackages.all()
        self.assertEqual(2, packages.count())
        self.assertEqual(
            {"libcurl", "openssl"},
            set(packages.values_list("name", flat=True)),
        )
        for package in packages:
            self.assertIn(resource, package.codebase_resources.all())

    @mock.patch("scanpipe.pipes.yara.scan_file")
    def test_scanpipe_pipes_yara_match_resources_different_versions(
        self, mock_scan_file
    ):
        resource1 = make_resource_file(self.project1, "src/openssl_v1.c")
        resource2 = make_resource_file(self.project1, "src/openssl_v2.c")

        def side_effect(location, rules):
            if "openssl_v1.c" in location:
                return [
                    MatchResult(
                        rule="openssl_detection",
                        purl=PackageURL.from_string("pkg:generic/openssl@1.0.0"),
                        version="1.0.0",
                        matched_strings=[],
                    )
                ]
            return [
                MatchResult(
                    rule="openssl_detection",
                    purl=PackageURL.from_string("pkg:generic/openssl@2.0.0"),
                    version="2.0.0",
                    matched_strings=[],
                )
            ]

        mock_scan_file.side_effect = side_effect
        yara.match_resources_by_yara(self.project1)

        packages = self.project1.discoveredpackages.all().order_by("version")
        self.assertEqual(2, packages.count())
        package_v1, package_v2 = packages
        self.assertEqual("1.0.0", package_v1.version)
        self.assertEqual([resource1], list(package_v1.codebase_resources.all()))
        self.assertEqual("2.0.0", package_v2.version)
        self.assertEqual([resource2], list(package_v2.codebase_resources.all()))

    @mock.patch("scanpipe.pipes.yara.scan_file")
    def test_scanpipe_pipes_yara_match_existing_package(self, mock_scan_file):
        existing_package = DiscoveredPackage.create_from_data(
            project=self.project1,
            package_data={"type": "generic", "name": "jq", "version": "1.0.0"},
        )
        self.assertEqual(1, self.project1.discoveredpackages.count())
        self.assertEqual(0, existing_package.codebase_resources.count())

        resource = make_resource_file(self.project1, "src/jq_main.c")
        mock_scan_file.return_value = [
            MatchResult(
                rule="jq_detection",
                purl=PackageURL.from_string("pkg:generic/jq@1.0.0"),
                version="1.0.0",
                matched_strings=[],
            )
        ]

        yara.match_resources_by_yara(self.project1)

        # Ensure existing package was reused and not duplicated
        self.assertEqual(1, self.project1.discoveredpackages.count())
        existing_package.refresh_from_db()
        self.assertIn(resource, existing_package.codebase_resources.all())

    @mock.patch("scanpipe.pipes.yara.scan_file")
    def test_scanpipe_pipes_yara_match_resources_by_yara_without_version(
        self, mock_scan_file
    ):
        resource = make_resource_file(self.project1, "src/libcurl_main.c")
        mock_scan_file.return_value = [
            MatchResult(
                rule="libcurl_detection",
                purl=PackageURL.from_string("pkg:generic/libcurl"),
                version=None,
                matched_strings=[],
            )
        ]

        yara.match_resources_by_yara(self.project1)

        packages = self.project1.discoveredpackages.all()
        self.assertEqual(1, packages.count())
        package = packages.first()
        self.assertEqual("generic", package.type)
        self.assertEqual("libcurl", package.name)
        self.assertEqual("", package.version)
        self.assertEqual("pkg:generic/libcurl", package.package_url)
        self.assertIn(resource, package.codebase_resources.all())

    @mock.patch("scanpipe.pipes.yara.scan_file")
    def test_scanpipe_pipes_yara_match_resources_by_yara_scan_error(
        self, mock_scan_file
    ):
        mock_scan_file.side_effect = yara.yara.Error("Scanning failed")
        make_resource_file(self.project1, "src/error.c")

        yara.match_resources_by_yara(self.project1)

        project_messages = self.project1.projectmessages.all()
        self.assertEqual(1, len(project_messages))
        self.assertEqual("Scanning failed", project_messages[0].description)

# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.

from pathlib import Path
from unittest import mock
from unittest import skipIf

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import flag
from scanpipe.pipes import yara
from scanpipe.tests import make_resource_file


@skipIf(not yara.is_available(), "yara-python is required to run YARA tests.")
class ScanPipeYaraPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="yara_test_project")
        self.rules_dir = self.data / "yara_rules"

    def test_yara_package_scanner_initialization(self):
        scanner = yara.YaraPackageScanner()
        self.assertIsNotNone(scanner.rules)

        with self.assertRaises(yara.InvalidYaraRules):
            yara.YaraPackageScanner(rule_path="/nonexistent/rules_dir")

        with self.assertRaises(yara.InvalidYaraRules):
            yara.YaraPackageScanner(rule_path=self.rules_dir / "jq.yar")

    def test_yara_package_scanner_extract_version(self):
        extract = yara.YaraPackageScanner._extract_version
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

    def test_match_resources_by_yara(self):
        matching_resource = make_resource_file(self.project1, "src/jq_main.c")
        matching_resource.location_path.parent.mkdir(parents=True, exist_ok=True)
        matching_resource.location_path.write_text(
            "/* jq - commandline JSON processor */\n"
            "/* jq-1.7.1 */\n"
            "void jq_init() {}\n"
            "void jq_compile() {}\n"
        )

        other_resource = make_resource_file(self.project1, "src/other.c")
        other_resource.location_path.write_text(
            "int add(int a, int b) { return a + b; }\n"
        )

        mock_logger = mock.Mock()
        yara.match_resources_by_yara(self.project1, logger=mock_logger)

        matching_resource.refresh_from_db()
        other_resource.refresh_from_db()

        # Verify resource flags & extra_data
        self.assertEqual(flag.MATCHED_BY_YARA_RULE, matching_resource.status)
        self.assertEqual("yara", matching_resource.extra_data.get("matched_by"))
        self.assertEqual("jq_detection", matching_resource.extra_data.get("yara_rule"))
        self.assertIn("$sym1", matching_resource.extra_data.get("matched_strings", {}))

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
        self.assertEqual(
            {"matched_by": "yara", "yara_rule": "jq_detection"},
            {
                key: package.extra_data[key]
                for key in ["matched_by", "yara_rule"]
                if key in package.extra_data
            },
        )
        self.assertIn(matching_resource, package.codebase_resources.all())
        self.assertNotIn(other_resource, package.codebase_resources.all())

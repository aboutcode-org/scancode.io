# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import os

from commoncode.testcase import FileBasedTesting
from licensedcode import match
from licensedcode import models
from licensedcode.spans import Span

from scantext.match_text import get_build_colors
from scantext.match_text import get_license_keys_count
from scantext.match_text import get_rule_text_url

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

SCANCODE_BASE_URL = (
    "https://github.com/nexB/scancode-toolkit/tree/develop/src/licensedcode/data"
)


class TestScantextViews(FileBasedTesting):
    test_data_dir = TEST_DATA_DIR

    def test_get_license_keys_count(self):
        rule1 = models.Rule(license_expression="Apache-2.0", stored_text="1")
        rule2 = models.Rule(license_expression="Apache-2.0 OR MIT", stored_text="2")
        rule3 = models.Rule(license_expression="BSD AND GPL", stored_text="3")

        match1 = match.LicenseMatch(rule=rule1, ispan=Span(), qspan=Span())
        match2 = match.LicenseMatch(rule=rule2, ispan=Span(), qspan=Span())
        match3 = match.LicenseMatch(rule=rule3, ispan=Span(), qspan=Span())
        matches = [match1, match2, match3]

        response = get_license_keys_count(matches)
        expected = 4
        self.assertEqual(response, expected)

    def test_get_rule_text_url_for_rule(self):
        rule1 = models.Rule(license_expression="Apache-2.0", stored_text="1")
        rule1.identifier = "Apache-2.0.RULE"

        response = get_rule_text_url(rule=rule1, base_url="http://example.com")
        expected = "http://example.com/rules/Apache-2.0.RULE"
        self.assertEqual(response, expected)

    def test_get_rule_text_url_for_license(self):
        rule1 = models.Rule(
            license_expression="Apache-2.0", stored_text="1", is_from_license=True
        )
        rule1.identifier = "Apache-2.0.LICENSE"

        response = get_rule_text_url(rule=rule1, base_url="http://example.com")
        expected = "http://example.com/licenses/Apache-2.0.LICENSE"
        self.assertEqual(response, expected)

    def test_get_rule_text_url_for_spdx(self):
        rule1 = models.SpdxRule(license_expression="Apache-2.0", stored_text="1")
        response = get_rule_text_url(rule=rule1, base_url="http://example.com")
        self.assertIsNone(response)

    def test_get_rule_text_url_for_unknown(self):
        rule1 = models.UnknownRule(license_expression="Apache-2.0", stored_text="1")
        response = get_rule_text_url(rule=rule1, base_url="http://example.com")
        self.assertIsNone(response)

    def test_get_rule_text_url_with_default_base_url(self):
        rule1 = models.Rule(license_expression="apache-2.0 or mit", stored_text="1")
        rule1.identifier = "apache-2.0_or_mit_48.RULE"

        response = get_rule_text_url(rule=rule1)
        expected = SCANCODE_BASE_URL + "/rules/apache-2.0_or_mit_48.RULE"
        self.assertEqual(response, expected)

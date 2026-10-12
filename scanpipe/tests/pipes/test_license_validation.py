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

from unittest import mock

from django.test import TestCase

from license_expression import Licensing

from scanpipe.pipes import flag
from scanpipe.pipes import license_validation


class ScanPipeLicenseValidationTest(TestCase):
    def setUp(self):
        self.licensing = Licensing()

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_validate_package_license_integrity_mismatch(
        self, mock_match_is_license_text
    ):
        mock_match_is_license_text.return_value = False

        mock_project = mock.Mock()
        mock_package = mock.Mock()
        mock_resource = mock.Mock()
        mock_data_path = mock.Mock()

        mock_package.type = "pypi"
        mock_package.package_uid = "pkg:pypi/test@1.0"
        mock_package.get_declared_license_expression.return_value = "mit"
        mock_package.datafile_paths = ["src/main.py"]
        mock_package.extra_data = {}

        mock_project.discoveredpackages.all.return_value = [mock_package]

        mock_resource.path = "src/main.py"
        mock_resource.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource.license_detections = [
            {
                "license_expression": "gpl-3.0",
                "matches": [
                    {
                        "license_expression": "gpl-3.0",
                        "rule_identifier": "test",
                    }
                ],
            }
        ]

        from_codebase_qs = mock_project.codebaseresources.from_codebase.return_value
        from_codebase_qs.has_license_expression.return_value = [mock_resource]

        mock_data_path.extra_data = {}
        mock_project.codebaseresources.get.return_value = mock_data_path

        license_validation.validate_package_license_integrity(mock_project)

        package_update_kwargs = mock_package.update.call_args.kwargs
        self.assertEqual(
            package_update_kwargs["extra_data"]["issues"][0]["issue_type"],
            "License Mismatch",
        )
        self.assertEqual(
            package_update_kwargs["extra_data"]["issues"][0][
                "detected_codebase_license"
            ],
            "gpl-3.0",
        )
        self.assertTrue(package_update_kwargs["has_license_issue"])

        mock_data_path.update.assert_called_once_with(status=flag.LICENSE_ISSUE)

    def test_contains_ignore_pattern(self):
        ignore_patterns = license_validation.LICENSE_VALIDATION_IGNORE_PATTERNS
        self.assertTrue(
            license_validation.contains_ignore_pattern(
                "project/test/test_main.py", ignore_patterns
            )
        )
        self.assertTrue(
            license_validation.contains_ignore_pattern(
                "project/scripts/build.sh", ignore_patterns
            )
        )
        self.assertFalse(
            license_validation.contains_ignore_pattern(
                "project/src/main.py", ignore_patterns
            )
        )

    def test_filter_ignored_licenses(self):
        exp1 = self.licensing.parse("mit")
        self.assertEqual(
            str(license_validation.filter_ignored_licenses(exp1, self.licensing)),
            "mit",
        )
        exp2 = self.licensing.parse("unknown")
        self.assertIsNone(
            license_validation.filter_ignored_licenses(exp2, self.licensing)
        )
        exp3 = self.licensing.parse("mit AND unknown")
        self.assertEqual(
            str(license_validation.filter_ignored_licenses(exp3, self.licensing)),
            "mit",
        )
        exp4 = self.licensing.parse("unknown-spdx OR free-unknown")
        self.assertIsNone(
            license_validation.filter_ignored_licenses(exp4, self.licensing)
        )

    def test_handle_operator_expression_and(self):
        expr = self.licensing.parse("mit AND apache-2.0")
        result = license_validation.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertEqual(str(result), "mit AND apache-2.0")

    def test_handle_operator_expression_or(self):
        expr = self.licensing.parse("mit OR bsd-3-clause")
        result = license_validation.handle_operator_expression(
            expr, self.licensing, self.licensing.OR
        )
        self.assertEqual(str(result), "mit OR bsd-3-clause")

    def test_handle_operator_expression_filters_to_single_arg(self):
        expr = self.licensing.parse("mit AND unknown")
        result = license_validation.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertEqual(str(result), "mit")

    def test_handle_operator_expression_all_filtered_out(self):
        expr = self.licensing.parse("unknown AND free-unknown")
        result = license_validation.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertIsNone(result)

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_collect_detected_licenses(self, mock_match_is_license_text):
        mock_match_is_license_text.return_value = False

        mock_resource1 = mock.Mock()
        mock_resource1.path = "project/src/main.py"
        mock_resource1.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource1.license_detections = [
            {
                "license_expression": "mit",
                "matches": [{"license_expression": "mit", "rule_identifier": "t"}],
            }
        ]

        mock_resource2 = mock.Mock()
        mock_resource2.path = "project/test/test_main.py"
        mock_resource2.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource2.license_detections = [
            {
                "license_expression": "gpl-3.0",
                "matches": [{"license_expression": "gpl-3.0", "rule_identifier": "t"}],
            }
        ]

        mock_resource3 = mock.Mock()
        mock_resource3.path = "project/src/other.py"
        mock_resource3.for_packages = ["pkg:pypi/test@2.0"]
        mock_resource3.license_detections = [
            {
                "license_expression": "apache-2.0",
                "matches": [
                    {"license_expression": "apache-2.0", "rule_identifier": "t"}
                ],
            }
        ]

        resources = [mock_resource1, mock_resource2, mock_resource3]
        ignore_patterns = license_validation.LICENSE_VALIDATION_IGNORE_PATTERNS

        result = license_validation.collect_detected_licenses(
            resources, ignore_patterns, package_uid="pkg:pypi/test@1.0"
        )
        self.assertEqual(str(result), "mit")

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_collect_detected_licenses_text_or_group(self, mock_match_is_license_text):
        mock_match_is_license_text.return_value = True

        resource1 = mock.Mock()
        resource1.path = "COPYING"
        resource1.for_packages = []
        resource1.license_detections = [
            {
                "license_expression": "apache-2.0",
                "matches": [
                    {"license_expression": "apache-2.0", "rule_identifier": "a"}
                ],
            }
        ]

        resource2 = mock.Mock()
        resource2.path = "COPYING.LESSER"
        resource2.for_packages = []
        resource2.license_detections = [
            {
                "license_expression": "lgpl-2.1",
                "matches": [{"license_expression": "lgpl-2.1", "rule_identifier": "b"}],
            }
        ]

        result = license_validation.collect_detected_licenses(
            [resource1, resource2], []
        )
        self.assertTrue(self.licensing.is_equivalent(result, "apache-2.0 OR lgpl-2.1"))

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_collect_detected_licenses_text_and_other_groups(
        self, mock_match_is_license_text
    ):
        text_by_rule = {
            "apache-2.0.LICENSE": True,
            "mit.LICENSE": True,
            "mit_or_apache-2.0_18.RULE": False,
        }

        def is_license_text(match):
            return text_by_rule[match["rule_identifier"]]

        mock_match_is_license_text.side_effect = is_license_text

        resource1 = mock.Mock()
        resource1.path = "LICENSE-APACHE"
        resource1.for_packages = []
        resource1.license_detections = [
            {
                "license_expression": "apache-2.0",
                "matches": [
                    {
                        "license_expression": "apache-2.0",
                        "rule_identifier": "apache-2.0.LICENSE",
                    }
                ],
            }
        ]

        resource2 = mock.Mock()
        resource2.path = "LICENSE-MIT"
        resource2.for_packages = []
        resource2.license_detections = [
            {
                "license_expression": "mit",
                "matches": [
                    {"license_expression": "mit", "rule_identifier": "mit.LICENSE"}
                ],
            }
        ]

        resource3 = mock.Mock()
        resource3.path = "README.md"
        resource3.for_packages = []
        resource3.license_detections = [
            {
                "license_expression": "bsd-new",
                "matches": [
                    {
                        "license_expression": "bsd-new",
                        "rule_identifier": "mit_or_apache-2.0_18.RULE",
                    }
                ],
            }
        ]

        result = license_validation.collect_detected_licenses(
            [resource1, resource2, resource3], []
        )
        self.assertTrue(
            self.licensing.is_equivalent(result, "(apache-2.0 OR mit) AND bsd-new")
        )

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_collect_detected_licenses_ignored_expression(
        self, mock_match_is_license_text
    ):
        mock_match_is_license_text.return_value = False

        resource = mock.Mock()
        resource.path = "src/main.py"
        resource.for_packages = []
        resource.license_detections = [
            {
                "license_expression": "unknown",
                "matches": [
                    {
                        "license_expression": "unknown",
                        "rule_identifier": "a",
                    }
                ],
            }
        ]

        result = license_validation.collect_detected_licenses([resource], [])

        self.assertIsNone(result)

    @mock.patch("scanpipe.pipes.license_validation.get_index")
    def test_match_is_license_text(self, mock_get_index):
        mock_rule_text = mock.Mock()
        mock_rule_text.is_license_text = True

        mock_rule_notice = mock.Mock()
        mock_rule_notice.is_license_text = False

        mock_index = mock.Mock()
        mock_index.rules_by_id = {
            "apache-2.0.LICENSE": mock_rule_text,
            "some-notice.RULE": mock_rule_notice,
        }
        mock_get_index.return_value = mock_index

        self.assertTrue(
            license_validation.match_is_license_text(
                {"rule_identifier": "apache-2.0.LICENSE"}
            )
        )
        self.assertFalse(
            license_validation.match_is_license_text(
                {"rule_identifier": "some-notice.RULE"}
            )
        )
        self.assertFalse(
            license_validation.match_is_license_text(
                {"rule_identifier": "unknown.RULE"}
            )
        )
        self.assertFalse(license_validation.match_is_license_text({}))

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_collect_match_expressions(self, mock_match_is_license_text):
        mock_match_is_license_text.return_value = False

        resource = mock.Mock()
        resource.path = "src/main.py"
        resource.license_detections = [
            {
                "matches": [
                    {
                        "license_expression": "mit",
                        "rule_identifier": "a",
                    },
                    {
                        "license_expression": "unknown",
                        "rule_identifier": "b",
                    },
                ],
            },
        ]

        results = list(
            license_validation.collect_match_expressions(resource, self.licensing)
        )

        self.assertEqual(len(results), 1)
        is_text, expression = results[0]
        self.assertFalse(is_text)
        self.assertEqual(str(expression), "mit")

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_collect_match_expressions_mixed_detection(
        self, mock_match_is_license_text
    ):
        text_by_rule = {
            "mit.LICENSE": True,
            "some-notice.RULE": False,
        }

        def is_license_text(match):
            return text_by_rule[match["rule_identifier"]]

        mock_match_is_license_text.side_effect = is_license_text

        resource = mock.Mock()
        resource.path = "src/main.rs"
        resource.license_detections = [
            {
                "license_expression": "mit AND apache-2.0",
                "matches": [
                    {
                        "license_expression": "mit",
                        "rule_identifier": "mit.LICENSE",
                    },
                    {
                        "license_expression": "apache-2.0",
                        "rule_identifier": "some-notice.RULE",
                    },
                ],
            }
        ]

        results = list(
            license_validation.collect_match_expressions(resource, self.licensing)
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], (True, self.licensing.parse("mit")))
        self.assertEqual(results[1], (False, self.licensing.parse("apache-2.0")))

    def test_combine_license_groups_text_and_other(self):
        text_licenses = [
            self.licensing.parse("mit"),
            self.licensing.parse("apache-2.0"),
        ]
        other_licenses = [self.licensing.parse("bsd-new")]

        result = license_validation.combine_license_groups(
            text_licenses, other_licenses, self.licensing
        )

        self.assertTrue(
            self.licensing.is_equivalent(result, "(mit OR apache-2.0) AND bsd-new")
        )

    def test_combine_license_groups_only_text(self):
        text_licenses = [
            self.licensing.parse("mit"),
            self.licensing.parse("apache-2.0"),
        ]

        result = license_validation.combine_license_groups(
            text_licenses, [], self.licensing
        )

        self.assertTrue(self.licensing.is_equivalent(result, "mit OR apache-2.0"))

    def test_combine_license_groups_only_other(self):
        other_licenses = [
            self.licensing.parse("bsd-new"),
            self.licensing.parse("mit"),
        ]

        result = license_validation.combine_license_groups(
            [], other_licenses, self.licensing
        )

        self.assertEqual(str(result), "bsd-new AND mit")

    def test_combine_license_groups_empty(self):
        result = license_validation.combine_license_groups([], [], self.licensing)
        self.assertIsNone(result)

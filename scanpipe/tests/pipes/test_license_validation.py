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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from unittest import mock

from django.test import TestCase

from license_expression import Licensing

from scanpipe.pipes import flag
from scanpipe.pipes import license_validation
from scanpipe.tests import make_package
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_file


def _as_detections(resources):
    """Return ``(path, license_detections)`` tuples, as the SQL query would."""
    return [(r.path, r.license_detections) for r in resources]


class ScanPipeLicenseValidationTest(TestCase):
    def setUp(self):
        self.project = make_project("license-validation")
        self.licensing = Licensing()

    @mock.patch(
        "scanpipe.pipes.license_validation.match_is_license_text",
        return_value=False,
    )
    def test_scanpipe_license_validation_validate_package_license_integrity_mismatch(
        self,
        mock_match_is_license_text,
    ):
        package = make_package(
            self.project,
            "pkg:pypi/test@1.0",
            declared_license_expression="mit",
            datafile_paths=["src/main.py"],
        )
        resource = make_resource_file(
            self.project,
            path="src/main.py",
            detected_license_expression="gpl-3.0",
            license_detections=[
                {
                    "license_expression": "gpl-3.0",
                    "matches": [
                        {
                            "license_expression": "gpl-3.0",
                            "rule_identifier": "gpl-3.0.LICENSE",
                        }
                    ],
                }
            ],
        )
        resource.update(tag="from")
        package.add_resources([resource])

        license_validation.validate_package_license_integrity(self.project)

        package.refresh_from_db()
        resource.refresh_from_db()

        self.assertTrue(package.has_license_issue)
        self.assertIn("issues", package.extra_data)
        issue = package.extra_data["issues"][0]
        self.assertEqual(issue["issue_type"], "License Mismatch")
        self.assertEqual(issue["declared_license"], "mit")
        self.assertEqual(issue["detected_codebase_license"], "gpl-3.0")

        self.assertEqual(resource.status, flag.LICENSE_MISMATCH)
        self.assertIn("issues", resource.extra_data)

    @mock.patch(
        "scanpipe.pipes.license_validation.match_is_license_text",
        return_value=True,
    )
    def test_scanpipe_license_validation_validate_package_license_integrity_no_mismatch(
        self,
        mock_match_is_license_text,
    ):
        """Declared and detected expressions match → no issue is recorded."""
        package = make_package(
            self.project,
            "pkg:pypi/test@1.0",
            declared_license_expression="mit",
        )
        resource = make_resource_file(
            self.project,
            path="src/main.py",
            detected_license_expression="mit",
            license_detections=[
                {
                    "license_expression": "mit",
                    "matches": [
                        {"license_expression": "mit", "rule_identifier": "mit.LICENSE"}
                    ],
                }
            ],
        )
        resource.update(tag="from")
        package.add_resources([resource])

        license_validation.validate_package_license_integrity(self.project)

        package.refresh_from_db()
        resource.refresh_from_db()

        self.assertFalse(package.has_license_issue)
        self.assertNotIn("issues", package.extra_data)
        self.assertNotEqual(resource.status, flag.LICENSE_MISMATCH)

    @mock.patch(
        "scanpipe.pipes.license_validation.match_is_license_text",
        return_value=True,
    )
    def test_scanpipe_license_validation_validate_package_license_integrity_cargo(
        self, mock_match_is_license_text
    ):
        """
        Cargo packages compare against all from/ resources (package_uid=None),
        even those not linked to the package. A pypi package would skip the
        same unlinked resource.
        """
        package = make_package(
            self.project,
            "pkg:cargo/test@1.0",
            declared_license_expression="mit",
        )
        resource = make_resource_file(
            self.project,
            path="src/main.rs",
            detected_license_expression="gpl-3.0",
            license_detections=[
                {
                    "license_expression": "gpl-3.0",
                    "matches": [
                        {
                            "license_expression": "gpl-3.0",
                            "rule_identifier": "gpl-3.0.LICENSE",
                        }
                    ],
                }
            ],
        )
        resource.update(tag="from")

        license_validation.validate_package_license_integrity(self.project)

        package.refresh_from_db()
        self.assertTrue(package.has_license_issue)

    @mock.patch(
        "scanpipe.pipes.license_validation.match_is_license_text",
        return_value=False,
    )
    def test_scanpipe_license_validation_ignores_patterns_at_sql_level(
        self,
        mock_match_is_license_text,
    ):
        package = make_package(
            self.project,
            "pkg:pypi/test@1.0",
            declared_license_expression="mit",
        )
        ignored = make_resource_file(
            self.project,
            path="project/test/test_main.py",
            detected_license_expression="gpl-3.0",
            license_detections=[
                {
                    "license_expression": "gpl-3.0",
                    "matches": [
                        {
                            "license_expression": "gpl-3.0",
                            "rule_identifier": "gpl-3.0.LICENSE",
                        }
                    ],
                }
            ],
        )
        ignored.update(tag="from")
        package.add_resources([ignored])

        license_validation.validate_package_license_integrity(self.project)

        package.refresh_from_db()
        self.assertFalse(package.has_license_issue)

    def test_scanpipe_license_validation_filter_ignored_licenses(self):
        """Ignored licenses are dropped; expressions become None if nothing remains."""
        for expression, expected in [
            ("mit", "mit"),
            ("unknown", None),
            ("mit AND unknown", "mit"),
            ("unknown-spdx OR free-unknown", None),
        ]:
            with self.subTest(expression=expression):
                parsed = self.licensing.parse(expression)
                result = license_validation.filter_ignored_licenses(
                    parsed, self.licensing
                )
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(str(result), expected)

    def test_scanpipe_license_validation_handle_operator_expression_passthrough(self):
        """With no licenses filtered, the operator expression is preserved."""
        for operator, expression in [
            (self.licensing.AND, "mit AND apache-2.0"),
            (self.licensing.OR, "mit OR bsd-3-clause"),
        ]:
            with self.subTest(operator=operator):
                parsed = self.licensing.parse(expression)
                result = license_validation.handle_operator_expression(
                    parsed, self.licensing, operator
                )
                self.assertEqual(str(result), expression)

    def test_scanpipe_license_validation_handle_operator_expression_filters(self):
        """Filtered args are removed; an all-filtered expression returns None."""
        expr = self.licensing.parse("mit AND unknown")
        self.assertEqual(
            str(
                license_validation.handle_operator_expression(
                    expr, self.licensing, self.licensing.AND
                )
            ),
            "mit",
        )

        expr = self.licensing.parse("unknown AND free-unknown")
        self.assertIsNone(
            license_validation.handle_operator_expression(
                expr, self.licensing, self.licensing.AND
            )
        )

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_scanpipe_license_validation_collect_detected_licenses(
        self, mock_match_is_license_text
    ):
        mock_match_is_license_text.return_value = False

        resource1 = make_resource_file(
            self.project,
            path="project/src/main.py",
            detected_license_expression="mit",
            license_detections=[
                {
                    "license_expression": "mit",
                    "matches": [{"license_expression": "mit", "rule_identifier": "t"}],
                }
            ],
        )
        resource2 = make_resource_file(
            self.project,
            path="project/src/other.py",
            detected_license_expression="apache-2.0",
            license_detections=[
                {
                    "license_expression": "apache-2.0",
                    "matches": [
                        {"license_expression": "apache-2.0", "rule_identifier": "t"}
                    ],
                }
            ],
        )

        detections = [(r.path, r.license_detections) for r in [resource1, resource2]]
        result = license_validation.collect_detected_licenses(
            detections, self.licensing
        )
        self.assertEqual(str(result), "mit AND apache-2.0")

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_scanpipe_license_validation_collect_detected_licenses_or_group(
        self, mock_match_is_license_text
    ):
        """Multiple license texts are OR-combined."""
        mock_match_is_license_text.return_value = True

        resource1 = make_resource_file(
            self.project,
            path="COPYING",
            detected_license_expression="apache-2.0",
            license_detections=[
                {
                    "license_expression": "apache-2.0",
                    "matches": [
                        {"license_expression": "apache-2.0", "rule_identifier": "a"}
                    ],
                }
            ],
        )
        resource2 = make_resource_file(
            self.project,
            path="COPYING.LESSER",
            detected_license_expression="lgpl-2.1",
            license_detections=[
                {
                    "license_expression": "lgpl-2.1",
                    "matches": [
                        {"license_expression": "lgpl-2.1", "rule_identifier": "b"}
                    ],
                }
            ],
        )

        result = license_validation.collect_detected_licenses(
            _as_detections([resource1, resource2]), self.licensing
        )
        self.assertTrue(self.licensing.is_equivalent(result, "apache-2.0 OR lgpl-2.1"))

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_scanpipe_license_validation_collect_detected_licenses_and_other(
        self, mock_match_is_license_text
    ):
        """Text licenses are OR-grouped, others AND-grouped, groups joined with AND."""
        text_by_rule = {
            "apache-2.0.LICENSE": True,
            "mit.LICENSE": True,
            "mit_or_apache-2.0_18.RULE": False,
        }

        def is_license_text(match):
            return text_by_rule[match["rule_identifier"]]

        mock_match_is_license_text.side_effect = is_license_text

        resource1 = make_resource_file(
            self.project,
            path="LICENSE-APACHE",
            detected_license_expression="apache-2.0",
            license_detections=[
                {
                    "license_expression": "apache-2.0",
                    "matches": [
                        {
                            "license_expression": "apache-2.0",
                            "rule_identifier": "apache-2.0.LICENSE",
                        }
                    ],
                }
            ],
        )
        resource2 = make_resource_file(
            self.project,
            path="LICENSE-MIT",
            detected_license_expression="mit",
            license_detections=[
                {
                    "license_expression": "mit",
                    "matches": [
                        {"license_expression": "mit", "rule_identifier": "mit.LICENSE"}
                    ],
                }
            ],
        )
        resource3 = make_resource_file(
            self.project,
            path="README.md",
            detected_license_expression="bsd-new",
            license_detections=[
                {
                    "license_expression": "bsd-new",
                    "matches": [
                        {
                            "license_expression": "bsd-new",
                            "rule_identifier": "mit_or_apache-2.0_18.RULE",
                        }
                    ],
                }
            ],
        )

        result = license_validation.collect_detected_licenses(
            _as_detections([resource1, resource2, resource3]), self.licensing
        )
        self.assertTrue(
            self.licensing.is_equivalent(result, "(apache-2.0 OR mit) AND bsd-new")
        )

    @mock.patch("scanpipe.pipes.license_validation.match_is_license_text")
    def test_scanpipe_license_validation_collect_detected_licenses_ignored_expression(
        self, mock_match_is_license_text
    ):
        """An expression made entirely of ignored licenses yields None."""
        mock_match_is_license_text.return_value = False

        resource = make_resource_file(
            self.project,
            path="src/main.py",
            detected_license_expression="unknown",
            license_detections=[
                {
                    "license_expression": "unknown",
                    "matches": [
                        {"license_expression": "unknown", "rule_identifier": "a"}
                    ],
                }
            ],
        )

        result = license_validation.collect_detected_licenses(
            _as_detections([resource]), self.licensing
        )
        self.assertIsNone(result)

    @mock.patch("scanpipe.pipes.license_validation.get_index")
    def test_scanpipe_license_validation_match_is_license_text(self, mock_get_index):
        """Only rules with `is_license_text=True` are treated as license texts."""
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

    def test_scanpipe_license_validation_combine_license_groups(self):
        """(text OR text) AND (other AND other), with each group optional."""
        mit = self.licensing.parse("mit")
        apache = self.licensing.parse("apache-2.0")
        bsd = self.licensing.parse("bsd-new")

        cases = [
            ([mit, apache], [bsd], "(mit OR apache-2.0) AND bsd-new"),
            ([mit, apache], [], "mit OR apache-2.0"),
            ([], [bsd, mit], "bsd-new AND mit"),
            ([], [], None),
        ]
        for text_licenses, other_licenses, expected in cases:
            with self.subTest(expected=expected):
                result = license_validation.combine_license_groups(
                    text_licenses, other_licenses, self.licensing
                )
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertTrue(self.licensing.is_equivalent(result, expected))

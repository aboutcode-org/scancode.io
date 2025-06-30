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

from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import TestCase

from scanpipe.pipes.license_clarity import ClarityThresholdsPolicy
from scanpipe.pipes.license_clarity import load_clarity_thresholds_from_file
from scanpipe.pipes.license_clarity import load_clarity_thresholds_from_yaml


class ClarityThresholdsPolicyTest(TestCase):
    data = Path(__file__).parent.parent / "data"
    """Test ClarityThresholdsPolicy class functionality."""

    def test_valid_thresholds_initialization(self):
        thresholds = {80: "ok", 50: "warning", 20: "error"}
        policy = ClarityThresholdsPolicy(thresholds)
        self.assertEqual(policy.thresholds, thresholds)

    def test_string_keys_converted_to_integers(self):
        thresholds = {"80": "ok", "50": "warning"}
        policy = ClarityThresholdsPolicy(thresholds)
        expected = {80: "ok", 50: "warning"}
        self.assertEqual(policy.thresholds, expected)

    def test_invalid_threshold_key_raises_error(self):
        with self.assertRaises(ValidationError) as cm:
            ClarityThresholdsPolicy({"invalid": "ok"})
        self.assertIn("must be integers", str(cm.exception))

    def test_invalid_alert_value_raises_error(self):
        with self.assertRaises(ValidationError) as cm:
            ClarityThresholdsPolicy({80: "invalid"})
        self.assertIn("must be one of 'ok', 'warning', 'error'", str(cm.exception))

    def test_non_dict_input_raises_error(self):
        with self.assertRaises(ValidationError) as cm:
            ClarityThresholdsPolicy([80, 50])
        self.assertIn("must be a dictionary", str(cm.exception))

    def test_duplicate_threshold_keys_raise_error(self):
        with self.assertRaises(ValidationError) as cm:
            ClarityThresholdsPolicy({80: "ok", "80": "warning"})
        self.assertIn("Duplicate threshold key", str(cm.exception))

    def test_overlapping_thresholds_wrong_order(self):
        with self.assertRaises(ValidationError) as cm:
            ClarityThresholdsPolicy({70: "ok", 80: "warning"})
        self.assertIn("Thresholds must be strictly descending", str(cm.exception))

    def test_float_threshold_keys(self):
        thresholds = {80.5: "ok", 50.9: "warning"}
        policy = ClarityThresholdsPolicy(thresholds)
        expected = {80: "ok", 50: "warning"}
        self.assertEqual(policy.thresholds, expected)

    def test_negative_threshold_values(self):
        thresholds = {50: "ok", 0: "warning", -10: "error"}
        policy = ClarityThresholdsPolicy(thresholds)
        self.assertEqual(policy.get_alert_for_score(60), "ok")
        self.assertEqual(policy.get_alert_for_score(25), "warning")
        self.assertEqual(policy.get_alert_for_score(-5), "error")
        self.assertEqual(policy.get_alert_for_score(-20), "error")

    def test_empty_thresholds_dict(self):
        policy = ClarityThresholdsPolicy({})
        self.assertEqual(policy.get_alert_for_score(100), "error")
        self.assertEqual(policy.get_alert_for_score(50), "error")
        self.assertEqual(policy.get_alert_for_score(0), "error")
        self.assertEqual(policy.get_alert_for_score(None), "error")

    def test_very_high_threshold_values(self):
        thresholds = {150: "ok", 100: "warning"}
        policy = ClarityThresholdsPolicy(thresholds)
        self.assertEqual(policy.get_alert_for_score(100), "warning")
        self.assertEqual(policy.get_alert_for_score(90), "error")
        self.assertEqual(policy.get_alert_for_score(50), "error")
        self.assertEqual(policy.get_alert_for_score(99), "error")

    # Policy logic via YAML string (mock policies.yml content)
    def test_yaml_string_ok_and_warning(self):
        yaml_content = """
license_clarity_thresholds:
  90: ok
  30: warning
"""
        policy = load_clarity_thresholds_from_yaml(yaml_content)
        self.assertEqual(policy.get_alert_for_score(95), "ok")
        self.assertEqual(policy.get_alert_for_score(60), "warning")
        self.assertEqual(policy.get_alert_for_score(20), "error")

    def test_yaml_string_single_threshold(self):
        yaml_content = """
license_clarity_thresholds:
  80: ok
"""
        policy = load_clarity_thresholds_from_yaml(yaml_content)
        self.assertEqual(policy.get_alert_for_score(90), "ok")
        self.assertEqual(policy.get_alert_for_score(79), "error")

    def test_yaml_string_invalid_alert(self):
        yaml_content = """
license_clarity_thresholds:
  80: great
"""
        with self.assertRaises(ValidationError):
            load_clarity_thresholds_from_yaml(yaml_content)

    def test_yaml_string_invalid_key(self):
        yaml_content = """
license_clarity_thresholds:
  eighty: ok
"""
        with self.assertRaises(ValidationError):
            load_clarity_thresholds_from_yaml(yaml_content)

    def test_yaml_string_missing_key(self):
        yaml_content = """
license_policies:
  - license_key: mit
"""
        with self.assertRaises(ValidationError):
            load_clarity_thresholds_from_yaml(yaml_content)

    def test_yaml_string_invalid_yaml(self):
        yaml_content = "license_clarity_thresholds: [80, 50"
        with self.assertRaises(ValidationError):
            load_clarity_thresholds_from_yaml(yaml_content)

    def test_load_from_existing_file(self):
        test_file = self.data / "license_clarity" / "sample_thresholds.yml"
        policy = load_clarity_thresholds_from_file(test_file)
        self.assertIsNotNone(policy)
        self.assertEqual(policy.get_alert_for_score(95), "ok")
        self.assertEqual(policy.get_alert_for_score(75), "warning")
        self.assertEqual(policy.get_alert_for_score(50), "error")

    def test_load_from_nonexistent_file(self):
        policy = load_clarity_thresholds_from_file("/nonexistent/file.yml")
        self.assertIsNone(policy)

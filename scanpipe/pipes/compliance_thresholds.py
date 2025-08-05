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

"""
Thresholds Management for License Clarity and Scorecard Compliance

This module provides an independent mechanism to read, validate, and evaluate
both license clarity and OpenSSF Scorecard score thresholds from policy files.
Unlike license and security policies which are applied during scan processing,
these thresholds are evaluated post-scan during summary generation and compliance
assessment.

The thresholds system uses simple key-value mappings where:
- Keys are numeric threshold values (minimum scores)
- Values are compliance alert levels ('ok', 'warning', 'error')

License Clarity Thresholds:
- Keys: integer threshold values (minimum clarity scores, 0-100 scale)
- Represents license information completeness percentage

Scorecard Compliance Thresholds:
- Keys: numeric threshold values (minimum scorecard scores, 0-10.0 scale)
- Represents OpenSSF security assessment (higher score = better security)

Example policies.yml structure:

license_clarity_thresholds:
  80: ok      # Scores >= 80 get 'ok' alert
  50: warning # Scores 50-79 get 'warning' alert
  0: error    # Scores below 50 get 'error' alert

scorecard_score_thresholds:
  9.0: ok       # Scores >= 9.0 get 'ok' alert
  7.0: warning  # Scores 7.0-8.9 get 'warning' alert
  0: error      # Scores below 7.0 get 'error' alert

Both threshold types follow the same evaluation logic but are tailored to their
specific scoring systems and use cases.
"""

from pathlib import Path

from django.core.exceptions import ValidationError

import saneyaml


def load_yaml_content(yaml_content):
    """Load and parse YAML content into a Python dictionary."""
    try:
        return saneyaml.load(yaml_content)
    except saneyaml.YAMLError as e:
        raise ValidationError(f"Policies file format error: {e}")


class BaseThresholdsPolicy:
    """Base class for managing score thresholds and compliance evaluation."""

    YAML_KEY = None
    THRESHOLD_TYPE = float
    POLICY_NAME = "thresholds"

    def __init__(self, threshold_dict):
        self.thresholds = self.validate_thresholds(threshold_dict)

    def validate_thresholds(self, threshold_dict):
        if not isinstance(threshold_dict, dict):
            raise ValidationError(f"The `{self.YAML_KEY}` must be a dictionary")

        validated = {}
        seen = set()
        for key, value in threshold_dict.items():
            try:
                threshold = self.THRESHOLD_TYPE(key)
            except (ValueError, TypeError):
                type_name = (
                    "integers" if issubclass(self.THRESHOLD_TYPE, int) else "numbers"
                )
                raise ValidationError(f"Threshold keys must be {type_name}, got: {key}")

            if threshold in seen:
                raise ValidationError(f"Duplicate threshold key: {threshold}")
            seen.add(threshold)

            if value not in ["ok", "warning", "error"]:
                raise ValidationError(
                    f"Compliance alert must be one of 'ok', 'warning', 'error', "
                    f"got: {value}"
                )
            validated[threshold] = value

        sorted_keys = sorted(validated.keys(), reverse=True)
        if list(validated.keys()) != sorted_keys:
            raise ValidationError("Thresholds must be strictly descending")

        return validated

    def get_alert_for_score(self, score):
        """Determine compliance alert level for a given score."""
        if score is None:
            return "error"

        applicable_thresholds = [t for t in self.thresholds if score >= t]
        if not applicable_thresholds:
            return "error"

        max_threshold = max(applicable_thresholds)
        return self.thresholds[max_threshold]


# Specific implementations
class LicenseClarityThresholdsPolicy(BaseThresholdsPolicy):
    YAML_KEY = "license_clarity_thresholds"
    THRESHOLD_TYPE = int
    POLICY_NAME = "license clarity thresholds"


class ScorecardThresholdsPolicy(BaseThresholdsPolicy):
    YAML_KEY = "scorecard_score_thresholds"
    THRESHOLD_TYPE = float
    POLICY_NAME = "scorecard score thresholds"


def load_thresholds_from_yaml(yaml_content, policy_class):
    """Load thresholds from YAML."""
    data = load_yaml_content(yaml_content)

    if not isinstance(data, dict):
        raise ValidationError("YAML content must be a dictionary.")

    if policy_class.YAML_KEY not in data:
        raise ValidationError(
            f"Missing '{policy_class.YAML_KEY}' key in policies file."
        )

    return policy_class(data[policy_class.YAML_KEY])


def load_thresholds_from_file(file_path, policy_class):
    """Load thresholds from file."""
    file_path = Path(file_path)
    if not file_path.exists():
        return

    try:
        yaml_content = file_path.read_text(encoding="utf-8")
        return load_thresholds_from_yaml(yaml_content, policy_class)
    except (OSError, UnicodeDecodeError) as e:
        raise ValidationError(f"Error reading file {file_path}: {e}")


def get_project_clarity_thresholds(project):
    policies_dict = project.get_policies_dict()
    if not policies_dict:
        return

    clarity_thresholds = policies_dict.get("license_clarity_thresholds")
    if not clarity_thresholds:
        return

    return LicenseClarityThresholdsPolicy(clarity_thresholds)


def get_project_scorecard_thresholds(project):
    policies_dict = project.get_policies_dict()
    if not policies_dict:
        return

    scorecard_thresholds = policies_dict.get("scorecard_score_thresholds")
    if not scorecard_thresholds:
        return

    return ScorecardThresholdsPolicy(scorecard_thresholds)

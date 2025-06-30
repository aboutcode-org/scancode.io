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
License Clarity Thresholds Management

This module provides an independent mechanism to read, validate, and evaluate
license clarity score thresholds from policy files. Unlike license policies
which are applied during scan processing, clarity thresholds are evaluated
post-scan during summary generation.

The clarity thresholds system uses a simple key-value mapping where:
- Keys are integer threshold values (minimum scores)
- Values are compliance alert levels ('ok', 'warning', 'error')

Example policies.yml structure:

license_clarity_thresholds:
  80: ok # Scores >= 80 get 'ok' alert
  50: warning # Scores 50-79 get 'warning' alert
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


class ClarityThresholdsPolicy:
    """
    Manages clarity score thresholds and compliance evaluation.

    This class reads clarity thresholds from a dictionary, validates them
    against threshold configurations and determines compliance alerts based on
    clarity scores.
    """

    def __init__(self, threshold_dict):
        """Initialize with validated threshold dictionary."""
        self.thresholds = self.validate_thresholds(threshold_dict)

    @staticmethod
    def validate_thresholds(threshold_dict):
        if not isinstance(threshold_dict, dict):
            raise ValidationError(
                "The `license_clarity_thresholds` must be a dictionary"
            )
        validated = {}
        seen = set()
        for key, value in threshold_dict.items():
            try:
                threshold = int(key)
            except (ValueError, TypeError):
                raise ValidationError(f"Threshold keys must be integers, got: {key}")
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
        """
        Determine compliance alert level for a given clarity score

        Returns:
            str: Compliance alert level ('ok', 'warning', 'error')

        """
        if score is None:
            return "error"

        # Find the highest threshold that the score meets or exceeds
        applicable_thresholds = [t for t in self.thresholds if score >= t]
        if not applicable_thresholds:
            return "error"

        max_threshold = max(applicable_thresholds)
        return self.thresholds[max_threshold]

    def get_thresholds_summary(self):
        """
        Get a summary of configured thresholds for reporting

        Returns:
            dict: Summary of thresholds and their alert levels

        """
        return dict(sorted(self.thresholds.items(), reverse=True))


def load_clarity_thresholds_from_yaml(yaml_content):
    """
    Load clarity thresholds from YAML content.

    Returns:
        ClarityThresholdsPolicy: Configured policy object

    """
    data = load_yaml_content(yaml_content)

    if not isinstance(data, dict):
        raise ValidationError("YAML content must be a dictionary.")

    if "license_clarity_thresholds" not in data:
        raise ValidationError(
            "Missing 'license_clarity_thresholds' key in policies file."
        )

    return ClarityThresholdsPolicy(data["license_clarity_thresholds"])


def load_clarity_thresholds_from_file(file_path):
    """
    Load clarity thresholds from a YAML file.

    Returns:
        ClarityThresholdsPolicy: Configured policy object or None if file not found

    """
    file_path = Path(file_path)

    if not file_path.exists():
        return None

    try:
        yaml_content = file_path.read_text(encoding="utf-8")
        return load_clarity_thresholds_from_yaml(yaml_content)
    except (OSError, UnicodeDecodeError) as e:
        raise ValidationError(f"Error reading file {file_path}: {e}")

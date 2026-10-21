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

import logging

from license_expression import ExpressionError
from license_expression import Licensing
from license_expression import combine_expressions
from licensedcode.cache import get_index

from scanpipe.models import convert_glob_to_django_regex
from scanpipe.pipes import flag

logger = logging.getLogger(__name__)

# Paths excluded from package license validation. The goal is to skip files
# whose detected license is not representative of the package's licensing.
LICENSE_VALIDATION_IGNORE_PATTERNS = [
    "*/tests/*",
    "*/test/*",
    "*.sh",
]

# Licenses that are not useful for validating package license integrity.
IGNORED_LICENSES = [
    "free-unknown",
    "unknown",
    "unknown-license-reference",
    "unknown-spdx",
]


def validate_package_license_integrity(project):
    """Validate the correctness of the package license."""
    licensing = Licensing()

    # Pre-filter at SQL: only from_codebase resources that have a license
    # expression, minus paths matching the ignore patterns. None of this
    # depends on the package, so it is applied once, outside the loop.
    base_resources_qs = (
        project.codebaseresources.from_codebase().has_license_expression()
    )
    for pattern in LICENSE_VALIDATION_IGNORE_PATTERNS:
        base_resources_qs = base_resources_qs.exclude(
            path__regex=convert_glob_to_django_regex(pattern)
        )

    for package in project.discoveredpackages.all():
        package_lic = package.get_declared_license_expression()
        if not package_lic:
            continue

        resources_qs = _get_package_resources_qs(package, base_resources_qs)
        detections = resources_qs.values_list("path", "license_detections")
        detected_expr = collect_detected_licenses(detections, licensing)

        if detected_expr is None:
            continue

        detected_lic_exp = str(licensing.dedup(detected_expr))

        if licensing.is_equivalent(detected_expr, package_lic):
            _clear_package_issues(package)
            continue

        issue = {
            "issue_type": "License Mismatch",
            "declared_license": package_lic,
            "detected_codebase_license": detected_lic_exp,
        }
        # Replace the previous issues list instead of appending to it so
        # re-runs do not duplicate the same entry.
        package.update(
            extra_data={**package.extra_data, "issues": [issue]},
            has_license_issue=True,
        )
        _flag_datafiles_with_issue(project, package, issue)


def _get_package_resources_qs(package, base_resources_qs):
    """Return the resources queryset to use for the given package."""
    if package.type == "cargo":
        # A single cargo package only has one Cargo.toml file, meaning
        # only one package is defined. The package_uid is not populated
        # on source files, so consider all resources in the codebase for
        # license validation.
        # https://github.com/aboutcode-org/scancode.io/issues/2169
        return base_resources_qs
    if package.package_uid:
        # SQL filter: only resources linked to this package through the
        # `discovered_packages` M2M.
        return base_resources_qs.filter(
            discovered_packages__package_uid=package.package_uid
        )
    return base_resources_qs


def _clear_package_issues(package):
    """Clear any previous mismatch state so re-runs are idempotent."""
    if package.has_license_issue or package.extra_data.get("issues"):
        extra_data = {
            key: value for key, value in package.extra_data.items() if key != "issues"
        }
        package.update(has_license_issue=False, extra_data=extra_data)


def _flag_datafiles_with_issue(project, package, issue):
    """
    Attach the license mismatch ``issue`` to the package's datafile resources
    without discarding any status set by an earlier pipeline step.
    """
    local_paths = [
        path for path in package.datafile_paths if not path.startswith("https://")
    ]
    if not local_paths:
        return

    for resource in project.codebaseresources.filter(path__in=local_paths):
        update_fields = {
            "extra_data": {**resource.extra_data, "issues": [issue]},
        }
        if not resource.status:
            update_fields["status"] = flag.LICENSE_MISMATCH
        resource.update(**update_fields)


def filter_ignored_licenses(license_expression, licensing):
    """Filter out ignored licenses from a license expression."""
    if isinstance(license_expression, licensing.Symbol):
        if (
            hasattr(license_expression, "key")
            and license_expression.key in IGNORED_LICENSES
        ):
            return None
        return license_expression

    if isinstance(license_expression, licensing.AND):
        return handle_operator_expression(license_expression, licensing, licensing.AND)

    if isinstance(license_expression, licensing.OR):
        return handle_operator_expression(license_expression, licensing, licensing.OR)

    return license_expression


def handle_operator_expression(expression, licensing, operator):
    """
    Process AND/OR operations in a license expression, filtering out
    ignored licenses.
    """
    args = []
    for arg in expression.args:
        filtered_arg = filter_ignored_licenses(arg, licensing)
        if filtered_arg is not None:
            args.append(filtered_arg)
    if not args:
        return None
    if len(args) == 1:
        return args[0]

    return operator(*args)


def match_is_license_text(match):
    """
    Return True if the matched rule is a full license text rather than a
    notice, tag, or reference.

    Read the `is_license_text` flag from the licensedcode rule index using
    the match's `rule_identifier`.

    Return False if the identifier is missing or unknown, or if the rule
    is not a license text.
    """
    identifier = match.get("rule_identifier")
    if not identifier:
        return False
    rule = get_index().rules_by_id.get(identifier)
    return bool(rule and rule.is_license_text)


def _iter_match_expressions(license_detections, licensing, path):
    """
    Yield ``(is_text, expression)`` pairs for each match in a
    ``license_detections`` array.
    """
    for detection in license_detections:
        for match in detection.get("matches"):
            expression = match.get("license_expression")
            if not expression:
                continue
            try:
                parsed = licensing.parse(expression)
            except ExpressionError:
                logger.warning(
                    f"Failed to parse the license expression: {expression} at {path}"
                )
                continue
            filtered = filter_ignored_licenses(parsed, licensing)
            if filtered is None:
                continue
            yield match_is_license_text(match), filtered


def combine_license_groups(text_licenses, other_licenses, licensing):
    """
    Combine text licenses with OR and other licenses with AND, then join
    the two groups with AND.

    Multiple license text files in a project such as COPYING, COPYING3,
    COPYING.LESSER are alternatives, so text detections are OR'd together.
    `AND` requirements come from notices, tags, or references elsewhere.

    Return None if both groups are empty.
    """
    parts = []
    if text_licenses:
        parts.append(
            combine_expressions(text_licenses, relation="OR", licensing=licensing)
        )
    if other_licenses:
        parts.append(
            combine_expressions(other_licenses, relation="AND", licensing=licensing)
        )

    if not parts:
        return None

    return combine_expressions(parts, relation="AND", licensing=licensing)


def collect_detected_licenses(detections, licensing):
    """
    Collect detected licenses from an iterable of ``(path,
    license_detections)`` tuples.

    Return a single LicenseExpression combining both groups with AND, or
    None if there is nothing to combine.
    """
    text_licenses = []
    other_licenses = []

    for path, license_detections in detections:
        for is_text, filtered in _iter_match_expressions(
            license_detections, licensing, path=path
        ):
            if is_text:
                if filtered not in text_licenses:
                    text_licenses.append(filtered)
            else:
                if filtered not in other_licenses:
                    other_licenses.append(filtered)

    return combine_license_groups(text_licenses, other_licenses, licensing)

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

from license_expression import Licensing

from scanpipe.pipes import flag


def validate_package_license_integrity(project):
    """Validate the correctness of the package license."""
    # Patterns to ignore certain resources during license validation
    ignore_patterns = [
        "*test*",
        "*.sh",
    ]

    for package in project.discoveredpackages.all():
        package_lic = package.get_declared_license_expression()
        if package_lic:
            if package.type == "cargo":
                # A single cargo package only has one Cargo.toml file
                # meaning only one package is defined. Therefore, we don't
                # need to check for the package_uid
                # In addition, the package_uid is not populated to source files:
                # https://github.com/aboutcode-org/scancode.io/issues/2169
                # so we set package_uid to None to consider all resources
                # in the codebase for license validation.
                package_uid = None
            else:
                package_uid = package.package_uid
            resources = project.codebaseresources.has_license_expression()
            detected_lic_list = collect_detected_licenses(
                resources, ignore_patterns, package_uid
            )

            if detected_lic_list:
                lic_exp = " AND ".join(detected_lic_list)
                # The dedup have bug and need to be fixed:
                # https://github.com/aboutcode-org/license-expression/issues/130
                detected_lic_exp = str(Licensing().dedup(lic_exp))
                # The package license is not in sync with detected license(s)
                if detected_lic_exp != package_lic:
                    package.update_extra_data(
                        {
                            "issue": "License Mismatch",
                            "declared_license": package_lic,
                            "detected_codebase_license": detected_lic_exp,
                        }
                    )
                    for datafile_path in package.datafile_paths:
                        if not datafile_path.startswith("https://"):
                            data_path = project.codebaseresources.get(
                                path=datafile_path
                            )
                            data_path.update(status=flag.LICENSE_ISSUE)
                            data_path.update_extra_data(
                                {
                                    "declared_license": package_lic,
                                    "detected_codebase_license": detected_lic_exp,
                                }
                            )


def contains_ignore_pattern(resource_path, ignore_patterns):
    """Check if the resource path matches any of the ignore patterns."""
    from fnmatch import fnmatch

    for pattern in ignore_patterns:
        if fnmatch(resource_path, pattern):
            return True
    return False


def collect_detected_licenses(resources, ignore_patterns, package_uid=None):
    """Collect detected licenses from resources, ignoring specified patterns."""
    detected_lic_list = []
    # Some licenses are not useful for validating package license integrity, so we ignore them.
    ignored_licenses = ['free-unknown', 'unknown', 'unknown-license-reference', 'unknown-spdx']
    for resource in resources:
        if contains_ignore_pattern(resource.path, ignore_patterns):
            continue

        # If a package_uid is provided, only consider resources linked to it
        if package_uid and package_uid not in resource.for_packages:
            continue

        lic = resource.detected_license_expression
        if lic and lic not in ignored_licenses and lic not in detected_lic_list:
            # Make sure there is parentheses if the license has an 'OR' operator
            # TODO: We need to parse the lic and check for ignored licenses if lic is an expression
            if ' OR ' in lic and not (lic.startswith('(') and lic.endswith(')')):
                lic = f'({lic})'
            detected_lic_list.append(lic)
    return detected_lic_list


# TODO: This may not be necessary since our focus is on license mismatches at the package level.
# If a file contains an extra license not declared in the package, we flag it at the package level rather than the file level.
# Therefore, the 'missing' and 'extra' checks may be excessive.
def evaluate_license_mismatch(package_lic, detected_lic_list):
    """Check if there is a license mismatch between declared package_license and detected licenses.

    Returns:
        A dictionary with mismatch information
    """
    licensing = Licensing()

    # Parse expressions
    package_expr = licensing.parse(package_lic)
    detected_exprs = [licensing.parse(lic) for lic in detected_lic_list]

    # Combine detected licenses with AND
    detected_combined = (detected_exprs[0] if len(detected_exprs) == 1
                        else licensing.AND(*detected_exprs))

    # Find what's missing from detected
    missing = find_missing(package_expr, detected_combined)

    # Find extra licenses (with special handling for OR expressions)
    extra = find_extra(detected_exprs, package_expr)

    return {
        'missing': sorted(missing),
        'extra': sorted(extra),
        'is_match': not missing and not extra,
        'details': format_details(missing, extra)
    }


def find_missing(expr, detected):
    """Find licenses required by package but missing from detected."""
    # Base case: single license
    if is_license_symbol(expr):
        return [expr.key] if not contains_license(detected, expr.key) else []

    # WITH exception
    if is_with_exception(expr):
        missing = []
        if not contains_license(detected, expr.license_symbol.key):
            missing.append(expr.license_symbol.key)
        if not contains_license(detected, expr.exception_symbol.key):
            missing.append(expr.exception_symbol.key)
        return missing

    # AND/OR expressions
    if hasattr(expr, 'args'):
        if is_and(expr):
            # AND requires all branches
            return sum((find_missing(arg, detected) for arg in expr.args), [])

        if is_or(expr):
            # OR requires at least one branch
            # First, check if any branch is fully satisfied
            for arg in expr.args:
                if not find_missing(arg, detected):
                    return []  # Found a fully satisfied branch

            # If no branch is fully satisfied, collect ALL licenses from ALL branches
            # to show everything that's missing from the OR
            all_missing = []
            for arg in expr.args:
                branch_missing = find_missing(arg, detected)
                all_missing.extend(branch_missing)
            return list(set(all_missing))  # Remove duplicates

    return []


def find_extra(detected_exprs, package_expr):
    """Find licenses in detected that aren't required by package."""
    extra = []

    for detected in detected_exprs:
        detected_keys = get_all_keys(detected)

        # If it's an OR and any branch is required, none of its licenses are extra
        if is_or(detected) and any(is_license_required(key, package_expr) for key in detected_keys):
            continue

        # Otherwise, add all keys not required by package
        for key in detected_keys:
            if not is_license_required(key, package_expr) and key not in extra:
                extra.append(key)

    return extra


def is_license_required(license_key, expr):
    """Check if a license key is required by the package expression."""
    if is_license_symbol(expr):
        return expr.key == license_key
    if is_with_exception(expr):
        return (expr.license_symbol.key == license_key or
                expr.exception_symbol.key == license_key)
    if hasattr(expr, 'args'):
        if is_and(expr):
            # In AND, a license is required if it appears in any branch
            return any(is_license_required(license_key, arg) for arg in expr.args)
        if is_or(expr):
            # In OR, a license is required if it appears in the expression
            return any(is_license_required(license_key, arg) for arg in expr.args)
    return False


def get_all_keys(expr):
    """Extract all license keys from an expression."""
    if is_license_symbol(expr):
        return [expr.key]
    if is_with_exception(expr):
        return [expr.license_symbol.key, expr.exception_symbol.key]
    if hasattr(expr, 'args'):
        keys = []
        for arg in expr.args:
            keys.extend(get_all_keys(arg))
        return keys
    return []


def contains_license(expr, license_key):
    """Check if an expression contains a specific license key."""
    if is_license_symbol(expr):
        return expr.key == license_key
    if is_with_exception(expr):
        return (expr.license_symbol.key == license_key or
                expr.exception_symbol.key == license_key)
    if hasattr(expr, 'args'):
        return any(contains_license(arg, license_key) for arg in expr.args)
    return False


def format_details(missing, extra):
    """Format the details string."""
    parts = []
    if missing:
        parts.append(f"Missing: {', '.join(sorted(missing))}")
    if extra:
        parts.append(f"Extra: {', '.join(sorted(extra))}")
    return '; '.join(parts) if parts else 'match'


# Helper functions for type checking
def is_license_symbol(expr):
    return hasattr(expr, 'key') and not hasattr(expr, 'license_symbol')

def is_with_exception(expr):
    return hasattr(expr, 'license_symbol') and hasattr(expr, 'exception_symbol')

def is_and(expr):
    return hasattr(expr, 'operator') and 'AND' in expr.operator.strip()

def is_or(expr):
    return hasattr(expr, 'operator') and 'OR' in expr.operator.strip()

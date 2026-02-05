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
import re
from collections import defaultdict

from licensedcode.cache import get_licensing

logger = logging.getLogger(__name__)

"""
Utilities for analyzing and detecting license issues in Nixpkgs packages.
This module provides specific rules for nixpkgs given the large diversity
of tech stacks and upstreams.

Main features:
- Automatically detect when a nixpkgs license declaration is incorrect
- Determine what the correct license should be based on detected licenses
- Identify ambiguous or unclear license declarations
- Report license inconsistencies between declared and detected
- Apply nixpkgs-specific rules for different ecosystems (Python, Rust, etc.)
- Check for copyleft compliance issues
- Validate license file presence and consistency

Usage:
    from scanpipe.pipes import nixpkgs
    
    # Analyze all packages in a project
    issues = nixpkgs.analyze_license_issues(project)
    
    # Detect issues in a specific package
    package_issues = nixpkgs.detect_package_license_issues(package)
    
    # Generate comprehensive report
    report = nixpkgs.generate_license_report(project)
    
    # Get license correction suggestion
    suggestion = nixpkgs.suggest_license_correction(package, detected_licenses)
"""


def analyze_license_issues(project):
    """
    Analyze all packages in the project and detect license inconsistencies.
    Returns a dict mapping package identifiers to their license issues.
    """
    issues = {}
    # Optimize database queries with prefetch_related
    packages = project.discoveredpackages.all().prefetch_related(
        "codebase_resources",
    )
    
    for package in packages:
        package_issues = detect_package_license_issues(package)
        if package_issues:
            issues[str(package)] = package_issues
    
    return issues


def detect_package_license_issues(package):
    """
    Detect licensing issues in a single package.
    Returns a list of issue descriptions for the package.
    """
    issues = []
    
    # Check if declared license exists
    if not package.declared_license_expression:
        issues.append({
            "type": "missing_declared_license",
            "severity": "error",
            "message": "Package has no declared license expression",
            "suggestion": "Review package metadata and source files to determine correct license"
        })
    
    # Get detected licenses from codebase resources
    detected_licenses = get_detected_licenses_for_package(package)
    
    # Compare declared vs detected
    if package.declared_license_expression and detected_licenses:
        declared_license = package.declared_license_expression
        inconsistencies = find_license_inconsistencies(
            declared_license,
            detected_licenses
        )
        if inconsistencies:
            issues.extend(inconsistencies)
    
    # Check for ambiguous license detections
    ambiguous_detections = check_ambiguous_detections(package)
    if ambiguous_detections:
        issues.extend(ambiguous_detections)
    
    # Check for license clarity issues
    clarity_issues = check_license_clarity(package)
    if clarity_issues:
        issues.extend(clarity_issues)
    
    # Nixpkgs-specific checks
    ecosystem_issue = check_nixpkgs_ecosystem_license(package)
    if ecosystem_issue:
        issues.append(ecosystem_issue)
    
    copyleft_issues = detect_copyleft_compliance_issues(package)
    if copyleft_issues:
        issues.extend(copyleft_issues)
    
    license_file_issues = detect_license_file_issues(package)
    if license_file_issues:
        issues.extend(license_file_issues)
    
    return issues


def get_detected_licenses_for_package(package):
    """
    Extract all detected license expressions from the package's codebase resources.
    Returns a list of unique license expressions found in the package files.
    """
    detected = set()
    
    resources = package.codebase_resources.all()
    for resource in resources:
        if resource.detected_license_expression:
            detected.add(resource.detected_license_expression)
    
    return list(detected)


def find_license_inconsistencies(declared_license, detected_licenses):
    """
    Compare declared license with detected licenses to find inconsistencies.
    Returns a list of inconsistency issues.
    """
    issues = []
    licensing = get_licensing()
    
    try:
        declared_parsed = licensing.parse(declared_license, validate=True)
    except Exception as e:
        issues.append({
            "type": "invalid_declared_license",
            "severity": "error",
            "message": f"Invalid declared license expression: {declared_license}",
            "details": str(e),
            "suggestion": "Fix the license expression syntax"
        })
        return issues
    
    # Check if any detected license is not compatible with declared
    for detected in detected_licenses:
        try:
            detected_parsed = licensing.parse(detected, validate=True)
            
            # Check if detected is subset of declared or vice versa
            if not are_licenses_compatible(declared_parsed, detected_parsed, licensing):
                issues.append({
                    "type": "license_mismatch",
                    "severity": "warning",
                    "message": f"Detected license '{detected}' differs from declared '{declared_license}'",
                    "declared": declared_license,
                    "detected": detected,
                    "suggestion": "Review source files to determine correct license. Consider if this is dual-licensing or incorrect declaration."
                })
        except Exception as e:
            # Log invalid detected licenses for debugging
            logger.debug(f"Invalid detected license expression '{detected}': {e}")
            continue
    
    return issues


def are_licenses_compatible(declared, detected, licensing):
    """
    Check if detected license is compatible with declared license.
    This is a simplified check - could be expanded with more sophisticated logic.
    """
    declared_str = str(declared).lower()
    detected_str = str(detected).lower()
    
    # Exact match
    if declared_str == detected_str:
        return True
    
    # Check if either expression contains the other
    # Split only on spaces, hyphens, and parentheses (not on operators)
    declared_parts = set(re.split(r'[\s()]+', declared_str))
    detected_parts = set(re.split(r'[\s()]+', detected_str))
    
    # Remove empty strings and common operators from comparison
    operators = {'or', 'and', 'with', ''}
    declared_parts -= operators
    detected_parts -= operators
    
    # Check if detected parts are subset of declared or vice versa
    if detected_parts and declared_parts:
        if detected_parts.issubset(declared_parts) or declared_parts.issubset(detected_parts):
            return True
    
    return False


def check_ambiguous_detections(package):
    """
    Check for ambiguous license detections that need review.
    Returns a list of ambiguity issues.
    """
    issues = []
    
    # Get license detections that need review from the package's project
    ambiguous_licenses = package.project.discoveredlicenses.filter(
        needs_review=True
    )
    
    # Get file regions related to this package
    package_paths = set(package.codebase_resources.values_list('path', flat=True))
    
    for lic in ambiguous_licenses:
        # Check if this detection appears in package files
        detection_paths = {
            fr_path
            for fr in (lic.file_regions or [])
            if isinstance(fr, dict)
            for fr_path in [fr.get("path")]
            if fr_path is not None
        }
        if package_paths & detection_paths:
            issues.append({
                "type": "ambiguous_detection",
                "severity": "warning",
                "message": f"Ambiguous license detection: {lic.license_expression}",
                "identifier": lic.identifier,
                "review_comments": lic.review_comments,
                "suggestion": "Manual review required for this detection"
            })
    
    return issues


def check_license_clarity(package):
    """
    Check for license clarity issues in the package.
    Returns a list of clarity issues.
    """
    issues = []
    
    # Check if license is too generic or unclear
    if package.declared_license_expression:
        unclear_indicators = [
            "unknown",
            "see-license",
            "other",
            "proprietary",
            "free",
            "open-source",
        ]
        
        declared_lower = package.declared_license_expression.lower()
        for indicator in unclear_indicators:
            # Use word boundary matching to avoid false positives
            pattern = r'\b' + re.escape(indicator) + r'\b'
            if re.search(pattern, declared_lower):
                issues.append({
                    "type": "unclear_license",
                    "severity": "warning",
                    "message": f"License expression contains unclear term: '{indicator}'",
                    "declared": package.declared_license_expression,
                    "suggestion": f"Review package to determine specific license instead of '{indicator}'"
                })
                break
    
    # Check for missing license files
    has_license_file = False
    for resource in package.codebase_resources.all():
        # Prefer the dedicated legal/notice flag
        if getattr(resource, "is_legal", False):
            has_license_file = True
            break
        # Fall back to common license filenames
        resource_name = resource.name.lower()
        if (resource_name in {"license", "license.txt", "license.md", "copying", "copying.txt"}
            or resource_name.startswith("license.")
            or resource_name.startswith("copying.")):
            has_license_file = True
            break
    
    if not has_license_file and package.declared_license_expression:
        issues.append({
            "type": "missing_license_file",
            "severity": "info",
            "message": "No LICENSE file found in package",
            "suggestion": "Consider including a LICENSE file for clarity"
        })
    
    return issues


def generate_license_report(project):
    """
    Generate a comprehensive license report for all packages in the project.
    Returns a structured report dict.
    """
    issues_by_package = analyze_license_issues(project)
    
    # Group by issue type and severity
    by_type = defaultdict(list)
    by_severity = defaultdict(list)
    
    for package_id, package_issues in issues_by_package.items():
        for issue in package_issues:
            issue_with_package = {**issue, "package": package_id}
            by_type[issue["type"]].append(issue_with_package)
            by_severity[issue["severity"]].append(issue_with_package)
    
    total_packages = project.discoveredpackages.count()
    packages_with_issues = len(issues_by_package)
    
    report = {
        "summary": {
            "total_packages": total_packages,
            "packages_with_issues": packages_with_issues,
            "packages_without_issues": total_packages - packages_with_issues,
            "total_issues": sum(len(issues) for issues in issues_by_package.values()),
        },
        "by_severity": {
            "error": len(by_severity.get("error", [])),
            "warning": len(by_severity.get("warning", [])),
            "info": len(by_severity.get("info", [])),
        },
        "by_type": {
            issue_type: len(issues)
            for issue_type, issues in by_type.items()
        },
        "issues_by_package": issues_by_package,
        "issues_by_type": dict(by_type),
        "issues_by_severity": dict(by_severity),
    }
    
    return report


def suggest_license_correction(package, detected_licenses):
    """
    Suggest the correct license for a package based on detected licenses.
    Returns a suggestion dict or None if no clear suggestion can be made.
    """
    if not detected_licenses:
        return None
    
    # If all detected licenses are the same, suggest that
    unique_detected = set(detected_licenses)
    if len(unique_detected) == 1:
        return {
            "suggested_license": list(unique_detected)[0],
            "confidence": "high",
            "reason": "All detected licenses are identical"
        }
    
    # If multiple licenses detected, check if they're compatible
    licensing = get_licensing()
    
    # Try to create a combined expression
    try:
        # Sort for consistent ordering
        sorted_licenses = sorted(unique_detected)
        # Most common pattern: dual licensing with OR
        combined_or = " OR ".join(sorted_licenses)
        licensing.parse(combined_or, validate=True)
        
        return {
            "suggested_license": combined_or,
            "confidence": "medium",
            "reason": "Multiple licenses detected - may be dual-licensed"
        }
    except Exception:
        pass
    
    # If can't combine, report most common
    if detected_licenses:
        most_common = max(set(detected_licenses), key=detected_licenses.count)
        return {
            "suggested_license": most_common,
            "confidence": "low",
            "reason": f"Most frequently detected license (appears {detected_licenses.count(most_common)} times)"
        }
    
    return None


# Nixpkgs-specific license mappings and rules
NIXPKGS_LICENSE_MAPPINGS = {
    # Common license name variations in nixpkgs
    "gpl": "GPL-1.0-or-later",
    "gpl2": "GPL-2.0-only",
    "gpl2+": "GPL-2.0-or-later",
    "gpl3": "GPL-3.0-only",
    "gpl3+": "GPL-3.0-or-later",
    "lgpl": "LGPL-2.1-or-later",
    "lgpl2": "LGPL-2.1-only",
    "lgpl21": "LGPL-2.1-only",
    "lgpl21+": "LGPL-2.1-or-later",
    "lgpl3": "LGPL-3.0-only",
    "lgpl3+": "LGPL-3.0-or-later",
    "bsd": "BSD-3-Clause",
    "bsd2": "BSD-2-Clause",
    "bsd3": "BSD-3-Clause",
    "apache": "Apache-2.0",
    "apache2": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "mpl": "MPL-2.0",
    "mpl2": "MPL-2.0",
    "mit": "MIT",
    "isc": "ISC",
    "zlib": "Zlib",
    "artistic": "Artistic-2.0",
    "artistic2": "Artistic-2.0",
}


# Package type to ecosystem mapping
PACKAGE_TYPE_TO_ECOSYSTEM = {
    "pypi": "python",
    "npm": "nodejs",
    "cargo": "rust",
    "gem": "ruby",
    "cpan": "perl",
    "maven": "java",
    "nuget": "dotnet",
    "hackage": "haskell",
}

# Known nixpkgs package ecosystems and their typical licenses
NIXPKGS_ECOSYSTEM_LICENSE_PATTERNS = {
    "python": ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0-or-later"],
    "rust": ["MIT", "Apache-2.0", "MIT OR Apache-2.0"],
    "nodejs": ["MIT", "ISC", "BSD-3-Clause"],
    "go": ["MIT", "Apache-2.0", "BSD-3-Clause"],
    "haskell": ["BSD-3-Clause", "MIT"],
    "ruby": ["MIT", "GPL-2.0-or-later"],
    "perl": ["Artistic-2.0", "GPL-1.0-or-later"],
    "java": ["Apache-2.0", "MIT", "LGPL-2.1-or-later"],
    "dotnet": ["MIT", "Apache-2.0"],
}


def normalize_nixpkgs_license(license_str):
    """
    Normalize a nixpkgs license string to SPDX identifier.
    Returns normalized license or original if no mapping found.
    """
    if not license_str:
        return license_str
    
    normalized = license_str.lower().strip()
    return NIXPKGS_LICENSE_MAPPINGS.get(normalized, license_str)


def check_nixpkgs_ecosystem_license(package):
    """
    Check if the package license is typical for its ecosystem.
    Returns issue dict if license seems unusual for the ecosystem.
    """
    if not package.type or not package.declared_license_expression:
        return None
    
    package_type = package.type.lower()
    # Map package type to ecosystem (e.g., pypi -> python)
    ecosystem = PACKAGE_TYPE_TO_ECOSYSTEM.get(package_type, package_type)
    expected_licenses = NIXPKGS_ECOSYSTEM_LICENSE_PATTERNS.get(ecosystem)
    
    if not expected_licenses:
        return None
    
    declared = package.declared_license_expression
    
    # Check if declared license matches expected patterns
    declared_lower = declared.lower()
    for expected in expected_licenses:
        # Use word boundary matching to avoid false positives like "mit" in "limited"
        pattern = r'\b' + re.escape(expected.lower()) + r'\b'
        if re.search(pattern, declared_lower):
            return None
    
    return {
        "type": "unusual_ecosystem_license",
        "severity": "info",
        "message": f"License '{declared}' is unusual for {ecosystem} packages",
        "expected_licenses": expected_licenses,
        "suggestion": f"Verify this is correct. Common {ecosystem} licenses: {', '.join(expected_licenses)}"
    }


def detect_copyleft_compliance_issues(package):
    """
    Detect potential copyleft compliance issues.
    Returns list of compliance-related issues.
    """
    issues = []
    
    if not package.declared_license_expression:
        return issues
    
    declared_lower = package.declared_license_expression.lower()
    
    # Check for copyleft licenses using word boundary matching
    copyleft_indicators = ["gpl", "agpl", "lgpl", "mpl", "epl", "cpl"]
    is_copyleft = any(
        re.search(r'\b' + re.escape(ind) + r'\b', declared_lower)
        for ind in copyleft_indicators
    )
    
    if is_copyleft:
        # Check if package has dependencies
        dependencies = package.project.discovereddependencies.filter(
            for_package=package
        )
        
        if dependencies.exists():
            issues.append({
                "type": "copyleft_with_dependencies",
                "severity": "warning",
                "message": f"Copyleft license {package.declared_license_expression} with dependencies",
                "suggestion": "Review dependencies for license compatibility"
            })
        
        # Check for proprietary indicators in notes or description
        proprietary_indicators = ["proprietary", "commercial", "closed"]
        description = (package.description or "").lower()
        notes = (package.notes or "").lower()
        
        # Use word boundary matching to avoid false positives like "commercial" in "noncommercial"
        has_proprietary = any(
            re.search(r'\b' + re.escape(ind) + r'\b', description) or
            re.search(r'\b' + re.escape(ind) + r'\b', notes)
            for ind in proprietary_indicators
        )
        
        if has_proprietary:
            issues.append({
                "type": "copyleft_proprietary_conflict",
                "severity": "error",
                "message": "Copyleft license declared but proprietary indicators found",
                "suggestion": "Verify license - copyleft and proprietary are incompatible"
            })
    
    return issues


def detect_license_file_issues(package):
    """
    Detect issues with license files in the package.
    Returns list of license file-related issues.
    """
    issues = []
    
    license_files = []
    resources = package.codebase_resources.all()
    
    # Known file extensions for license files
    license_extensions = {'.txt', '.md', '.rst', '.html', '.pdf', ''}
    
    for resource in resources:
        # Prefer the is_legal flag when available
        if getattr(resource, "is_legal", False):
            license_files.append(resource)
            continue
        
        # Fall back to matching common canonical license filenames
        name_lower = resource.name.lower()
        # Extract file extension for validation
        file_ext = '.' + name_lower.split('.')[-1] if '.' in name_lower else ''
        
        # Check if it matches expected license file patterns with valid extensions
        if (
            # Exact common license filenames
            name_lower in {
                "license", "license.txt", "license.md",
                "licence", "licence.txt", "licence.md",
                "copying", "copying.txt", "copying.md",
                "copyright", "copyright.txt", "copyright.md",
            }
            # Files starting with common license-related prefixes and valid extensions
            or (file_ext in license_extensions and name_lower.startswith((
                "license.", "license-",
                "licence.", "licence-",
                "copying.", "copying-",
                "copyright.", "copyright-",
            )))
        ):
            license_files.append(resource)
    
    # Multiple license files might indicate multiple licenses
    if len(license_files) > 1:
        issues.append({
            "type": "multiple_license_files",
            "severity": "info",
            "message": f"Found {len(license_files)} license-related files",
            "files": [f.path for f in license_files],
            "suggestion": "Review all license files to ensure declared license is complete"
        })
    
    # License file but no declared license
    if license_files and not package.declared_license_expression:
        issues.append({
            "type": "license_file_without_declaration",
            "severity": "warning",
            "message": "License file exists but no license declared",
            "files": [f.path for f in license_files],
            "suggestion": "Extract license from license file and update declaration"
        })
    
    return issues

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

from django.db import models

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import nixpkgs
from scanpipe.pipes import scancode


class AnalyzeNixpkgsLicenses(Pipeline):
    """
    Analyze Nixpkgs packages for license clarity and correctness.
    
    This pipeline automatically finds and reports issues for licenses in Nixpkgs,
    including:
    - Detecting when a nixpkgs license declaration is incorrect
    - Determining what the correct license should be
    - Identifying ambiguous or unclear license declarations
    - Reporting license inconsistencies between declared and detected
    
    This pipeline applies specific rules for nixpkgs, given the large diversity
    of nixpkgs tech stacks and upstreams.
    
    Key features:
    - Scans package source code for license detections
    - Compares declared vs detected licenses
    - Checks for ecosystem-specific license patterns (Python, Rust, Node.js, etc.)
    - Detects copyleft compliance issues
    - Validates license file presence and consistency
    - Generates comprehensive license report with severity levels
    - Provides suggested license corrections with confidence scores
    
    Output:
    - Stores issues in package notes for review
    - Flags license detections needing manual review
    - Generates license report in project extra_data:
      * nixpkgs_license_issues: Dict of issues by package
      * nixpkgs_license_report: Comprehensive report with summary and grouping
    
    Example workflow:
    1. Copy inputs and extract archives
    2. Scan codebase for packages and licenses
    3. Analyze packages for license issues
    4. Flag packages and detections needing review
    5. Generate comprehensive report
    
    See scanpipe.pipes.nixpkgs for detailed license analysis functions.
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.scan_for_files,
            cls.collect_and_create_license_detections,
            cls.analyze_nixpkgs_license_issues,
            cls.flag_packages_with_license_issues,
            cls.flag_license_detections_needing_review,
            cls.generate_nixpkgs_license_report,
        )

    def analyze_nixpkgs_license_issues(self):
        """
        Analyze all packages in the project to detect license issues specific
        to nixpkgs packages.
        """
        self.log("Analyzing nixpkgs packages for license issues")
        
        issues = nixpkgs.analyze_license_issues(self.project)
        
        if issues:
            self.log(f"Found license issues in {len(issues)} package(s)")
            # Store issues in project extra_data for later reporting
            self.project.update_extra_data({
                "nixpkgs_license_issues": issues
            })
        else:
            self.log("No license issues detected")

    def flag_packages_with_license_issues(self):
        """
        Flag discovered packages that have license issues for review.
        """
        self.log("Flagging packages with license issues")
        
        issues = self.project.extra_data.get("nixpkgs_license_issues", {})
        
        for package_str, package_issues in issues.items():
            # Find package by its string representation or purl
            packages = self.project.discoveredpackages.filter(
                models.Q(package_url__contains=package_str) |
                models.Q(name__contains=package_str)
            )
            
            for package in packages:
                # Collect issue messages
                issue_messages = [
                    f"{issue['severity'].upper()}: {issue['message']}"
                    for issue in package_issues
                ]
                
                # Update package notes with issues
                current_notes = package.notes or ""
                new_notes = "\n".join([
                    current_notes,
                    "\n=== License Issues ===",
                    *issue_messages,
                ])
                package.update(notes=new_notes.strip())
                
                # Get detected licenses for this package
                detected_licenses = nixpkgs.get_detected_licenses_for_package(package)
                
                # Try to suggest correction if declared license is wrong
                if detected_licenses:
                    suggestion = nixpkgs.suggest_license_correction(
                        package,
                        detected_licenses
                    )
                    if suggestion and package.declared_license_expression:
                        if suggestion["suggested_license"] != package.declared_license_expression:
                            self.log(
                                f"Package {package}: suggested license "
                                f"'{suggestion['suggested_license']}' "
                                f"(confidence: {suggestion['confidence']})"
                            )
                            # Add suggestion to notes
                            suggestion_note = (
                                f"\nSuggested license: {suggestion['suggested_license']} "
                                f"(confidence: {suggestion['confidence']})\n"
                                f"Reason: {suggestion['reason']}"
                            )
                            package.update(notes=package.notes + suggestion_note)

    def flag_license_detections_needing_review(self):
        """
        Automatically check all license detections for issues and flag them
        for review when needed.
        """
        self.log("Checking license detections for issues")
        
        # Get all license detections in the project
        license_detections = self.project.discoveredlicenses.all()
        
        flagged_count = 0
        for detection in license_detections:
            # Check for issues using existing scancode functionality
            if not detection.needs_review:
                scancode.check_license_detection_for_issues(detection)
                if detection.needs_review:
                    flagged_count += 1
        
        self.log(f"Flagged {flagged_count} license detections for review")

    def generate_nixpkgs_license_report(self):
        """
        Generate a comprehensive license report for all nixpkgs packages.
        """
        self.log("Generating nixpkgs license report")
        
        report = nixpkgs.generate_license_report(self.project)
        
        # Store report in project extra_data
        self.project.update_extra_data({
            "nixpkgs_license_report": report
        })
        
        # Log summary
        summary = report["summary"]
        self.log(
            f"License Report Summary:\n"
            f"  Total packages: {summary['total_packages']}\n"
            f"  Packages with issues: {summary['packages_with_issues']}\n"
            f"  Total issues: {summary['total_issues']}\n"
            f"  Errors: {report['by_severity']['error']}\n"
            f"  Warnings: {report['by_severity']['warning']}\n"
            f"  Info: {report['by_severity']['info']}"
        )

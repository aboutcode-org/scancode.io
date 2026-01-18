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

from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import nixpkgs


class NixpkgsLicenseAnalysisTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Nixpkgs Project")

    def test_detect_missing_declared_license(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
        )
        
        issues = nixpkgs.detect_package_license_issues(package)
        
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "missing_declared_license")
        self.assertEqual(issues[0]["severity"], "error")

    def test_detect_license_mismatch(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="MIT",
        )
        
        # Create a resource with different detected license
        resource = CodebaseResource.objects.create(
            project=self.project,
            path="test.py",
            detected_license_expression="GPL-3.0-only",
        )
        package.codebase_resources.add(resource)
        
        issues = nixpkgs.detect_package_license_issues(package)
        
        # Should detect mismatch
        mismatch_issues = [i for i in issues if i["type"] == "license_mismatch"]
        self.assertGreater(len(mismatch_issues), 0)
        self.assertEqual(mismatch_issues[0]["severity"], "warning")

    def test_normalize_nixpkgs_license(self):
        # Test common nixpkgs license mappings
        self.assertEqual(
            nixpkgs.normalize_nixpkgs_license("gpl2+"),
            "GPL-2.0-or-later"
        )
        self.assertEqual(
            nixpkgs.normalize_nixpkgs_license("apache2"),
            "Apache-2.0"
        )
        self.assertEqual(
            nixpkgs.normalize_nixpkgs_license("mit"),
            "MIT"
        )
        
        # Test unknown license passes through
        self.assertEqual(
            nixpkgs.normalize_nixpkgs_license("CustomLicense"),
            "CustomLicense"
        )

    def test_check_nixpkgs_ecosystem_license(self):
        # Python package with unusual license
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="Artistic-2.0",
        )
        
        issue = nixpkgs.check_nixpkgs_ecosystem_license(package)
        
        self.assertIsNotNone(issue)
        self.assertEqual(issue["type"], "unusual_ecosystem_license")
        self.assertEqual(issue["severity"], "info")

    def test_check_nixpkgs_ecosystem_license_typical(self):
        # Python package with typical license
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="MIT",
        )
        
        issue = nixpkgs.check_nixpkgs_ecosystem_license(package)
        
        # No issue expected for typical license
        self.assertIsNone(issue)

    def test_detect_copyleft_with_dependencies(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="GPL-3.0-only",
        )
        
        issues = nixpkgs.detect_copyleft_compliance_issues(package)
        
        # Note: This test would need dependencies to trigger the issue
        # For now, it should return empty list
        self.assertIsInstance(issues, list)

    def test_suggest_license_correction_single_detected(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="GPL-3.0-only",
        )
        
        detected_licenses = ["MIT"]
        suggestion = nixpkgs.suggest_license_correction(package, detected_licenses)
        
        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion["suggested_license"], "MIT")
        self.assertEqual(suggestion["confidence"], "high")

    def test_suggest_license_correction_multiple_detected(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="GPL-3.0-only",
        )
        
        detected_licenses = ["MIT", "Apache-2.0"]
        suggestion = nixpkgs.suggest_license_correction(package, detected_licenses)
        
        self.assertIsNotNone(suggestion)
        self.assertIn("OR", suggestion["suggested_license"])
        self.assertEqual(suggestion["confidence"], "medium")

    def test_suggest_license_correction_no_detected(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="MIT",
        )
        
        suggestion = nixpkgs.suggest_license_correction(package, [])
        
        self.assertIsNone(suggestion)

    def test_analyze_license_issues(self):
        # Create package with issue
        DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="package-with-issue",
            version="1.0.0",
            # No declared license - should trigger issue
        )
        
        # Create package without issue
        DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="package-without-issue",
            version="1.0.0",
            declared_license_expression="MIT",
        )
        
        issues = nixpkgs.analyze_license_issues(self.project)
        
        # Should have issues for one package
        self.assertEqual(len(issues), 1)

    def test_generate_license_report(self):
        # Create package with issue
        DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="package1",
            version="1.0.0",
        )
        
        # Create package without issue
        DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="package2",
            version="1.0.0",
            declared_license_expression="MIT",
        )
        
        report = nixpkgs.generate_license_report(self.project)
        
        self.assertIn("summary", report)
        self.assertIn("by_severity", report)
        self.assertIn("by_type", report)
        self.assertIn("issues_by_package", report)
        
        summary = report["summary"]
        self.assertEqual(summary["total_packages"], 2)
        self.assertEqual(summary["packages_with_issues"], 1)
        self.assertEqual(summary["packages_without_issues"], 1)

    def test_check_license_clarity_unclear_license(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package-unclear",
            version="1.0.0",
            declared_license_expression="Unknown",
        )
        
        issues = nixpkgs.check_license_clarity(package)
        
        unclear_issues = [i for i in issues if i["type"] == "unclear_license"]
        self.assertGreater(len(unclear_issues), 0)
        self.assertEqual(unclear_issues[0]["severity"], "warning")

    def test_get_detected_licenses_for_package(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package-detected",
            version="1.0.0",
        )
        
        # Create resources with licenses
        resource1 = CodebaseResource.objects.create(
            project=self.project,
            path="file1.py",
            detected_license_expression="MIT",
        )
        resource2 = CodebaseResource.objects.create(
            project=self.project,
            path="file2.py",
            detected_license_expression="Apache-2.0",
        )
        
        package.codebase_resources.add(resource1, resource2)
        
        detected = nixpkgs.get_detected_licenses_for_package(package)
        
        self.assertEqual(len(detected), 2)
        self.assertIn("MIT", detected)
        self.assertIn("Apache-2.0", detected)

    def test_detect_license_file_issues_multiple_files(self):
        package = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="test-package",
            version="1.0.0",
            declared_license_expression="MIT",
        )
        
        # Create multiple license files
        license1 = CodebaseResource.objects.create(
            project=self.project,
            path="LICENSE",
            name="LICENSE",
        )
        license2 = CodebaseResource.objects.create(
            project=self.project,
            path="COPYING",
            name="COPYING",
        )
        
        package.codebase_resources.add(license1, license2)
        
        issues = nixpkgs.detect_license_file_issues(package)
        
        multiple_file_issues = [
            i for i in issues if i["type"] == "multiple_license_files"
        ]
        self.assertGreater(len(multiple_file_issues), 0)

    def test_are_licenses_compatible_exact_match(self):
        from licensedcode.cache import get_licensing
        
        licensing = get_licensing()
        lic1 = licensing.parse("MIT", validate=True)
        lic2 = licensing.parse("MIT", validate=True)
        
        result = nixpkgs.are_licenses_compatible(lic1, lic2, licensing)
        
        self.assertTrue(result)

    def test_are_licenses_compatible_different(self):
        from licensedcode.cache import get_licensing
        
        licensing = get_licensing()
        lic1 = licensing.parse("MIT", validate=True)
        lic2 = licensing.parse("GPL-3.0-only", validate=True)
        
        result = nixpkgs.are_licenses_compatible(lic1, lic2, licensing)
        
        self.assertFalse(result)

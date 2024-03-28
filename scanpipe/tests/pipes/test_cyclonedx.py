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

import json
from pathlib import Path

from django.test import TestCase

from cyclonedx.model import license as cdx_license_model
from cyclonedx.model.bom import Bom
from cyclonedx.validation import ValidationError

from scanpipe.pipes import cyclonedx


class ScanPipeCycloneDXPipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data" / "cyclonedx"
    bom_file = data_location / "nested.cdx.json"

    def setUp(self):
        self.bom_json = self.bom_file.read_text()
        self.bom_parsed = json.loads(self.bom_json)
        self.bom = Bom.from_json(data=self.bom_parsed)
        self.component1 = self.bom.components[0]
        self.component2 = self.component1.components[0]
        self.component3 = self.component2.components[0]

    def test_scanpipe_cyclonedx_is_cyclonedx_bom(self):
        # JSON
        self.assertTrue(cyclonedx.is_cyclonedx_bom(self.bom_file))
        input_location = self.data_location / "missing_schema.json"
        self.assertTrue(cyclonedx.is_cyclonedx_bom(input_location))
        input_location = self.data_location / "missing_bom_format.json"
        self.assertFalse(cyclonedx.is_cyclonedx_bom(input_location))

        # XML
        input_location = self.data_location / "laravel-7.12.0" / "bom.1.4.xml"
        self.assertTrue(cyclonedx.is_cyclonedx_bom(input_location))
        input_location = self.data_location / "not_valid.xml"
        self.assertFalse(cyclonedx.is_cyclonedx_bom(input_location))

    def test_scanpipe_cyclonedx_get_components(self):
        empty_bom = Bom()
        self.assertEqual([], cyclonedx.get_components(empty_bom))

        components = cyclonedx.get_components(self.bom)
        self.assertEqual(3, len(components))

        purls = [component.bom_ref.value for component in components]
        expected = [
            "pkg:pypi/toml@0.10.2?extension=tar.gz",
            "pkg:pypi/fictional@9.10.2",
            "pkg:pypi/billiard@3.6.3.0",
        ]
        self.assertEqual(sorted(expected), (sorted(purls)))

    def test_scanpipe_cyclonedx_resolve_license(self):
        license = cdx_license_model.LicenseExpression("OFL-1.1 AND Apache-2.0")
        result = cyclonedx.resolve_license(license)
        expected = "OFL-1.1 AND Apache-2.0"
        self.assertEqual(result, expected)

        license = cdx_license_model.DisjunctiveLicense(id="OFL-1.1")
        result = cyclonedx.resolve_license(license)
        expected = "OFL-1.1"
        self.assertEqual(result, expected)

        license = cdx_license_model.DisjunctiveLicense(name="Apache-2.0")
        result = cyclonedx.resolve_license(license)
        expected = "Apache-2.0"
        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_declared_licenses(self):
        # This component is using license id and name
        result = cyclonedx.get_declared_licenses(self.component1.licenses)
        expected = "OFL-1.1\nApache-2.0"
        self.assertEqual(result, expected)

        # This component is using license_expression
        result = cyclonedx.get_declared_licenses(self.component2.licenses)
        expected = "BSD-3-Clause"
        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_checksums(self):
        result = cyclonedx.get_checksums(self.component1)
        expected = {
            "sha256": "806143ae5bfb6a3c6e736a764057db0e6a0e05e338b5630894a5f779cabb4f9b"
        }

        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_external_references(self):
        result = cyclonedx.get_external_references(self.component1)
        expected = {
            "vcs": ["https://cyclonedx.org/vcs"],
            "issue-tracker": ["https://cyclonedx.org/issue-tracker"],
            "website": ["https://cyclonedx.org/website"],
            "advisories": ["https://cyclonedx.org/advisories"],
            "bom": ["https://cyclonedx.org/bom"],
            "mailing-list": ["https://cyclonedx.org/mailing-list"],
        }

        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_properties_data(self):
        properties_data = cyclonedx.get_properties_data(self.component3)
        expected = {
            "download_url": "https://download.url/package.zip",
            "filename": "package.zip",
            "homepage_url": "https://home.page",
            "primary_language": "Python",
        }
        self.assertEqual(expected, properties_data)

    def test_scanpipe_cyclonedx_validate_document(self):
        error = cyclonedx.validate_document(document="{}")
        self.assertIsInstance(error, ValidationError)
        self.assertEqual("'specVersion' is a required property", str(error))

        error = cyclonedx.validate_document(document='{"specVersion": "1.5"}')
        self.assertIsInstance(error, ValidationError)
        self.assertIn("'bomFormat' is a required property", str(error)[:50])

        error = cyclonedx.validate_document(self.bom_json)
        self.assertIsNone(error)

    def test_scanpipe_cyclonedx_component_to_package_data(self):
        expected = {
            "name": "toml",
            "extracted_license_statement": "OFL-1.1\nApache-2.0",
            "version": "0.10.2",
            "extra_data": {
                "externalReferences": {
                    "advisories": ["https://cyclonedx.org/advisories"],
                    "bom": ["https://cyclonedx.org/bom"],
                    "issue-tracker": ["https://cyclonedx.org/issue-tracker"],
                    "mailing-list": ["https://cyclonedx.org/mailing-list"],
                    "vcs": ["https://cyclonedx.org/vcs"],
                    "website": ["https://cyclonedx.org/website"],
                },
                "nestedComponents": [
                    "pkg:pypi/billiard@3.6.3.0",
                    "pkg:pypi/fictional@9.10.2",
                ],
            },
            "type": "pypi",
            "qualifiers": "extension=tar.gz",
            "sha256": (
                "806143ae5bfb6a3c6e736a764057db0e6a0e05e338b5630894a5f779cabb4f9b"
            ),
            "homepage_url": "https://cyclonedx.org/website",
        }
        package_data = cyclonedx.cyclonedx_component_to_package_data(self.component1)
        self.assertEqual(expected, package_data)

    def test_scanpipe_cyclonedx_resolve_cyclonedx_packages(self):
        input_location = self.data_location / "missing_schema.json"
        with self.assertRaises(ValueError) as cm:
            cyclonedx.resolve_cyclonedx_packages(input_location)
        expected_error = (
            'CycloneDX document "missing_schema.json" is not valid:\n'
            "Additional properties are not allowed ('invalid_entry' was unexpected)"
        )
        self.assertIn(expected_error, str(cm.exception))

        packages = cyclonedx.resolve_cyclonedx_packages(self.bom_file)
        self.assertEqual(3, len(packages))

        # JSON v1.2
        input_location = self.data_location / "laravel-7.12.0" / "bom.1.2.json"
        packages = cyclonedx.resolve_cyclonedx_packages(input_location)
        self.assertEqual(63, len(packages))

        # JSON v1.3
        input_location = self.data_location / "laravel-7.12.0" / "bom.1.3.json"
        packages = cyclonedx.resolve_cyclonedx_packages(input_location)
        self.assertEqual(63, len(packages))

        # JSON v1.4
        input_location = self.data_location / "laravel-7.12.0" / "bom.1.4.json"
        packages = cyclonedx.resolve_cyclonedx_packages(input_location)
        self.assertEqual(63, len(packages))

        # JSON v1.5 (this file is generated by the to_cyclonedx)
        input_location = self.data_location / "asgiref-3.3.0.cdx.json"
        packages = cyclonedx.resolve_cyclonedx_packages(input_location)
        self.assertEqual(3, len(packages))

        # XML v1.4
        input_location = self.data_location / "laravel-7.12.0" / "bom.1.4.xml"
        packages = cyclonedx.resolve_cyclonedx_packages(input_location)
        self.assertEqual(63, len(packages))

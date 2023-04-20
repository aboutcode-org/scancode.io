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

from scanpipe.pipes import resolve


class ScanPipeResolvePipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"
    manifest_location = data_location / "manifests"

    def test_scanpipe_pipes_resolve_get_default_package_type(self):
        self.assertIsNone(resolve.get_default_package_type(input_location=""))

        input_location = self.manifest_location / "Django-4.0.8-py3-none-any.whl.ABOUT"
        self.assertEqual("about", resolve.get_default_package_type(input_location))

        input_location = self.manifest_location / "toml.spdx.json"
        self.assertEqual("spdx", resolve.get_default_package_type(input_location))

        input_location = self.manifest_location / "toml.json"
        self.assertEqual("spdx", resolve.get_default_package_type(input_location))

        input_location = self.data_location / "cyclonedx/nested.bom.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

        input_location = self.data_location / "cyclonedx/asgiref-3.3.0.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

        input_location = self.data_location / "cyclonedx/missing_schema.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

    def test_scanpipe_pipes_resolve_set_license_expression(self):
        declared_license = {"license": "MIT"}
        data = resolve.set_license_expression({"declared_license": declared_license})
        self.assertEqual("mit", data.get("license_expression"))

        declared_license = {
            "classifiers": [
                "License :: OSI Approved :: Python Software Foundation License"
            ]
        }
        data = resolve.set_license_expression({"declared_license": declared_license})
        self.assertEqual("python", data.get("license_expression"))

        declared_license = "GPL 2.0"
        data = resolve.set_license_expression({"declared_license": declared_license})
        self.assertEqual("gpl-2.0", data.get("license_expression"))

    def test_scanpipe_pipes_resolve_resolve_packages(self):
        # ScanCode.io resolvers
        input_location = self.manifest_location / "Django-4.0.8-py3-none-any.whl.ABOUT"
        packages = resolve.resolve_packages(str(input_location))
        expected = {
            "filename": "Django-4.0.8-py3-none-any.whl",
            "download_url": "https://python.org/Django-4.0.8-py3-none-any.whl",
            "license_expression": "bsd-new",
            "md5": "386349753c386e574dceca5067e2788a",
            "name": "django",
            "sha1": "4cc6f7abda928a0b12cd1f1cd8ad3677519ca04e",
            "type": "pypi",
            "version": "4.0.8",
        }
        self.assertEqual([expected], packages)

        # ScanCode-toolkit resolvers
        input_location = self.manifest_location / "package.json"
        packages = resolve.resolve_packages(str(input_location))
        expected_location = self.manifest_location / "package.expected.json"
        expected = json.loads(expected_location.read_text())
        self.assertEqual(expected, packages)

    def test_scanpipe_pipes_resolve_resolve_about_packages(self):
        input_location = self.manifest_location / "Django-4.0.8-py3-none-any.whl.ABOUT"
        package = resolve.resolve_about_packages(str(input_location))
        expected = {
            "filename": "Django-4.0.8-py3-none-any.whl",
            "download_url": "https://python.org/Django-4.0.8-py3-none-any.whl",
            "license_expression": "bsd-new",
            "md5": "386349753c386e574dceca5067e2788a",
            "name": "django",
            "sha1": "4cc6f7abda928a0b12cd1f1cd8ad3677519ca04e",
            "type": "pypi",
            "version": "4.0.8",
        }
        self.assertEqual([expected], package)

        input_location = self.manifest_location / "poor_values.ABOUT"
        package = resolve.resolve_about_packages(str(input_location))
        expected = {"name": "project"}
        self.assertEqual([expected], package)

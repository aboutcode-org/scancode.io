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

from scanpipe import pipes
from scanpipe.models import Project
from scanpipe.pipes import resolve
from scanpipe.tests import package_data1


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

        input_location = self.data_location / "cyclonedx/nested.cdx.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

        input_location = self.data_location / "cyclonedx/asgiref-3.3.0.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

        input_location = self.data_location / "cyclonedx/missing_schema.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

    def test_scanpipe_pipes_resolve_set_license_expression(self):
        extracted_license_statement = {"license": "MIT"}
        data = resolve.set_license_expression(
            {"extracted_license_statement": extracted_license_statement}
        )
        self.assertEqual("mit", data.get("declared_license_expression"))

        extracted_license_statement = {
            "classifiers": [
                "License :: OSI Approved :: Python Software Foundation License"
            ]
        }
        data = resolve.set_license_expression(
            {"extracted_license_statement": extracted_license_statement}
        )
        self.assertEqual("python", data.get("declared_license_expression"))

        extracted_license_statement = "GPL 2.0"
        data = resolve.set_license_expression(
            {"extracted_license_statement": extracted_license_statement}
        )
        self.assertEqual("gpl-2.0", data.get("declared_license_expression"))

    def test_scanpipe_pipes_resolve_convert_spdx_expression(self):
        spdx = "MIT OR GPL-2.0-only WITH LicenseRef-scancode-generic-exception"
        scancode_expression = "mit OR gpl-2.0 WITH generic-exception"
        self.assertEqual(scancode_expression, resolve.convert_spdx_expression(spdx))

    def test_scanpipe_pipes_resolve_resolve_packages(self):
        # ScanCode.io resolvers
        input_location = self.manifest_location / "Django-4.0.8-py3-none-any.whl.ABOUT"
        packages = resolve.resolve_packages(str(input_location))
        expected = {
            "filename": "Django-4.0.8-py3-none-any.whl",
            "download_url": "https://python.org/Django-4.0.8-py3-none-any.whl",
            "declared_license_expression": "bsd-new",
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
            "declared_license_expression": "bsd-new",
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

    def test_scanpipe_pipes_resolve_spdx_package_to_discovered_package_data(self):
        p1 = Project.objects.create(name="Analysis")
        package = pipes.update_or_create_package(p1, package_data1)
        package_spdx = package.as_spdx()
        package_data = resolve.spdx_package_to_discovered_package_data(package_spdx)
        expected = {
            "name": "adduser",
            "download_url": "https://download.url/package.zip",
            "declared_license_expression": "gpl-2.0 AND gpl-2.0-plus",
            "declared_license_expression_spdx": "GPL-2.0-only AND GPL-2.0-or-later",
            "extracted_license_statement": "GPL-2.0-only AND GPL-2.0-or-later",
            "copyright": (
                "Copyright (c) 2000 Roland Bauerschmidt <rb@debian.org>\n"
                "Copyright (c) 1997, 1998, 1999 Guy Maor <maor@debian.org>\n"
                "Copyright (c) 1995 Ted Hajek <tedhajek@boombox.micro.umn.edu>\n"
                "portions Copyright (c) 1994 Debian Association, Inc."
            ),
            "version": "3.118",
            "homepage_url": "https://packages.debian.org",
            "filename": "package.zip",
            "description": "add and remove users and groups",
            "release_date": "1999-10-10",
            "type": "deb",
            "namespace": "debian",
            "qualifiers": "arch=all",
            "md5": "76cf50f29e47676962645632737365a7",
        }
        self.assertEqual(expected, package_data)

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

"""Tests for npm-health helper utilities."""

from datetime import UTC
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.test import SimpleTestCase

from scanpipe.pipes import npm_health


class NpmHealthPipesTest(SimpleTestCase):

    def test_validate_npm_package_url(self):
        package = npm_health.validate_npm_package_url("pkg:npm/lodash@4.17.21")
        self.assertEqual("npm", package.type)
        self.assertEqual("lodash", package.name)
        self.assertEqual("4.17.21", package.version)


    def test_parse_package_url_rejects_empty_value(self):
        with self.assertRaises(npm_health.NpmHealthPayloadError):
            npm_health.parse_package_url("")


    def test_validate_npm_package_url_rejects_other_types(self):
        with self.assertRaises(npm_health.NpmHealthPayloadError):
            npm_health.validate_npm_package_url("pkg:pypi/django@5.2")


    def test_validate_npm_package_url_requires_version(self):
        with self.assertRaises(npm_health.NpmHealthPayloadError):
            npm_health.validate_npm_package_url("pkg:npm/lodash")


    def test_get_package_name_supports_scopes(self):
        package = npm_health.validate_npm_package_url(
            "pkg:npm/%40babel/core@7.28.0"
        )
        self.assertEqual("@babel/core", npm_health.get_package_name(package))


    def test_get_registry_metadata_url_for_scoped_package(self):
        package = npm_health.validate_npm_package_url(
            "pkg:npm/%40babel/core@7.28.0"
        )
        self.assertEqual(
            "https://registry.npmjs.org/@babel%2Fcore/7.28.0",
            npm_health.get_registry_metadata_url(package),
        )


    def test_normalize_repository_url_dict(self):
        repository = {"type": "git", "url": "git+https://github.com/a/b.git"}
        self.assertEqual(
            "https://github.com/a/b",
            npm_health.normalize_repository_url(repository),
        )


    def test_normalize_repository_url_git_transports(self):
        self.assertEqual(
            "https://github.com/a/b",
            npm_health.normalize_repository_url("git://github.com/a/b.git"),
        )
        self.assertEqual(
            "https://github.com/a/b",
            npm_health.normalize_repository_url("git@github.com:a/b.git"),
        )

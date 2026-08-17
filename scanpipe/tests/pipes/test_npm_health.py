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


    def test_build_collection_targets(self):
        metadata = {
            "repository": {"url": "https://github.com/a/b.git"},
            "homepage": "https://example.com",
            "dist": {"tarball": "https://registry.example/a.tgz"},
        }
        self.assertEqual(
            {
                "repository_url": "https://github.com/a/b",
                "tarball_url": "https://registry.example/a.tgz",
                "homepage_url": "https://example.com",
            },
            npm_health.build_collection_targets(metadata),
        )


    def test_normalize_metric_value_fraction(self):
        self.assertEqual(0.75, npm_health.normalize_metric_value(0.75))


    def test_normalize_metric_value_percentage(self):
        self.assertEqual(0.75, npm_health.normalize_metric_value(75))
        self.assertEqual(1.0, npm_health.normalize_metric_value(150))


    def test_normalize_metrics_nested_payload(self):
        self.assertEqual(
            {"activity": 0.8, "security": 1.0},
            npm_health.normalize_metrics(
                {"metrics": {"activity": 80, "security": True}}
            ),
        )


    def test_collect_registry_metrics(self):
        metadata = {
            "repository": {"url": "https://github.com/a/b.git"},
            "homepage": "https://example.com",
            "license": "MIT",
            "maintainers": [{"name": "a"}, {"name": "b"}, {"name": "c"}],
            "dependencies": {"one": "1", "two": "2"},
        }
        metrics = npm_health.collect_registry_metrics(metadata)
        self.assertEqual(1.0, metrics["metadata_completeness"])
        self.assertEqual(1.0, metrics["maintainer_presence"])
        self.assertGreater(metrics["dependency_simplicity"], 0.9)


    def test_merge_metrics_external_values_override_baseline(self):
        merged = npm_health.merge_metrics(
            {"activity": 0.2, "security": 0.5},
            {"activity": 90},
        )
        self.assertEqual({"activity": 0.9, "security": 0.5}, merged)


    def test_normalize_weights_ignores_non_positive_values(self):
        self.assertEqual(
            {"activity": 2.0},
            npm_health.normalize_weights({"activity": 2, "security": 0}),
        )


    def test_compute_health_score(self):
        score = npm_health.compute_health_score(
            {"activity": 1.0, "security": 0.5},
            {"activity": 1.0, "security": 1.0},
        )
        self.assertEqual(75.0, score)


    def test_classify_health_score(self):
        self.assertEqual("excellent", npm_health.classify_health_score(90))
        self.assertEqual("good", npm_health.classify_health_score(70))
        self.assertEqual("needs-attention", npm_health.classify_health_score(50))
        self.assertEqual("high-risk", npm_health.classify_health_score(20))

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


import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

from license_expression import Licensing

from scanpipe.pipes import flag
from scanpipe.pipes import utils


class ScanPipeUtilsTest(TestCase):
    def setUp(self):
        self.licensing = Licensing()

    @mock.patch("scanpipe.models.CodebaseResource")
    @mock.patch("scanpipe.models.DiscoveredPackage")
    @mock.patch("scanpipe.models.Project")
    def test_validate_package_license_integrity_mismatch(
        self, mock_project_class, mock_package_class, mock_resource_class
    ):
        mock_project = mock_project_class()
        mock_package = mock_package_class()

        mock_package.type = "pypi"
        mock_package.package_uid = "pkg:pypi/test@1.0"
        mock_package.get_declared_license_expression.return_value = "mit"
        mock_package.datafile_paths = ["src/main.py"]
        mock_package.extra_data = {}

        mock_project.discoveredpackages.all.return_value = [mock_package]

        mock_resource = mock_resource_class()
        mock_resource.path = "src/main.py"
        mock_resource.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource.detected_license_expression = "gpl-3.0"

        mock_project.codebaseresources.has_license_expression.return_value = [
            mock_resource
        ]

        mock_data_path = mock_resource_class()
        mock_data_path.extra_data = {}
        mock_project.codebaseresources.get.return_value = mock_data_path

        utils.validate_package_license_integrity(mock_project)

        package_update_args = mock_package.update_extra_data.call_args.args[0]
        self.assertEqual(
            package_update_args["issues"][0]["issue_type"], "License Mismatch"
        )
        self.assertEqual(
            package_update_args["issues"][0]["detected_codebase_license"], "gpl-3.0"
        )

        mock_data_path.update.assert_called_once_with(status=flag.LICENSE_ISSUE)

    def test_contains_ignore_pattern(self):
        ignore_patterns = ["*test*", "*.sh"]
        self.assertTrue(
            utils.contains_ignore_pattern("src/test_main.py", ignore_patterns)
        )
        self.assertTrue(
            utils.contains_ignore_pattern("scripts/build.sh", ignore_patterns)
        )
        self.assertFalse(utils.contains_ignore_pattern("src/main.py", ignore_patterns))

    def test_filter_ignored_licenses(self):
        exp1 = self.licensing.parse("mit")
        self.assertEqual(
            str(utils.filter_ignored_licenses(exp1, self.licensing)), "mit"
        )

        exp2 = self.licensing.parse("unknown")
        self.assertIsNone(utils.filter_ignored_licenses(exp2, self.licensing))

        exp3 = self.licensing.parse("mit AND unknown")
        self.assertEqual(
            str(utils.filter_ignored_licenses(exp3, self.licensing)), "mit"
        )

        exp4 = self.licensing.parse("unknown-spdx OR free-unknown")
        self.assertIsNone(utils.filter_ignored_licenses(exp4, self.licensing))

    def test_collect_detected_licenses(self):
        mock_resource1 = mock.Mock()
        mock_resource1.path = "src/main.py"
        mock_resource1.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource1.detected_license_expression = "mit AND unknown"

        mock_resource2 = mock.Mock()
        mock_resource2.path = "test/test_main.py"
        mock_resource2.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource2.detected_license_expression = "gpl-3.0"

        mock_resource3 = mock.Mock()
        mock_resource3.path = "src/other.py"
        mock_resource3.for_packages = ["pkg:pypi/test@2.0"]
        mock_resource3.detected_license_expression = "apache-2.0"

        resources = [mock_resource1, mock_resource2, mock_resource3]
        ignore_patterns = ["*test*"]

        result = utils.collect_detected_licenses(
            resources, ignore_patterns, package_uid="pkg:pypi/test@1.0"
        )

        self.assertEqual(result, ["(mit)"])

    def test_get_url_netloc_namespace_and_name(self):
        url = "https://github.com/aboutcode-org/scancode.io/"
        netloc, namespace, name = utils.get_url_netloc_namespace_and_name(url)
        self.assertEqual(netloc, "github.com")
        self.assertEqual(namespace, "aboutcode-org")
        self.assertEqual(name, "scancode.io")

        url_web = "https://example.com/ns/project/index.html"
        netloc, namespace, name = utils.get_url_netloc_namespace_and_name(url_web)
        self.assertEqual(netloc, "example.com")
        self.assertEqual(namespace, "ns")
        self.assertEqual(name, "project")

    @mock.patch("scanpipe.pipes.utils.fetch.fetch_url")
    def test_download_src_repo_success(self, mock_fetch):
        mock_fetch.return_value.path = "/test/downloaded_repo"
        result = utils.download_src_repo("https://example.com/repo.zip")
        self.assertEqual(result, "/test/downloaded_repo")

    @mock.patch("scanpipe.pipes.utils.fetch.fetch_url")
    def test_download_src_repo_failure(self, mock_fetch):
        mock_fetch.side_effect = ValueError("Invalid URL")
        result = utils.download_src_repo("invalid_url")
        self.assertIsNone(result)

    @mock.patch("scanpipe.pipes.utils.get_repo_download_url_by_package_type")
    @mock.patch("scanpipe.pipes.utils.clarify_version_tag")
    def test_get_download_url(self, mock_clarify, mock_get_repo_url):
        mock_clarify.return_value = "v1.0.0"
        mock_get_repo_url.return_value = (
            "https://github.com/namespace/repo_name/archive/v1.0.0.zip"
        )

        url = "https://github.com/namespace/repo_name"
        result = utils.get_download_url(url, "1.0.0")

        self.assertEqual(
            result, "https://github.com/namespace/repo_name/archive/v1.0.0.zip"
        )

    @mock.patch("scanpipe.pipes.utils.requests.get")
    def test_clarify_version_tag(self, mock_get):
        # Simulate 2 requests which the first returns 404 and the second
        # returns 200
        mock_get.side_effect = [mock.Mock(status_code=404), mock.Mock(status_code=200)]

        # The function tries prefixes in order: ["", "v", "V", "release-",
        # "RELEASE-", "v-", "V-"]
        result = utils.clarify_version_tag("github", "namespace", "name", "1.0.0")

        self.assertEqual(result, "v1.0.0")
        self.assertEqual(mock_get.call_count, 2)

    @mock.patch("scanpipe.pipes.utils.requests.get")
    def test_github_pages_to_repo(self, mock_get):
        mock_get.return_value = mock.Mock(status_code=200)
        url = "https://krumpetpirate.github.io/AAXtoMP3/"
        result = utils.github_pages_to_repo(url)
        self.assertEqual(result, "https://github.com/krumpetpirate/AAXtoMP3")

        # Failed mapping
        mock_get.return_value = mock.Mock(status_code=404)
        result_failed = utils.github_pages_to_repo(url)
        self.assertIsNone(result_failed)

    def test_get_all_files_and_count(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file1_path = Path(tmp_dir) / "file1.txt"
            file2_path = Path(tmp_dir) / "tmp" / "file2.txt"

            file2_path.parent.mkdir()
            # Use touch() to create empty files
            file1_path.touch()
            file2_path.touch()

            self.assertEqual(utils.count_total_files(tmp_dir), 2)

            file_map = utils.get_all_files(tmp_dir)
            self.assertIn("file1.txt", file_map)
            self.assertIn("tmp/file2.txt", file_map)
            self.assertEqual(file_map["file1.txt"]["name"], "file1.txt")
            self.assertIsNotNone(file_map["file1.txt"]["hash"])

    def test_consolidate_unmatched(self):
        all_files = ["src/main.py", "src/utils.py", "docs/readme.md", "docs/install.md"]
        unmatched_files = ["docs/readme.md", "docs/install.md", "src/utils.py"]

        result = utils.consolidate_unmatched(all_files, unmatched_files)

        # 'docs' directory is entirely unmatched.
        # 'src/utils.py' is unmatched, but 'src' has a matched file ('main.py').
        expected = [("docs", True), ("src/utils.py", False)]
        self.assertEqual(result, sorted(expected))

    @mock.patch("scanpipe.pipes.utils.get_all_files")
    def test_compare_directories(self, mock_get_all_files):
        mock_get_all_files.side_effect = [
            # input_source
            {
                "hello.py": {"hash": "123", "name": "hello.py"},
                "world.py": {"hash": "456", "name": "world.py"},
            },
            # source_repo
            {
                "hello.py": {"hash": "123", "name": "hello.py"},
                "universe.py": {"hash": "789", "name": "universe.py"},
            },
        ]

        matched_count, mismatches = utils.compare_directories("input", "repo")
        self.assertEqual(matched_count, 1)
        self.assertIn("[File] world.py", mismatches["input_source_only"])
        self.assertIn("[File] universe.py", mismatches["source_repo_only"])

    @mock.patch("scanpipe.models.DiscoveredPackage")
    @mock.patch("scanpipe.models.Project")
    def test_update_comparison_summary_package_found(
        self, mock_project_class, mock_package_class
    ):
        mock_project = mock_project_class()
        mock_package = mock_package_class()

        mock_project.discoveredpackages.filter.return_value.first.return_value = (
            mock_package
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            utils.update_comparison_summary(
                project=mock_project,
                purl="pkg:pypi/testg@1.0",
                devel_codebase_dir=temp_dir,
                src_repo_url="https://github.com/test/test",
                package_name="test",
                package_version="1.0",
                matched_count=3,
                mismatches={
                    "mismatches": [],
                    "input_source_only": [],
                    "source_repo_only": [],
                },
            )

            called_data = mock_package.update_extra_data.call_args.args[0]

            self.assertIn("comparison_summary", called_data)
            self.assertEqual(
                called_data["comparison_summary"]["total_matching_files"], 3
            )
            self.assertEqual(
                called_data["comparison_summary"]["input_source"], "pkg:pypi/testg@1.0"
            )

    def test_handle_operator_expression_and(self):
        expr = self.licensing.parse("mit AND apache-2.0")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertEqual(str(result), "mit AND apache-2.0")

    def test_handle_operator_expression_or(self):
        expr = self.licensing.parse("mit OR bsd-3-clause")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.OR
        )
        self.assertEqual(str(result), "mit OR bsd-3-clause")

    def test_handle_operator_expression_filters_to_single_arg(self):
        # 'unknown' gets filtered out to None, leaving only 'mit' (len == 1)
        expr = self.licensing.parse("mit AND unknown")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertEqual(str(result), "mit")

    def test_handle_operator_expression_all_filtered_out(self):
        # Both 'unknown' and 'free-unknown' get filtered out, leaving empty args
        expr = self.licensing.parse("unknown AND free-unknown")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertIsNone(result)

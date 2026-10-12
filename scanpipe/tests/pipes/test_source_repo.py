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
from unittest import mock

from django.test import TestCase

from scanpipe.pipes import source_repo


class ScanPipeSourceRepoTest(TestCase):
    @mock.patch("scanpipe.pipes.source_repo.fetch.fetch_url")
    def test_download_src_repo_success(self, mock_fetch):
        mock_fetch.return_value.path = "/test/downloaded_repo"
        result = source_repo.download_src_repo("https://example.com/repo.zip")
        self.assertEqual(result, "/test/downloaded_repo")

    @mock.patch("scanpipe.pipes.source_repo.fetch.fetch_url")
    def test_download_src_repo_failure(self, mock_fetch):
        mock_fetch.side_effect = ValueError("Invalid URL")
        result = source_repo.download_src_repo("invalid_url")
        self.assertIsNone(result)

    @mock.patch("scanpipe.pipes.source_repo.get_repo_download_url_by_package_type")
    @mock.patch("scanpipe.pipes.source_repo.clarify_version_tag")
    def test_get_download_url(self, mock_clarify, mock_get_repo_url):
        mock_clarify.return_value = "v1.0.0"
        mock_get_repo_url.return_value = (
            "https://github.com/namespace/repo_name/archive/v1.0.0.zip"
        )

        url = "https://github.com/namespace/repo_name"
        result = source_repo.get_download_url(url, "1.0.0")
        self.assertEqual(
            result, "https://github.com/namespace/repo_name/archive/v1.0.0.zip"
        )

    @mock.patch("scanpipe.pipes.source_repo.requests.get")
    def test_clarify_version_tag(self, mock_get):
        # Simulate 2 requests which the first returns 404 and the second
        # returns 200
        mock_get.side_effect = [
            mock.Mock(status_code=404),
            mock.Mock(status_code=200),
        ]

        result = source_repo.clarify_version_tag("github", "namespace", "name", "1.0.0")
        self.assertEqual(result, "v1.0.0")
        self.assertEqual(mock_get.call_count, 2)

    @mock.patch("scanpipe.pipes.source_repo.requests.get")
    def test_github_pages_to_repo(self, mock_get):
        mock_get.return_value = mock.Mock(status_code=200)
        url = "https://krumpetpirate.github.io/AAXtoMP3/"
        result = source_repo.github_pages_to_repo(url)
        self.assertEqual(result, "https://github.com/krumpetpirate/AAXtoMP3")

        # Failed mapping
        mock_get.return_value = mock.Mock(status_code=404)
        result_failed = source_repo.github_pages_to_repo(url)
        self.assertIsNone(result_failed)

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
            source_repo.update_comparison_summary(
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
                called_data["comparison_summary"]["input_source"],
                "pkg:pypi/testg@1.0",
            )

    def test_get_src_repo_download_url_missing_repository_url(self):
        url, warning = source_repo.get_src_repo_download_url(
            repository_url="", version="1.0.0"
        )
        self.assertIsNone(url)
        self.assertEqual(warning, "No source repository URL found in Cargo.toml.")

    @mock.patch("scanpipe.pipes.source_repo.get_download_url")
    def test_get_src_repo_download_url_unresolvable(self, mock_get_download_url):
        mock_get_download_url.return_value = None
        url, warning = source_repo.get_src_repo_download_url(
            repository_url="https://example.com/unknown",
            version="1.0.0",
        )
        self.assertIsNone(url)
        self.assertIn("Not able to determine", warning)

    @mock.patch("scanpipe.pipes.source_repo.get_download_url")
    def test_get_src_repo_download_url_success(self, mock_get_download_url):
        mock_get_download_url.return_value = "https://example.com/archive.zip"
        url, warning = source_repo.get_src_repo_download_url(
            repository_url="https://github.com/ns/repo",
            version="1.0.0",
        )
        self.assertEqual(url, "https://example.com/archive.zip")
        self.assertIsNone(warning)

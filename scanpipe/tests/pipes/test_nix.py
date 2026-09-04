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

from packageurl import PackageURL

from scanpipe.pipes import nix


class ScanPipeNixPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_nix_check_input_and_return_purl(self):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit=1234abcd"
        ]

        expected = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit=1234abcd"
        )
        result = nix.check_input_and_return_purl(project)
        self.assertEqual(result, expected)

    def test_scanpipe_nix_check_input_and_return_purl_no_input(self):
        project = mock.Mock()
        project.inputsources.all.return_value = []
        with self.assertRaisesMessage(ValueError, "Only 1 nix purl is accepted."):
            nix.check_input_and_return_purl(project)

    def test_scanpipe_nix_check_input_and_return_purl_multi_input(self):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux",
            "pkg:nix/nixpkgs/world@2.40.0?system=x86_64-linux",
        ]
        with self.assertRaisesMessage(ValueError, "Only 1 nix purl is accepted."):
            nix.check_input_and_return_purl(project)

    def test_scanpipe_nix_check_input_and_return_purl_non_supported_type(self):
        project = mock.Mock()
        project.inputsources.all.return_value = ["pkg:npm/test@1.0"]
        with self.assertRaisesMessage(ValueError, "Only nix purl is supported."):
            nix.check_input_and_return_purl(project)

    def test_scanpipe_nix_check_input_and_return_purl_invalid_namespace(self):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:nix/namespace/hello@2.12.1?system=x86_64-linux"
        ]
        with self.assertRaisesMessage(
            Exception, "Only official nixpkgs repository is supported"
        ):
            nix.check_input_and_return_purl(project)

    def test_scanpipe_nix_check_input_and_return_purl_missing_version_and_commit(self):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:nix/nixpkgs/hello?system=x86_64-linux"
        ]
        with self.assertRaisesMessage(
            Exception, "Version or a 'commit' qualifier is required."
        ):
            nix.check_input_and_return_purl(project)

    def test_scanpipe_nix_check_input_and_return_purl_missing_system(self):
        project = mock.Mock()
        project.inputsources.all.return_value = ["pkg:nix/nixpkgs/hello@2.12.1"]
        with self.assertRaisesMessage(
            Exception,
            "The 'system' qualifier is required to resolve system-specific binaries.",
        ):
            nix.check_input_and_return_purl(project)

    @mock.patch("scanpipe.pipes.nix.fetch_json_response")
    def test_scanpipe_nix_get_package_data(self, mock_fetch_json):
        mock_fetch_json.return_value = {
            "releases": [
                {
                    "version": "2.12.1",
                    "platforms": [
                        {
                            "arch": "x86-64",
                            "os": "Linux",
                            "system": "x86_64-linux",
                            "commit_hash": "1234abcd",
                            "outputs": [
                                {
                                    "name": "out",
                                    "path": "/nix/store/aaaaaaa-hello-2.12.1",
                                }
                            ],
                        }
                    ],
                    "platforms_summary": "Linux only",
                    "outputs_summary": "out",
                }
            ]
        }
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )

        result = nix.get_package_data(purl)
        self.assertEqual(
            result,
            {
                "releases": [
                    {
                        "version": "2.12.1",
                        "platforms": [
                            {
                                "arch": "x86-64",
                                "os": "Linux",
                                "system": "x86_64-linux",
                                "commit_hash": "1234abcd",
                                "outputs": [
                                    {
                                        "name": "out",
                                        "path": "/nix/store/aaaaaaa-hello-2.12.1",
                                    }
                                ],
                            }
                        ],
                        "platforms_summary": "Linux only",
                        "outputs_summary": "out",
                    }
                ]
            },
        )
        mock_fetch_json.assert_called_once_with(
            "https://search.devbox.sh/v2/pkg?name=hello"
        )

    def test_scanpipe_nix_get_commit_hash_nix_store_path(self):
        data = {
            "releases": [
                {
                    "version": "2.12.1",
                    "platforms": [
                        {
                            "system": "x86_64-linux",
                            "commit_hash": "1234abcd",
                            "outputs": [
                                {
                                    "name": "out",
                                    "path": "/nix/store/aaaaaaa-hello-2.12.1",
                                },
                                {
                                    "name": "debug",
                                    "path": "/nix/store/aaaaaaa-hello-2.12.1-debug",
                                },
                            ],
                        }
                    ],
                }
            ]
        }

        commit, store_path = nix.get_commit_hash_nix_store_path(
            data, "x86_64-linux", "out", "2.12.1", "1234abcd"
        )
        self.assertEqual(commit, "1234abcd")
        self.assertEqual(store_path, "/nix/store/aaaaaaa-hello-2.12.1")

    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_get_nix_store_path_with_nix(self, mock_subprocess_run):
        mock_result = mock.Mock()
        mock_result.stdout = "/nix/store/evaluated-path-out"
        mock_subprocess_run.return_value = mock_result

        path = nix.get_nix_store_path_with_nix(
            "hello", "x86_64-linux", "out", "1234abcd"
        )
        self.assertEqual(path, "/nix/store/evaluated-path-out")

    @mock.patch("scanpipe.pipes.nix.get_narinfo_url")
    def test_scanpipe_nix_get_nix_download_url(self, mock_get_narinfo):
        mock_get_narinfo.return_value = "nar/abc.nar.xz"
        store_path = "/nix/store/aaaaaaaaaaaaa-hello-2.12.1"

        url = nix.get_nix_download_url(store_path)
        self.assertEqual(url, "https://cache.nixos.org/nar/abc.nar.xz")

    @mock.patch("scanpipe.pipes.nix.requests.get")
    def test_scanpipe_nix_get_narinfo_url(self, mock_requests_get):
        mock_response = mock.Mock()
        mock_response.text = "StorePath: /nix/store/xyz\nURL: nar/123.nar.xz"
        mock_requests_get.return_value = mock_response

        url_path = nix.get_narinfo_url("https://cache.nixos.org/aaaaaaaaaaa.narinfo")
        self.assertEqual(url_path, "nar/123.nar.xz")

    @mock.patch("scanpipe.pipes.nix.get_package_data")
    @mock.patch("scanpipe.pipes.nix.get_commit_hash_nix_store_path")
    @mock.patch("scanpipe.pipes.nix.get_nix_download_url")
    @mock.patch("scanpipe.pipes.nix.get_patched_source_with_docker")
    @mock.patch("scanpipe.pipes.utils.fetch_path")
    def test_scanpipe_nix_fetch_inputs(
        self,
        mock_fetch_path,
        mock_get_patched_source,
        mock_get_download_url,
        mock_get_store_path,
        mock_get_package_data,
    ):
        mock_get_package_data.return_value = {"releases": []}
        mock_get_store_path.return_value = ("1234abcd", "/nix/store/aaaaaaaaaa")
        mock_get_download_url.return_value = "https://cache.nixos.org/nar/hello.nar.xz"
        mock_get_patched_source.return_value = "/path/extracted/from"
        mock_fetch_path.return_value = "/path/debug/to"

        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit=1234abcd"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            src_path, bin_path, output_fmt = nix.fetch_inputs(purl, temp_dir)

            self.assertEqual(src_path, "/path/extracted/from")
            self.assertEqual(bin_path, "/path/debug/to")
            self.assertEqual(output_fmt, "debug")

    @mock.patch("scanpipe.pipes.nix.get_commit_hash_nix_store_path")
    def test_scanpipe_nix_get_nix_store_path_success(self, mock_get_store_path):
        mock_get_store_path.return_value = ("1234abcd", "/nix/store/hello-path")

        output_fmt, path, commit = nix.get_nix_store_path(
            data={"releases": []},
            name="hello",
            version="2.12.1",
            system="x86_64-linux",
            commit_hash="1234abcd",
            user_output="",
        )

        self.assertEqual(output_fmt, "debug")
        self.assertEqual(path, "/nix/store/hello-path")
        self.assertEqual(commit, "1234abcd")

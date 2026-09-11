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
    @mock.patch("scanpipe.pipes.nix.get_nix_store_path_with_nix")
    @mock.patch("scanpipe.pipes.nix.get_nix_download_url")
    @mock.patch("scanpipe.pipes.nix.get_patched_source_with_docker")
    @mock.patch("scanpipe.pipes.utils.fetch_path")
    def test_scanpipe_nix_fetch_inputs(
        self,
        mock_fetch_path,
        mock_get_patched_source,
        mock_get_download_url,
        mock_get_store_path_with_nix,
        mock_get_package_data,
    ):
        mock_get_package_data.return_value = None
        mock_get_store_path_with_nix.return_value = "/nix/store/aaaaaaaaaa"

        mock_get_download_url.return_value = "https://cache.nixos.org/nar/hello.nar.xz"
        mock_get_patched_source.return_value = nix.PatchedSourceResult(
            path="/path/extracted/from",
            used_fallback=False,
            fallback_reason="",
        )
        mock_fetch_path.return_value = "/path/debug/to"

        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit=1234abcd"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            src_path, bin_path, output_fmt, error_msg, warning_msg = nix.fetch_inputs(
                purl, temp_dir
            )

            self.assertEqual(src_path, "/path/extracted/from")
            self.assertEqual(bin_path, "/path/debug/to")
            self.assertEqual(output_fmt, "debug")
            self.assertEqual(error_msg, "")
            self.assertEqual(warning_msg, "")

            mock_get_store_path_with_nix.assert_called_once()

    @mock.patch("scanpipe.pipes.nix.get_package_data")
    @mock.patch("scanpipe.pipes.nix.get_nix_store_path_with_nix")
    @mock.patch("scanpipe.pipes.nix.get_nix_download_url")
    @mock.patch("scanpipe.pipes.nix.get_patched_source_with_docker")
    @mock.patch("scanpipe.pipes.nix.build_binary_with_docker")
    @mock.patch("scanpipe.pipes.utils.fetch_path")
    def test_scanpipe_nix_fetch_inputs_fallback_build(
        self,
        mock_fetch_path,
        mock_build_binary,
        mock_get_patched_source,
        mock_get_download_url,
        mock_get_store_path_with_nix,
        mock_get_package_data,
    ):
        """Test that fetch_inputs falls back to local build if download fails."""
        mock_get_package_data.return_value = None
        mock_get_store_path_with_nix.return_value = "/nix/store/aaaaaaaaaa"

        # Simulate a missing/failed cache download
        mock_get_download_url.return_value = ""
        mock_fetch_path.return_value = ""

        # Simulate a successful local build and source extraction
        mock_build_binary.return_value = "/path/built/locally/to"
        mock_get_patched_source.return_value = nix.PatchedSourceResult(
            path="/path/extracted/from",
            used_fallback=False,
            fallback_reason="",
        )

        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit=1234abcd"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            src_path, bin_path, output_fmt, error_msg, warning_msg = nix.fetch_inputs(
                purl, temp_dir
            )

            self.assertEqual(src_path, "/path/extracted/from")
            self.assertEqual(bin_path, "/path/built/locally/to")
            self.assertEqual(output_fmt, "debug")
            self.assertEqual(error_msg, "")
            self.assertTrue("Built locally using commit" in warning_msg)

            mock_build_binary.assert_called_once()
            mock_get_store_path_with_nix.assert_called_once()

    @mock.patch("scanpipe.pipes.nix.get_commit_hash_nix_store_path")
    def test_scanpipe_nix_get_nix_store_path_success(
        self, mock_get_commit_hash_nix_store_path
    ):
        mock_get_commit_hash_nix_store_path.return_value = (
            "1234abcd",
            "/nix/store/hello-path",
        )

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

    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_get_patched_source_with_docker_success(
        self, mock_subprocess_run
    ):
        """Test successful fetching and patching of source using Docker."""
        mock_subprocess_run.return_value = mock.Mock(stderr="", returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            from_dir = Path(temp_dir) / "from"
            from_dir.mkdir()
            (from_dir / "somefile").touch()

            result = nix.get_patched_source_with_docker(
                name="hello",
                output_dir=temp_dir,
                system="x86_64-linux",
                commit_hash="1234abcd",
            )

            self.assertEqual(result.path, str(from_dir))
            self.assertFalse(result.used_fallback)
            self.assertEqual(result.fallback_reason, "")
            mock_subprocess_run.assert_called_once()

    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_get_patched_source_with_docker_fallback(
        self, mock_subprocess_run
    ):
        """The fallback line on stderr flips used_fallback and carries the reason."""
        mock_subprocess_run.return_value = mock.Mock(
            stderr=(
                "some nix output\n"
                "PATCHED_SOURCE_FALLBACK_REASON="
                "primary output contained only env-vars\n"
            ),
            returncode=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            from_dir = Path(temp_dir) / "from"
            from_dir.mkdir()
            (from_dir / "somefile").touch()

            result = nix.get_patched_source_with_docker(
                name="hello",
                output_dir=temp_dir,
                system="x86_64-linux",
                commit_hash="1234abcd",
            )

            self.assertEqual(result.path, str(from_dir))
            self.assertTrue(result.used_fallback)
            self.assertEqual(
                result.fallback_reason, "primary output contained only env-vars"
            )

    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_extract_nar_archive_success(self, mock_subprocess_run):
        """Test extracting a .nar archive via Docker."""
        mock_subprocess_run.return_value = mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            # We don't actually need the file to exist for the mocked test
            archive_path = Path(temp_dir) / "hello-bin.nar.xz"

            result = nix.extract_nar_archive(
                archive_path=str(archive_path), output_dir=temp_dir, output="debug"
            )

            expected_extracted_path = str(Path(temp_dir).resolve() / "to" / "debug")
            self.assertEqual(result, expected_extracted_path)

    @mock.patch("scanpipe.pipes.nix.shutil.copy2")
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_extract_nar_archive_stages_from_tmp(
        self, mock_subprocess_run, mock_copy2
    ):
        """Archive outside output_dir is staged into it before docker run."""
        mock_subprocess_run.return_value = mock.Mock(returncode=0)

        with (
            tempfile.TemporaryDirectory() as source_dir,
            tempfile.TemporaryDirectory() as output_dir,
        ):
            archive_path = Path(source_dir) / "hello-bin.nar.xz"

            result = nix.extract_nar_archive(
                archive_path=str(archive_path), output_dir=output_dir, output="debug"
            )

            expected_extracted_path = str(Path(output_dir).resolve() / "to" / "debug")
            self.assertEqual(result, expected_extracted_path)

            # Staging must have happened exactly once
            mock_copy2.assert_called_once()
            src, dst = mock_copy2.call_args[0]
            self.assertEqual(Path(src), Path(source_dir).resolve() / "hello-bin.nar.xz")
            self.assertEqual(Path(dst), Path(output_dir).resolve() / "hello-bin.nar.xz")

            # The docker mount source must be output_dir, not the /tmp source
            cmd = mock_subprocess_run.call_args[0][0]
            volume_mounts = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-v"]
            self.assertTrue(
                any(str(Path(output_dir).resolve()) in v for v in volume_mounts),
                f"expected staged mount in {volume_mounts}",
            )
            self.assertFalse(
                any(str(Path(source_dir).resolve()) in v for v in volume_mounts),
                f"unexpected source mount in {volume_mounts}",
            )

    def test_scanpipe_nix_get_decompress_cmd(self):
        cases = [
            ("foo.nar.xz", "xz", "xzcat /input/foo.nar.xz"),
            ("foo.nar.zst", "zstd", "zstdcat /input/foo.nar.zst"),
            ("foo.nar.bz2", "bzip2", "bzcat /input/foo.nar.bz2"),
            ("foo.nar.gz", "gzip", "zcat /input/foo.nar.gz"),
            ("foo.nar", None, "cat /input/foo.nar"),
        ]
        for name, expected_type, expected_cmd in cases:
            compression_type, cmd = nix._get_decompress_cmd(name)
            self.assertEqual(compression_type, expected_type)
            self.assertEqual(cmd, expected_cmd)

    def test_scanpipe_nix_stage_archive_already_in_output_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir).resolve()
            archive_path = output_dir / "hello-bin.nar.xz"

            with mock.patch("scanpipe.pipes.nix.shutil.copy2") as mock_copy2:
                result = nix._stage_archive(archive_path, output_dir)

            self.assertEqual(result, archive_path)
            mock_copy2.assert_not_called()

    @mock.patch("scanpipe.pipes.nix.shutil.copy2")
    def test_scanpipe_nix_stage_archive_from_elsewhere(self, mock_copy2):
        with (
            tempfile.TemporaryDirectory() as source_dir,
            tempfile.TemporaryDirectory() as output_dir,
        ):
            archive_path = Path(source_dir).resolve() / "hello-bin.nar.xz"
            output_path = Path(output_dir).resolve()

            result = nix._stage_archive(archive_path, output_path)

            self.assertEqual(result, output_path / "hello-bin.nar.xz")
            mock_copy2.assert_called_once_with(
                archive_path, output_path / "hello-bin.nar.xz"
            )

    @mock.patch("scanpipe.pipes.nix.shutil.copy2")
    def test_scanpipe_nix_stage_archive_skips_copy_when_sizes_match(self, mock_copy2):
        with (
            tempfile.TemporaryDirectory() as source_dir,
            tempfile.TemporaryDirectory() as output_dir,
        ):
            archive_path = Path(source_dir).resolve() / "hello-bin.nar.xz"
            archive_path.write_bytes(b"payload")
            target = Path(output_dir).resolve() / "hello-bin.nar.xz"
            target.write_bytes(b"payload")  # same size

            result = nix._stage_archive(archive_path, Path(output_dir).resolve())

            self.assertEqual(result, target)
            mock_copy2.assert_not_called()

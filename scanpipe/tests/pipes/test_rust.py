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


import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

from packageurl import PackageURL

from scanpipe.pipes import rust


class ScanPipeRustPipesTest(TestCase):
    def test_get_cargo_toml_path_found(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            crate_dir = base / "test-1.0.0"
            crate_dir.mkdir()
            cargo_toml = crate_dir / "Cargo.toml"
            cargo_toml.touch()

            purl = PackageURL.from_string("pkg:cargo/test@1.0.0")
            found_path = rust.get_cargo_toml_path(base, purl)
            self.assertEqual(found_path, cargo_toml)

    def test_get_cargo_toml_path_not_found(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            purl = PackageURL.from_string("pkg:cargo/test@1.0.0")
            found_path = rust.get_cargo_toml_path(base, purl)
            self.assertIsNone(found_path)

    @mock.patch("pathlib.Path.exists", return_value=True)
    @mock.patch("pathlib.Path.open", new_callable=mock.mock_open)
    @mock.patch("scanpipe.pipes.rust.tomllib.load")
    def test_get_repository_value_from_cargo_toml_success(
        self, mock_tomllib_load, mock_file_open, mock_exists
    ):
        mock_tomllib_load.return_value = {
            "package": {"repository": "https://github.com/owner/repo"}
        }
        repo_url = rust.get_repository_value_from_cargo_toml("Cargo.toml")
        self.assertEqual(repo_url, "https://github.com/owner/repo")

    @mock.patch("pathlib.Path.exists", return_value=False)
    def test_get_repository_value_from_cargo_toml_missing(self, mock_exists):
        with self.assertRaises(FileNotFoundError):
            rust.get_repository_value_from_cargo_toml("/nonexistent/Cargo.toml")

    def test_check_input_and_return_purl_success(self):
        mock_project = mock.Mock()
        mock_project.inputsources.all.return_value = ["pkg:cargo/test@1.0.0"]

        purl = rust.check_input_and_return_purl(mock_project)
        self.assertEqual(purl.type, "cargo")
        self.assertEqual(purl.name, "test")
        self.assertEqual(purl.version, "1.0.0")

    def test_check_input_and_return_purl_invalid_type(self):
        mock_project = mock.Mock()
        mock_project.inputsources.all.return_value = ["pkg:pypi/test@1.0.0"]

        with self.assertRaises(ValueError):
            rust.check_input_and_return_purl(mock_project)

    def test_check_input_and_return_purl_missing_version(self):
        mock_project = mock.Mock()
        mock_project.inputsources.all.return_value = ["pkg:cargo/test"]

        with self.assertRaises(ValueError):
            rust.check_input_and_return_purl(mock_project)

    @mock.patch("scanpipe.pipes.rust.run_command_safely")
    def test_build_crates_success(self, mock_run_cmd):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            cargo_path = base_path / "Cargo.toml"
            cargo_path.touch()
            other_file = base_path / "src_file.rs"
            other_file.touch()

            # Since run_command_safely is mocked, Cargo won't create the
            # 'to' dir automatically
            (base_path / "to").mkdir()

            success, new_cargo_toml_path, new_devel_dir = rust.build_crates(
                base_path, cargo_path
            )
            self.assertTrue(success)
            self.assertTrue((base_path / "to").exists())
            self.assertTrue((base_path / "from").exists())
            self.assertTrue((base_path / "from" / "src_file.rs").exists())
            self.assertEqual(new_devel_dir, base_path / "from")
            self.assertEqual(new_cargo_toml_path, base_path / "from" / "Cargo.toml")

    @mock.patch("scanpipe.pipes.rust.run_command_safely")
    def test_build_crates_failure(self, mock_run_cmd):
        mock_run_cmd.side_effect = subprocess.SubprocessError("build failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            cargo_path = base_path / "Cargo.toml"
            cargo_path.touch()
            (base_path / "to").mkdir()

            success, returned_cargo_toml, returned_devel_dir = rust.build_crates(
                base_path, cargo_path
            )
            self.assertFalse(success)
            self.assertEqual(returned_cargo_toml, cargo_path)
            self.assertEqual(returned_devel_dir, base_path)

    def test_parse_d_file_valid(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            d_file = Path(tmp_dir) / "test.d"
            d_file.write_text("/codebase/to/release/libtest.rlib: /src/a.rs /src/b.rs")
            rust_lib_path, file_paths = rust.parse_d_file(d_file)
            self.assertEqual(rust_lib_path, "/codebase/to/release/libtest.rlib")
            self.assertEqual(file_paths, ["/src/a.rs", "/src/b.rs"])

    def test_parse_d_file_invalid_no_colon(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            d_file = Path(tmp_dir) / "test.d"
            d_file.write_text("not a valid .d file")
            rust_lib_path, file_paths = rust.parse_d_file(d_file)
            self.assertEqual(rust_lib_path, "")
            self.assertEqual(file_paths, [])

    def test_parse_d_file_missing_file(self):
        rust_lib_path, file_paths = rust.parse_d_file("/nonexistent/file.d")
        self.assertEqual(rust_lib_path, "")
        self.assertEqual(file_paths, [])

    def test_get_rust_file_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            d_file = Path(tmp_dir) / "test.d"
            d_file.write_text("/codebase/lib.rlib: /src/a.rs /src/b.rs")
            rust_lib_path, paths = rust.get_rust_file_paths(d_file)
            self.assertEqual(rust_lib_path, "/codebase/lib.rlib")
            self.assertEqual(paths, {"rust_file_paths": ["/src/a.rs", "/src/b.rs"]})

    def test_get_rust_file_paths_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            d_file = Path(tmp_dir) / "test.d"
            d_file.write_text("")
            rust_lib_path, paths = rust.get_rust_file_paths(d_file)
            self.assertEqual(rust_lib_path, "")
            self.assertEqual(paths, {})

    def test_find_crate_subdirectory_at_root(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo-0.2.0"
            crate_dir = repo / "uselesskey-hmac"
            crate_dir.mkdir(parents=True)
            (crate_dir / "Cargo.toml").touch()

            purl = PackageURL.from_string("pkg:cargo/uselesskey-hmac@0.2.0")
            result = rust.find_crate_subdirectory(repo, purl)
            self.assertEqual(result, crate_dir)

    def test_find_crate_subdirectory_monorepo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo-0.2.0"
            crate_dir = repo / "crates" / "uselesskey-hmac"
            crate_dir.mkdir(parents=True)
            (crate_dir / "Cargo.toml").touch()
            # Workspace manifest
            (repo / "Cargo.toml").touch()

            purl = PackageURL.from_string("pkg:cargo/uselesskey-hmac@0.2.0")
            result = rust.find_crate_subdirectory(repo, purl)
            self.assertEqual(result, crate_dir)

    def test_find_crate_subdirectory_not_found(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo-0.2.0"
            repo.mkdir()
            (repo / "unrelated").mkdir()

            purl = PackageURL.from_string("pkg:cargo/uselesskey-hmac@0.2.0")
            result = rust.find_crate_subdirectory(repo, purl)
            self.assertIsNone(result)

    def test_find_crate_subdirectory_crate_name_with_version(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "repo"
            crate_dir = repo / "uselesskey-hmac-0.2.0"
            crate_dir.mkdir(parents=True)
            (crate_dir / "Cargo.toml").touch()

            purl = PackageURL.from_string("pkg:cargo/uselesskey-hmac@0.2.0")
            result = rust.find_crate_subdirectory(repo, purl)
            self.assertEqual(result, crate_dir)

    @mock.patch("scanpipe.pipes.rust.fetch.fetch_path")
    def test_fetch_inputs_success(self, mock_fetch_path):
        purl = PackageURL.from_string("pkg:cargo/rand@0.7.2")
        mock_fetch_path.return_value = "/safe/rand-0.7.2.crate"

        result = rust.fetch_inputs(purl)

        self.assertEqual(Path("/safe/rand-0.7.2.crate"), result)
        mock_fetch_path.assert_called_once_with("pkg:cargo/rand@0.7.2")

    @mock.patch("scanpipe.pipes.rust.fetch.fetch_path")
    def test_fetch_inputs_fail(self, mock_fetch_path):
        purl = PackageURL.from_string("pkg:cargo/does-not-exist@1.0")
        mock_fetch_path.return_value = None

        with self.assertRaises(ValueError) as err:
            rust.fetch_inputs(purl)

        expected = "No source could be resolved for pkg:cargo/does-not-exist@1.0."
        self.assertEqual(expected, str(err.exception))

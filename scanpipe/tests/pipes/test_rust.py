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

from scanpipe.pipes import rust


class ScanPipeRustPipesTest(TestCase):
    @mock.patch("pathlib.Path.rglob")
    def test_get_cargo_toml_path_found(self, mock_rglob):
        mock_cargo_path = Path("/mock/Cargo.toml")
        mock_rglob.return_value = [mock_cargo_path]

        found_path = rust.get_cargo_toml_path(Path("/mock"))
        self.assertEqual(found_path, mock_cargo_path)
        mock_rglob.assert_called_once_with("Cargo.toml")

    @mock.patch("pathlib.Path.rglob")
    def test_get_cargo_toml_path_not_found(self, mock_rglob):
        mock_rglob.return_value = []

        found_path = rust.get_cargo_toml_path(Path("/mock"))
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

            success = rust.build_crates(base_path, cargo_path)
            self.assertTrue(success)
            self.assertTrue((base_path / "to").exists())
            self.assertTrue((base_path / "from").exists())
            self.assertTrue((base_path / "from" / "src_file.rs").exists())

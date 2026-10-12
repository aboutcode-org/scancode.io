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
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import hashlib
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe.pipes import utils


class ScanPipeUtilsTest(TestCase):
    @mock.patch("scanpipe.pipes.utils.shutil.which", return_value=None)
    def test_check_docker_command_no_docker_executable(self, mock_which):
        self.assertFalse(utils.check_docker_command())

    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    @mock.patch("scanpipe.pipes.utils.shutil.which", return_value="/usr/bin/docker")
    def test_check_docker_command_daemon_running(self, mock_which, mock_run):
        mock_run.return_value = mock.Mock(returncode=0)
        self.assertTrue(utils.check_docker_command())

    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    @mock.patch("scanpipe.pipes.utils.shutil.which", return_value="/usr/bin/docker")
    def test_check_docker_command_daemon_not_running(self, mock_which, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.SubprocessError("daemon not running")
        self.assertFalse(utils.check_docker_command())

    def _write(self, base, rel_path, content):
        path = Path(base) / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_get_all_files_and_count(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._write(tmp_dir, "file1.txt", b"hello")
            self._write(tmp_dir, "tmp/file2.txt", b"world")

            self.assertEqual(utils.count_total_files(tmp_dir), 2)

            file_map = utils.get_all_files(tmp_dir)
            self.assertIn("file1.txt", file_map)
            self.assertIn("tmp/file2.txt", file_map)
            self.assertEqual(file_map["file1.txt"]["name"], "file1.txt")
            self.assertIsNotNone(file_map["file1.txt"]["hash"])

    def test_get_all_files_from_resources_strips_prefix_and_uses_db_sha1(self):
        resource_1 = mock.Mock(path="from/rand-0.7.2/src/lib.rs", sha1="aaa111")
        resource_2 = mock.Mock(path="from/rand-0.7.2/Cargo.toml", sha1="bbb222")

        file_map = utils.get_all_files_from_resources(
            [resource_1, resource_2],
            base_path_prefix="from/",
        )

        self.assertEqual(
            file_map,
            {
                "rand-0.7.2/src/lib.rs": {"name": "lib.rs", "hash": "aaa111"},
                "rand-0.7.2/Cargo.toml": {"name": "Cargo.toml", "hash": "bbb222"},
            },
        )

    def test_consolidate_unmatched(self):
        all_files = ["src/main.py", "src/utils.py", "docs/readme.md", "docs/install.md"]
        unmatched_files = ["docs/readme.md", "docs/install.md", "src/utils.py"]

        result = utils.consolidate_unmatched(all_files, unmatched_files)

        # 'docs' directory is entirely unmatched.
        # 'src/utils.py' is unmatched, but 'src' has a matched file ('main.py').
        expected = [("docs", True), ("src/utils.py", False)]
        self.assertEqual(result, sorted(expected))

    def test_compare_directories_accepts_prebuilt_input_files_map(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            self._write(repo_dir, "a.txt", b"hello")
            self._write(repo_dir, "sub/b.txt", b"world")

            repo_hash_a = hashlib.sha1(b"hello", usedforsecurity=False).hexdigest()
            repo_hash_b = hashlib.sha1(b"world", usedforsecurity=False).hexdigest()

            input_files = {
                "a.txt": {"name": "a.txt", "hash": repo_hash_a},
                "sub/b.txt": {"name": "b.txt", "hash": repo_hash_b},
            }

            matched_count, mismatches = utils.compare_directories(input_files, repo_dir)

        self.assertEqual(matched_count, 2)
        self.assertEqual(mismatches["mismatches"], [])
        self.assertEqual(mismatches["input_source_only"], [])
        self.assertEqual(mismatches["source_repo_only"], [])

    def test_compare_directories_reports_content_mismatch(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            self._write(repo_dir, "a.txt", b"different")

            input_files = {
                "a.txt": {
                    "name": "a.txt",
                    "hash": hashlib.sha1(b"hello", usedforsecurity=False).hexdigest(),
                },
            }

            matched_count, mismatches = utils.compare_directories(input_files, repo_dir)

        self.assertEqual(matched_count, 0)
        self.assertEqual(mismatches["mismatches"], ["[File] a.txt"])

    def test_compare_directories_reports_input_only(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            input_files = {
                "only_in_input.txt": {
                    "name": "only_in_input.txt",
                    "hash": hashlib.sha1(b"x", usedforsecurity=False).hexdigest(),
                },
            }
            matched_count, mismatches = utils.compare_directories(input_files, repo_dir)

        self.assertEqual(matched_count, 0)
        self.assertIn("[File] only_in_input.txt", mismatches["input_source_only"])

    def test_compare_directories_reports_repo_only(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            self._write(repo_dir, "only_in_repo.txt", b"hello")

            matched_count, mismatches = utils.compare_directories({}, repo_dir)

        self.assertEqual(matched_count, 0)
        self.assertIn("[File] only_in_repo.txt", mismatches["source_repo_only"])

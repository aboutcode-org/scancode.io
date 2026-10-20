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

import fcntl
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe.pipes import utils


class ScanPipeUtilsTest(TestCase):
    @mock.patch("scanpipe.pipes.utils.shutil.which")
    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_scanpipe_utils_check_docker_command_success(
        self, mock_subprocess_run, mock_shutil_which
    ):
        mock_shutil_which.return_value = "/usr/bin/docker"
        mock_subprocess_run.return_value = mock.Mock(returncode=0)

        self.assertTrue(utils.check_docker_command())

    @mock.patch("scanpipe.pipes.utils.shutil.which")
    def test_scanpipe_utils_check_docker_command_not_found(self, mock_shutil_which):
        mock_shutil_which.return_value = None
        self.assertFalse(utils.check_docker_command())

    @mock.patch("scanpipe.pipes.utils.shutil.which")
    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_scanpipe_utils_check_docker_command_exception(
        self, mock_subprocess_run, mock_shutil_which
    ):
        mock_shutil_which.return_value = "/usr/bin/docker"
        mock_subprocess_run.side_effect = subprocess.SubprocessError

        self.assertFalse(utils.check_docker_command())

    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_scanpipe_utils_docker_image_exists(self, mock_subprocess_run):
        mock_subprocess_run.return_value = mock.Mock(returncode=0)
        self.assertTrue(utils.docker_image_exists("scancode:test"))

        mock_subprocess_run.return_value = mock.Mock(returncode=1)
        self.assertFalse(utils.docker_image_exists("scancode:test"))

    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_scanpipe_utils_docker_rm_force(self, mock_subprocess_run):
        utils.docker_rm_force("test-container")
        mock_subprocess_run.assert_called_once_with(
            ["docker", "rm", "-f", "test-container"],
            capture_output=True,
            check=False,
        )

    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_scanpipe_utils_run_docker_container_success(self, mock_subprocess_run):
        mock_subprocess_run.return_value = mock.Mock(
            returncode=0, stdout="stdout_data", stderr="stderr_data"
        )

        result = utils.run_docker_container(
            ["docker", "run", "img"], "test-container", 100, "Testing container"
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "stdout_data")

    @mock.patch("scanpipe.pipes.utils.docker_rm_force")
    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_scanpipe_utils_run_docker_container_failure(
        self, mock_subprocess_run, mock_docker_rm_force
    ):
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "run", "img"],
            stderr="standard error message",
        )

        with self.assertRaises(subprocess.CalledProcessError) as cm:
            utils.run_docker_container(
                ["docker", "run", "img"],
                "test-container",
                100,
                "Testing container",
            )

        self.assertEqual(cm.exception.stderr, "standard error message")
        mock_docker_rm_force.assert_called_once_with("test-container")

    @mock.patch("scanpipe.pipes.utils.docker_rm_force")
    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_scanpipe_utils_run_docker_container_timeout(
        self, mock_subprocess_run, mock_docker_rm_force
    ):
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired("cmd", 15)

        with self.assertRaises(subprocess.TimeoutExpired):
            utils.run_docker_container(
                ["docker", "run", "img"],
                "test-container",
                100,
                "Testing container",
            )

        mock_docker_rm_force.assert_called_once_with("test-container")

    @mock.patch("scanpipe.pipes.utils.fcntl.flock")
    def test_scanpipe_utils_file_lock(self, mock_flock):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            with utils.file_lock(lock_path):
                self.assertTrue(lock_path.exists())

                # Verify an exclusive lock (LOCK_EX) was acquired
                mock_flock.assert_called_once_with(mock.ANY, fcntl.LOCK_EX)

                # Reset the mock to cleanly track the release step
                mock_flock.reset_mock()

            # Verify the lock was released (LOCK_UN) after the 'with' block exits
            mock_flock.assert_called_once_with(mock.ANY, fcntl.LOCK_UN)

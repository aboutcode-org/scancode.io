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

import os
import subprocess
from unittest import mock

from django.test import TestCase

from scanpipe.pipes import container


class ScanPipeContainerTest(TestCase):
    @mock.patch("scanpipe.pipes.container.shutil.which")
    @mock.patch("scanpipe.pipes.container.subprocess.run")
    def test_scanpipe_container_check_docker_command_success(
        self, mock_subprocess_run, mock_shutil_which
    ):
        mock_shutil_which.return_value = "/usr/bin/docker"
        mock_subprocess_run.return_value = mock.Mock(returncode=0)

        self.assertTrue(container.check_docker_command())

    @mock.patch("scanpipe.pipes.container.shutil.which")
    def test_scanpipe_container_check_docker_command_not_found(self, mock_shutil_which):
        mock_shutil_which.return_value = None
        self.assertFalse(container.check_docker_command())

    @mock.patch("scanpipe.pipes.container.shutil.which")
    @mock.patch("scanpipe.pipes.container.subprocess.run")
    def test_scanpipe_container_check_docker_command_exception(
        self, mock_subprocess_run, mock_shutil_which
    ):
        mock_shutil_which.return_value = "/usr/bin/docker"
        mock_subprocess_run.side_effect = subprocess.SubprocessError

        self.assertFalse(container.check_docker_command())

    @mock.patch("scanpipe.pipes.container.subprocess.run")
    def test_scanpipe_container_docker_image_exists(self, mock_subprocess_run):
        mock_subprocess_run.return_value = mock.Mock(returncode=0)
        self.assertTrue(container.docker_image_exists("scancode:test"))

        mock_subprocess_run.return_value = mock.Mock(returncode=1)
        self.assertFalse(container.docker_image_exists("scancode:test"))

    @mock.patch("scanpipe.pipes.container.subprocess.run")
    def test_scanpipe_container_docker_rm_force(self, mock_subprocess_run):
        container.docker_rm_force("test-container")
        mock_subprocess_run.assert_called_once_with(
            ["docker", "rm", "-f", "test-container"],
            capture_output=True,
            check=False,
            timeout=60,
        )

    @mock.patch("scanpipe.pipes.container.subprocess.run")
    def test_scanpipe_container_run_docker_container_success(self, mock_subprocess_run):
        mock_subprocess_run.return_value = mock.Mock(
            returncode=0, stdout="stdout_data", stderr="stderr_data"
        )

        result = container.run_docker_container(
            ["docker", "run", "img"], "test-container", 100, "Testing container"
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "stdout_data")

    @mock.patch("scanpipe.pipes.container.docker_rm_force")
    @mock.patch("scanpipe.pipes.container.subprocess.run")
    def test_scanpipe_container_run_docker_container_failure(
        self, mock_subprocess_run, mock_docker_rm_force
    ):
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "run", "img"],
            stderr="standard error message",
        )

        with self.assertRaises(subprocess.CalledProcessError) as cm:
            container.run_docker_container(
                ["docker", "run", "img"],
                "test-container",
                100,
                "Testing container",
            )

        self.assertEqual(cm.exception.stderr, "standard error message")
        mock_docker_rm_force.assert_called_once_with("test-container")

    @mock.patch("scanpipe.pipes.container.docker_rm_force")
    @mock.patch("scanpipe.pipes.container.subprocess.run")
    def test_scanpipe_container_run_docker_container_timeout(
        self, mock_subprocess_run, mock_docker_rm_force
    ):
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired("cmd", 15)

        with self.assertRaises(subprocess.TimeoutExpired):
            container.run_docker_container(
                ["docker", "run", "img"],
                "test-container",
                100,
                "Testing container",
            )

        mock_docker_rm_force.assert_called_once_with("test-container")

    @mock.patch.dict(os.environ, {"DOCKER_HOST": ""})
    @mock.patch("scanpipe.pipes.container.Path")
    def test_scanpipe_container_has_docker_endpoint_local_socket(self, mock_path):
        mock_path.return_value.exists.return_value = True
        self.assertTrue(container.has_docker_endpoint())

    @mock.patch.dict(os.environ, {"DOCKER_HOST": ""})
    @mock.patch("scanpipe.pipes.container.Path")
    def test_scanpipe_container_has_docker_endpoint_none(self, mock_path):
        mock_path.return_value.exists.return_value = False
        self.assertFalse(container.has_docker_endpoint())

    @mock.patch.dict(os.environ, {"DOCKER_HOST": "tcp://localhost:2375"})
    def test_scanpipe_container_has_docker_endpoint_docker_host(self):
        self.assertTrue(container.has_docker_endpoint())

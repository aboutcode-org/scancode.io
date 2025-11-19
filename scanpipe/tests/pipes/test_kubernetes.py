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

from pathlib import Path
from subprocess import SubprocessError
from unittest import mock

from django.test import TestCase

from scanpipe.pipes import kubernetes


class ScanPipeKubernetesPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    @mock.patch("scanpipe.pipes.kubernetes.run_command_safely")
    def test_scanpipe_pipes_kubernetes_get_images_from_kubect(
        self, mock_run_command_safely
    ):
        mock_run_command_safely.side_effect = FileNotFoundError
        with self.assertRaises(FileNotFoundError) as cm:
            kubernetes.get_images_from_kubectl()
        expected = (
            "kubectl not found. Please ensure kubectl is installed and in your PATH."
        )
        self.assertEqual(expected, str(cm.exception))

        mock_run_command_safely.side_effect = SubprocessError
        with self.assertRaises(RuntimeError) as cm:
            kubernetes.get_images_from_kubectl()
        expected = "Failed to execute kubectl command: "
        self.assertEqual(expected, str(cm.exception))

        mock_run_command_safely.side_effect = None
        mock_run_command_safely.return_value = "nginx:latest redis:alpine redis:alpine"
        expected = ["nginx:latest", "redis:alpine"]
        self.assertEqual(expected, kubernetes.get_images_from_kubectl())

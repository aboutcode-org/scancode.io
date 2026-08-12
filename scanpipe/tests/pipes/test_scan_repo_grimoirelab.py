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

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from django.test import TestCase

from scanpipe.pipelines.scan_repo_grimoirelab import ScanRepoGrimoirelab
from scanpipe.pipelines.scan_repo_grimoirelab import is_valid_vcs_url


class ScanRepoGrimoirelabTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "grimorielab"

    def setUp(self):
        mock_run = MagicMock()
        self.pipeline = ScanRepoGrimoirelab(mock_run)
        self.pipeline.project = MagicMock()
        self.pipeline.project.input_sources = [
            {"download_url": "https://github.com/example/repo.git"}
        ]
        self.pipeline.project.get_output_file_path.return_value = "metrics.json"
        self.pipeline.log = MagicMock()

    @patch("scanpipe.pipelines.scan_repo_grimoirelab.run_command_safely")
    def test_collect_and_store_grimoire_metric_called_process_error(
        self, mock_run_command
    ):
        """Test handling of a non-zero exit code (CalledProcessError)."""
        mock_run_command.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["grimoirelab-metrics"]
        )

        expected_msg = "Grimoirelab-metrics pipeline failed"

        self.pipeline.get_repo_url_input()
        with self.assertRaisesMessage(RuntimeError, expected_msg):
            self.pipeline.collect_and_store_grimoire_metric()

    def test_invalid_input_sources(self):
        """Test handling of invalid number of input sources."""
        self.pipeline.project.input_sources = []

        expected_msg = "Expected exactly one input source"
        with self.assertRaisesMessage(ValueError, expected_msg):
            self.pipeline.get_repo_url_input()

        self.pipeline.project.input_sources = [
            {"download_url": "https://github.com/example/repo1.git"},
            {"download_url": "https://github.com/example/repo2.git"},
        ]

        expected_msg = "Expected exactly one input source"
        with self.assertRaisesMessage(ValueError, expected_msg):
            self.pipeline.get_repo_url_input()

    def test_format_metrics_output(self):
        """Test formatting the GrimoireLab metrics output using fixture files."""
        temp_dir = tempfile.mkdtemp()

        input_file = self.data / "metrics.json"
        expected_file = self.data / "expected-metrics.json"

        temp_metrics_path = Path(temp_dir) / "metrics.json"
        temp_metrics_path.write_text(input_file.read_text())

        self.pipeline.metrics_output_path = temp_metrics_path
        self.pipeline.format_metrics_output()

        with open(temp_metrics_path) as f:
            result = json.load(f)

        with open(expected_file) as f:
            expected_result = json.load(f)

        self.assertEqual(expected_result, result)
        shutil.rmtree(temp_dir)

    def test_is_valid_vcs_url(self):
        """Test VCS repository URL validation."""
        test_cases = [
            # Valid URLs
            ("https://github.com/example/repo.git", True),
            ("git://github.com/example/repo.git", True),
            # Invalid URLs
            ("user@localhost:path/to/repo.git", False),
            ("hg@bitbucket.org:owner/repo", False),
            ("https://github.com/repo.git; rm -rf /", False),
            ("https://github.com/repo.git | ls -la", False),
            ("https://github.com/repo.git & whoami", False),
            ("git@github.com:repo.git\nrm -rf /", False),
            ("https://github.com/ repo.git", False),
            (" https://github.com/repo.git", False),
            ("https://", False),
            ("https:///repo.git", False),
            ("https://?foo=bar", False),
            ("", False),
            (None, False),
        ]

        for url, expected in test_cases:
            with self.subTest(url=url):
                self.assertEqual(is_valid_vcs_url(url), expected)

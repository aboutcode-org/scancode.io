import subprocess
from unittest.mock import MagicMock
from unittest.mock import patch

from django.test import TestCase

from scanpipe.pipelines.scan_repo_grimoirelab import ScanRepoGrimoirelab


class ScanRepoGrimoirelabTest(TestCase):
    def setUp(self):
        mock_run = MagicMock()
        self.pipeline = ScanRepoGrimoirelab(mock_run)

        self.pipeline.project = MagicMock()
        self.pipeline.project.input_sources = [
            {"download_url": "https://github.com/example/repo.git"}
        ]
        self.pipeline.project.get_output_file_path.return_value = (
            "/tmp/project/metrics.json"
        )
        self.pipeline.log = MagicMock()

    @patch("scanpipe.pipelines.scan_repo_grimoirelab.run_command_safely")
    def test_collect_and_store_grimoire_metric_called_process_error(
        self, mock_run_command
    ):
        """Test handling of a non-zero exit code (CalledProcessError)."""
        mock_run_command.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["grimoirelab-metrics"]
        )

        expected_msg = "grimoirelab-metrics pipeline failed 1 for https://github.com/example/repo.git"
        with self.assertRaisesMessage(RuntimeError, expected_msg):
            self.pipeline.collect_and_store_grimoire_metric()

    @patch("scanpipe.pipelines.scan_repo_grimoirelab.run_command_safely")
    def test_collect_and_store_grimoire_metric_timeout(self, mock_run_command):
        """Test handling of a command execution timeout."""
        mock_run_command.side_effect = subprocess.TimeoutExpired(
            cmd=["grimoirelab-metrics"], timeout=300
        )

        expected_msg = "grimoirelab-metrics pipeline timed out"
        with self.assertRaisesMessage(RuntimeError, expected_msg):
            self.pipeline.collect_and_store_grimoire_metric()

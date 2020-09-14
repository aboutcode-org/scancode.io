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
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

from celery.exceptions import SoftTimeLimitExceeded
from scancode_config import __version__ as scancode_version

from scanner.models import Scan
from scanner.tasks import download
from scanner.tasks import download_and_scan
from scanner.tasks import dump_key_files_data
from scanner.tasks import get_scan_input_location
from scanner.tasks import get_scancode_compatible_content
from scanner.tasks import run_scancode
from scanner.tasks import scan_task


class TasksTest(TestCase):
    data_location = Path(__file__).parent / "data"

    def _prepare_file_for_scanning(self, filename):
        """
        Copy the `filename` file from the test data directory to a temp
        directory for processing.
        Return the temp directory.
        """
        input_file = self.data_location / filename
        scan_location = tempfile.mkdtemp()
        shutil.copyfile(input_file, Path(scan_location, filename))
        return scan_location

    @mock.patch("requests.get")
    def test_task_download(self, mock_get):
        url = "https://example.com/filename.zip"
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=url
        )
        downloaded_file = download(url)
        self.assertTrue(Path(downloaded_file.directory, "filename.zip").exists())

        redirect_url = "https://example.com/redirect.zip"
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=redirect_url
        )
        downloaded_file = download(url)
        self.assertTrue(Path(downloaded_file.directory, "redirect.zip").exists())

        headers = {
            "content-disposition": 'attachment; filename="another_name.zip"',
        }
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers=headers, status_code=200, url=url
        )
        downloaded_file = download(url)
        self.assertTrue(Path(downloaded_file.directory, "another_name.zip").exists())

    def test_task_download_and_scan_with_fake_uri(self):
        scan1 = Scan.objects.create(uri="http://thisdoesnotexists.com")
        download_and_scan(scan1.pk)
        scan1.refresh_from_db()
        expected = "HTTPConnectionPool(host='thisdoesnotexists.com', port=80)"
        self.assertIn(expected, scan1.task_output)

    def test_task_download_and_scan_with_non_valid_uri(self):
        scan1 = Scan.objects.create(uri="thisisnotaproperuri")
        download_and_scan(scan1.pk)
        scan1.refresh_from_db()
        expected = (
            "Invalid URL 'thisisnotaproperuri': No schema supplied. "
            "Perhaps you meant http://thisisnotaproperuri?"
        )
        self.assertIn(expected, scan1.task_output)

    @mock.patch("requests.get")
    def test_download_and_scan_with_404_uri(self, mock_get):
        mock_get.return_value = mock.Mock(status_code=404)
        scan1 = Scan.objects.create(uri="http://www.nexb.com/not_existing.jar")
        download_and_scan(scan1.pk)
        scan1.refresh_from_db()
        self.assertEqual("Not found", scan1.task_output)

    @mock.patch("requests.get")
    def test_download_and_scan_proper(self, mock_get):
        url = "https://localhost/filename.zip"
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=url
        )
        scan1 = Scan.objects.create(uri=url)
        download_and_scan(scan1.pk)
        scan1.refresh_from_db()
        self.assertEqual(36, len(str(scan1.task_id)))
        self.assertEqual(0, scan1.task_exitcode)
        self.assertIn("Extracting archives...", scan1.task_output)
        self.assertIn("Extracting done.", scan1.task_output)
        self.assertIn("Scanning done.", scan1.task_output)
        self.assertTrue(scan1.task_start_date)
        self.assertTrue(scan1.task_end_date)
        self.assertEqual(scancode_version, scan1.scancode_version)
        self.assertEqual("filename.zip", scan1.filename)
        self.assertEqual("5ba93c9db0cff93f52b521d7420e43f6eda2784f", scan1.sha1)
        self.assertEqual("93b885adfe0da089cdf634904fd59f71", scan1.md5)
        self.assertEqual(1, scan1.size)

        summary_expected_keys = [
            "authors",
            "holders",
            "packages",
            "key_files",
            "copyrights",
            "license_matches",
            "license_expressions",
            "programming_language",
            "license_clarity_score",
        ]
        self.assertEqual(summary_expected_keys, list(scan1.summary.keys()))

    def test_run_scancode_with_extract_failure(self):
        file_extract_issues = Path(__file__).parent / "data" / "tar-2.2.1.tgz"
        download_location = tempfile.mkdtemp()
        shutil.copyfile(file_extract_issues, Path(download_location) / "tar-2.2.1.tgz")

        output_location = str(Path(download_location, "output.json"))
        exitcode, output = run_scancode(download_location, output_location)

        self.assertEqual(1, exitcode)
        self.assertIn("ERROR extracting", output)
        self.assertIn("Scanning done.", output)
        self.assertIn("Errors count:   0", output)

    def test_get_scan_input_location(self):
        self.assertFalse(get_scan_input_location("/does/not/exist/"))

        empty_location = tempfile.mkdtemp()
        self.assertFalse(list(Path(empty_location).iterdir()))
        self.assertFalse(get_scan_input_location(empty_location))

        one_file = tempfile.mkdtemp()
        tempfile.mkstemp(dir=one_file)
        self.assertEqual(1, len(list(Path(one_file).iterdir())))
        self.assertEqual(one_file, get_scan_input_location(one_file))

        two_files = tempfile.mkdtemp()
        tempfile.mkstemp(dir=two_files)
        tempfile.mkstemp(dir=two_files)
        self.assertEqual(2, len(list(Path(two_files).iterdir())))
        self.assertFalse(get_scan_input_location(two_files))

        file_plus_extract = tempfile.mkdtemp()
        tempfile.mkstemp(dir=file_plus_extract)
        extract_dir = tempfile.mkdtemp(dir=file_plus_extract, suffix="-extract")
        self.assertEqual(2, len(list(Path(file_plus_extract).iterdir())))
        self.assertEqual(extract_dir, str(get_scan_input_location(file_plus_extract)))

        file_plus_two_extract = tempfile.mkdtemp()
        tempfile.mkstemp(dir=file_plus_two_extract)
        tempfile.mkdtemp(dir=file_plus_two_extract, suffix="-extract")
        tempfile.mkdtemp(dir=file_plus_two_extract, suffix="-extract")
        self.assertEqual(3, len(list(Path(file_plus_two_extract).iterdir())))
        self.assertFalse(get_scan_input_location(file_plus_two_extract))

    def test_dump_key_files_data(self):
        output_location = tempfile.mkstemp()[1]

        key_files = []
        source_directory = ""
        dump_key_files_data(key_files, source_directory, output_location)
        with open(output_location) as f:
            self.assertEqual("", f.read())

        source_directory = str(self.data_location)
        key_files = [
            {
                "path": "key_file",
            }
        ]
        dump_key_files_data(key_files, source_directory, output_location)
        expected = '[{"path": "key_file", "content": "content"}]'
        with open(output_location) as f:
            self.assertEqual(expected, f.read())

    def test_dump_key_files_data_with_encoding_issues(self):
        output_location = tempfile.mkstemp()[1]

        source_directory = str(self.data_location)
        key_files = [
            {
                "path": "encoding/hnb-0.2.tar.gz.README",
            }
        ]
        dump_key_files_data(key_files, source_directory, output_location)

        with open(output_location) as f:
            content = f.read()
        self.assertIn('"path": "encoding/hnb-0.2.tar.gz.README"', content)

    @mock.patch("scanner.tasks.run_scancode")
    def test_scan_task_timeout_soft_time_limit_exceeded(self, mock_run_scancode):
        scan_location = self._prepare_file_for_scanning("tar-2.2.1.tgz")

        scan1 = Scan.objects.create(uri="filename.zip")
        mock_run_scancode.side_effect = SoftTimeLimitExceeded()

        scan_task(scan1.pk, scan_location, run_subscriptions=False)
        scan1.refresh_from_db()
        self.assertEqual(4, scan1.task_exitcode)
        self.assertEqual("SoftTimeLimitExceeded", scan1.task_output)

    def test_scanner_tasks_get_scancode_compatible_content(self):
        input_location = str(self.data_location / "encoding" / "null_chars.txt")

        content = get_scancode_compatible_content(input_location)
        self.assertNotIn("\x00", content)
        self.assertTrue(content.strip().endswith("BEFORE the"))


class ScanCodeOutputDataTest(TestCase):
    data_location = Path(__file__).parent / "data"
    reference_scan_path = data_location / "reference_scan"
    maxDiff = None

    def without_keys(self, input, exclude_keys):
        """
        Returns the input excluding the provided `exclude_keys`.
        """
        if type(input) == list:
            return [self.without_keys(entry, exclude_keys) for entry in input]

        if type(input) == dict:
            return {
                key: self.without_keys(value, exclude_keys)
                if type(value) in [list, dict]
                else value
                for key, value in input.items()
                if key not in exclude_keys
            }

        return input

    @mock.patch("scanner.tasks.get_scan_input_location")
    def test_run_scancode_output_validation_against_reference_data(
        self, mock_scan_input_location
    ):
        download_location = tempfile.mkdtemp()
        shutil.copytree(
            self.reference_scan_path, Path(download_location) / "reference_scan"
        )
        mock_scan_input_location.return_value = (
            Path(download_location) / "reference_scan" / "code"
        )

        output_location = str(Path(download_location, "output.json"))
        exitcode, output = run_scancode(download_location, output_location)
        self.assertEqual(0, exitcode)
        self.assertIn(
            "Initial counts: 15 resource(s): 10 file(s) and 5 directorie(s)", output
        )

        reference_file = self.reference_scan_path / "reference.json"
        with open(reference_file) as f:
            reference_data = json.loads(f.read())

        with open(output_location) as f:
            output_data = json.loads(f.read())

        # Un-comment to regen the reference input
        # with open(reference_file, 'w') as f:
        #     f.write(json.dumps(output_data, indent=2))

        exclude_keys = [
            "date",
            "start_timestamp",
            "end_timestamp",
            "duration",
            "input",
            "--json-pp",
            "file_type",
            "mime_type",
            "tool_version",
        ]
        reference_data = self.without_keys(reference_data, exclude_keys)
        output_data = self.without_keys(output_data, exclude_keys)

        self.assertEqual(reference_data, output_data)

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
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from scanpipe.models import InputSource
from scanpipe.pipes.input import add_input_from_upload
from scanpipe.pipes.input import add_input_from_url
from scancodeio.settings import download_store
from scanpipe.tests import make_project


class TestInput(TestCase):
    def setUp(self):
        self.project = make_project()
        self.test_filename = "sample.tar.gz"
        self.test_data_path = (
            Path(__file__).parent / "data" / "test-downloads" / self.test_filename
        )
        with open(self.test_data_path, "rb") as f:
            self.test_content = f.read()

    @patch("requests.get")
    def test_add_input_from_url_with_archiving(self):
        with patch("scanpipe.settings.ENABLE_DOWNLOAD_ARCHIVING", "always"):
            test_url = "https://files.pythonhosted.org/packages/sample.tar.gz"
            mock_get = self.mocker.patch("requests.get")
            mock_get.return_value.content = self.test_content
            mock_get.return_value.status_code = 200
            add_input_from_url(self.project, test_url, filename=self.test_filename)
            input_source = InputSource.objects.get(project=self.project)
            self.assertEqual(input_source.filename, self.test_filename)
            self.assertEqual(input_source.download_url, test_url)
            self.assertTrue(input_source.sha256)
            self.assertTrue(input_source.download_date)
            self.assertFalse(input_source.is_uploaded)
            if download_store:
                download = download_store.get(input_source.sha256)
                self.assertEqual(download.download_url, test_url)

    @patch("requests.get")
    def test_add_input_from_url_without_archiving(self):
        with patch("scanpipe.settings.ENABLE_DOWNLOAD_ARCHIVING", False):
            test_url = "https://files.pythonhosted.org/packages/sample.tar.gz"
            mock_get = self.mocker.patch("requests.get")
            mock_get.return_value.content = self.test_content
            mock_get.return_value.status_code = 200
            add_input_from_url(self.project, test_url, filename=self.test_filename)
            input_source = InputSource.objects.get(project=self.project)
            self.assertEqual(input_source.filename, self.test_filename)
            self.assertEqual(input_source.download_url, test_url)
            self.assertFalse(input_source.sha256)
            self.assertFalse(input_source.download_date)
            self.assertFalse(input_source.is_uploaded)
            input_path = self.project.input_path / self.test_filename
            self.assertTrue(input_path.exists())

    def test_add_input_from_upload_with_archiving(self):
        with patch("scanpipe.settings.ENABLE_DOWNLOAD_ARCHIVING", "always"):
            uploaded_file = SimpleUploadedFile(self.test_filename, self.test_content)
            add_input_from_upload(self.project, uploaded_file)
            input_source = InputSource.objects.get(project=self.project)
            self.assertEqual(input_source.filename, self.test_filename)
            self.assertEqual(input_source.download_url, "")
            self.assertTrue(input_source.sha256)
            self.assertTrue(input_source.download_date)
            self.assertTrue(input_source.is_uploaded)
            if download_store:
                download = download_store.get(input_source.sha256)
                self.assertEqual(download.filename, self.test_filename)

    def test_add_input_from_upload_without_archiving(self):
        with patch("scanpipe.settings.ENABLE_DOWNLOAD_ARCHIVING", False):
            uploaded_file = SimpleUploadedFile(self.test_filename, self.test_content)
            add_input_from_upload(self.project, uploaded_file)
            input_source = InputSource.objects.get(project=self.project)
            self.assertEqual(input_source.filename, self.test_filename)
            self.assertEqual(input_source.download_url, "")
            self.assertFalse(input_source.sha256)
            self.assertFalse(input_source.download_date)
            self.assertTrue(input_source.is_uploaded)
            input_path = self.project.input_path / self.test_filename
            self.assertTrue(input_path.exists())

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
from pathlib import Path

from django.test import TestCase

from scanpipe.archiving import LocalFilesystemProvider
from scanpipe.tests import make_project


class TestArchiving(TestCase):
    def setUp(self):
        self.project = make_project()
        self.root_path = Path(__file__).parent / "data" / "test_downloads"
        self.store = LocalFilesystemProvider(root_path=self.root_path)
        self.test_content = b"test content"
        self.test_url = "https://files.pythonhosted.org/packages/sample.tar.gz"
        self.test_filename = "sample.tar.gz"

    def tearDown(self):
        if self.root_path.exists():
            import shutil

            shutil.rmtree(self.root_path)

    def test_local_filesystem_provider_put_get(self):
        download = self.store.put(
            content=self.test_content,
            download_url=self.test_url,
            download_date="2025-08-21T09:00:00",
            filename=self.test_filename,
        )
        sha256 = hashlib.sha256(self.test_content).hexdigest()
        self.assertEqual(download.sha256, sha256)
        self.assertEqual(download.download_url, self.test_url)
        self.assertEqual(download.filename, self.test_filename)
        self.assertEqual(download.download_date, "2025-08-21T09:00:00")
        content_path = (
            self.root_path / sha256[:2] / sha256[2:4] / sha256[4:] / "content"
        )
        self.assertTrue(content_path.exists())
        with open(content_path, "rb") as f:
            self.assertEqual(f.read(), self.test_content)

        retrieved = self.store.get(sha256)
        self.assertEqual(retrieved.sha256, sha256)
        self.assertEqual(retrieved.download_url, self.test_url)
        self.assertEqual(retrieved.filename, self.test_filename)

    def test_local_filesystem_provider_deduplication(self):
        download1 = self.store.put(
            content=self.test_content,
            download_url=self.test_url,
            download_date="2025-08-21T09:00:00",
            filename=self.test_filename,
        )
        download2 = self.store.put(
            content=self.test_content,
            download_url="https://files.pythonhosted.org/packages/another.tar.gz",
            download_date="2025-08-21T10:00:00",
            filename="another.tar.gz",
        )
        self.assertEqual(download1.sha256, download2.sha256)
        self.assertEqual(download1.download_url, self.test_url)

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

from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe.pipes import fetch


class ScanPipeFetchPipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    @mock.patch("requests.get")
    def test_scanpipe_pipes_fetch_http(self, mock_get):
        url = "https://example.com/filename.zip"

        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=url
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "filename.zip").exists())

        redirect_url = "https://example.com/redirect.zip"
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=redirect_url
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "redirect.zip").exists())

        headers = {
            "content-disposition": 'attachment; filename="another_name.zip"',
        }
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers=headers, status_code=200, url=url
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "another_name.zip").exists())

    @mock.patch("scanpipe.pipes.fetch.get_docker_image_platform")
    @mock.patch("scanpipe.pipes.fetch._get_skopeo_location")
    @mock.patch("scanpipe.pipes.run_command")
    def test_scanpipe_pipes_fetch_docker_image(
        self, mock_run_command, mock_skopeo, mock_platform
    ):
        url = "docker://debian:10.9"

        mock_platform.return_value = "linux", "amd64", ""
        mock_skopeo.return_value = "skopeo"
        mock_run_command.return_value = 1, "error"

        with self.assertRaises(fetch.FetchDockerImageError):
            fetch.fetch_docker_image(url)

        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        self.assertTrue(cmd.startswith("skopeo copy --insecure-policy"))
        self.assertIn("docker://debian:10.9 docker-archive:/", cmd)
        self.assertIn("--override-os=linux --override-arch=amd64", cmd)
        self.assertTrue(cmd.endswith("debian_10_9.tar"))

    @mock.patch("requests.get")
    def test_scanpipe_pipes_fetch_fetch_urls(self, mock_get):
        urls = [
            "https://example.com/filename.zip",
            "https://example.com/archive.tar.gz",
        ]

        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url="mocked_url"
        )
        downloads, errors = fetch.fetch_urls(urls)
        self.assertEqual(2, len(downloads))
        self.assertEqual(urls[0], downloads[0].uri)
        self.assertEqual(urls[1], downloads[1].uri)
        self.assertEqual(0, len(errors))

        mock_get.side_effect = Exception
        downloads, errors = fetch.fetch_urls(urls)
        self.assertEqual(0, len(downloads))
        self.assertEqual(2, len(errors))
        self.assertEqual(urls, errors)

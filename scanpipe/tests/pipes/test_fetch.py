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
from django.test import override_settings

from requests import auth as request_auth

from scanpipe.pipes import fetch


class ScanPipeFetchPipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_fetch_get_fetcher(self):
        self.assertEqual(fetch.fetch_http, fetch.get_fetcher("http://a.b/f.z"))
        self.assertEqual(fetch.fetch_http, fetch.get_fetcher("https://a.b/f.z"))
        self.assertEqual(fetch.fetch_docker_image, fetch.get_fetcher("docker://image"))

        with self.assertRaises(ValueError) as cm:
            fetch.get_fetcher("")
        expected = "URL scheme '' is not supported."
        self.assertEqual(expected, str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            fetch.get_fetcher("abcd://a.b/f.z")
        expected = "URL scheme 'abcd' is not supported."
        self.assertEqual(expected, str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            fetch.get_fetcher("Docker://image")
        expected = "URL scheme 'Docker' is not supported. Did you mean: 'docker'?"
        self.assertEqual(expected, str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            fetch.get_fetcher("DOCKER://image")
        expected = "URL scheme 'DOCKER' is not supported. Did you mean: 'docker'?"
        self.assertEqual(expected, str(cm.exception))

    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_http(self, mock_get):
        url = "https://example.com/filename.zip"

        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=url
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "filename.zip").exists())

        url_with_spaces = "https://example.com/space%20in%20name.zip"
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=url_with_spaces
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "space in name.zip").exists())

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
    @mock.patch("scanpipe.pipes.fetch.run_command_safely")
    def test_scanpipe_pipes_fetch_docker_image(
        self, mock_run_command_safely, mock_skopeo, mock_platform
    ):
        with self.assertRaises(ValueError) as cm:
            fetch.fetch_docker_image("Docker://debian")
        expected = "Invalid Docker reference."
        self.assertEqual(expected, str(cm.exception))

        url = "docker://registry.com/debian:10.9"
        mock_platform.return_value = "linux", "amd64", ""
        mock_skopeo.return_value = "skopeo"
        mock_run_command_safely.side_effect = Exception

        with self.assertRaises(Exception):
            fetch.fetch_docker_image(url)

        mock_run_command_safely.assert_called_once()
        cmd_args = mock_run_command_safely.call_args[0][0]
        expected = (
            "skopeo",
            "copy",
            "--insecure-policy",
            "--override-os=linux",
            "--override-arch=amd64",
            url,
        )
        self.assertEqual(expected, cmd_args[0:6])
        self.assertTrue(cmd_args[-1].endswith("debian_10_9.tar"))

        with override_settings(SCANCODEIO_SKOPEO_AUTHFILE_LOCATION="auth.json"):
            with self.assertRaises(Exception):
                fetch.fetch_docker_image(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--authfile auth.json", cmd_args)

        credentials = {"registry.com": "user:password"}
        with override_settings(SCANCODEIO_SKOPEO_CREDENTIALS=credentials):
            with self.assertRaises(Exception):
                fetch.fetch_docker_image(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--src-creds user:password", cmd_args)

    @mock.patch("scanpipe.pipes.fetch._get_skopeo_location")
    @mock.patch("scanpipe.pipes.fetch.run_command_safely")
    def test_scanpipe_pipes_fetch_get_docker_image_platform(
        self,
        mock_run_command_safely,
        mock_skopeo,
    ):
        url = "docker://registry.com/busybox"
        mock_skopeo.return_value = "skopeo"
        mock_run_command_safely.return_value = "{}"

        fetch.get_docker_image_platform(url)
        mock_run_command_safely.assert_called_once()
        cmd_args = mock_run_command_safely.call_args[0][0]
        expected = (
            "skopeo",
            "inspect",
            "--insecure-policy",
            "--raw",
            "--no-creds",
            url,
        )
        self.assertEqual(expected, cmd_args)

        with override_settings(SCANCODEIO_SKOPEO_AUTHFILE_LOCATION="auth.json"):
            fetch.get_docker_image_platform(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--authfile auth.json", cmd_args)
            self.assertNotIn("--no-creds", cmd_args)

        credentials = {"registry.com": "user:password"}
        with override_settings(SCANCODEIO_SKOPEO_CREDENTIALS=credentials):
            fetch.get_docker_image_platform(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--creds user:password", cmd_args)
            self.assertNotIn("--no-creds", cmd_args)

    def test_scanpipe_pipes_fetch_docker_image_string_injection_protection(self):
        url = 'docker://;echo${IFS}"PoC"${IFS}"'
        with self.assertRaises(ValueError) as cm:
            fetch.fetch_docker_image(url)
        self.assertEqual("Invalid Docker reference.", str(cm.exception))

    @mock.patch("requests.sessions.Session.get")
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

    def test_scanpipe_pipes_fetch_get_request_session(self):
        url = "https://example.com/filename.zip"
        host = "example.com"
        credentials = ("user", "pass")

        session = fetch.get_request_session(url)
        self.assertIsNone(session.auth)

        with override_settings(SCANCODEIO_FETCH_BASIC_AUTH={host: credentials}):
            session = fetch.get_request_session(url)
            self.assertEqual(request_auth.HTTPBasicAuth(*credentials), session.auth)

        with override_settings(SCANCODEIO_FETCH_DIGEST_AUTH={host: credentials}):
            session = fetch.get_request_session(url)
            self.assertEqual(request_auth.HTTPDigestAuth(*credentials), session.auth)

        headers = {
            host: {"Authorization": "token TOKEN"},
        }
        with override_settings(SCANCODEIO_FETCH_HEADERS=headers):
            session = fetch.get_request_session(url)
            self.assertEqual("token TOKEN", session.headers.get("Authorization"))

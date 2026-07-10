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

import socket
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.test import override_settings

import requests
from requests import auth as request_auth

from scanpipe.models import Project
from scanpipe.pipes import fetch
from scanpipe.tests import make_mock_response


class ScanPipeFetchPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_fetch_get_fetcher(self):
        self.assertEqual(fetch.fetch_http, fetch.get_fetcher("http://a.b/f.z"))
        self.assertEqual(fetch.fetch_http, fetch.get_fetcher("https://a.b/f.z"))
        self.assertEqual(fetch.fetch_docker_image, fetch.get_fetcher("docker://image"))
        git_http_url = "https://github.com/aboutcode-org/scancode.io.git"
        self.assertEqual(fetch.fetch_git_repo, fetch.get_fetcher(git_http_url))
        self.assertEqual(fetch.fetch_git_repo, fetch.get_fetcher(git_http_url + "/"))
        self.assertEqual(fetch.fetch_package_url, fetch.get_fetcher("pkg:npm/d3@5.8.0"))
        self.assertEqual(fetch.fetch_package_url, fetch.get_fetcher("pkg:pypi/django"))

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

        with self.assertRaises(ValueError) as cm:
            fetch.get_fetcher("git@github.com:nexB/scancode.io.git")
        expected = "SSH 'git@' URLs are not supported. Use https:// instead."
        self.assertEqual(expected, str(cm.exception))

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_http(self, mock_get, mock_is_safe_url):
        url = "https://example.com/filename.zip"

        mock_get.return_value = make_mock_response(url=url)
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "filename.zip").exists())

        url_with_spaces = "https://example.com/space%20in%20name.zip"
        mock_get.return_value = make_mock_response(url=url_with_spaces)
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "space in name.zip").exists())

        headers = {
            "content-disposition": 'attachment; filename="another_name.zip"',
        }
        mock_get.return_value = make_mock_response(url=url, headers=headers)
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "another_name.zip").exists())

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_package_url(self, mock_get, mock_is_safe_url):
        package_url = "pkg:not_a_valid_purl"
        with self.assertRaises(ValueError) as cm:
            fetch.fetch_package_url(package_url)
        expected = f"purl is missing the required type component: '{package_url}'."
        self.assertEqual(expected, str(cm.exception))

        package_url = "pkg:generic/name@version"
        with self.assertRaises(ValueError) as cm:
            fetch.fetch_package_url(package_url)
        expected = f"Could not resolve a download URL for {package_url}."
        self.assertEqual(expected, str(cm.exception))

        package_url = "pkg:npm/d3@5.8.0"
        mock_get.return_value = make_mock_response(url="https://exa.com/filename.zip")
        downloaded_file = fetch.fetch_package_url(package_url)
        self.assertTrue(Path(downloaded_file.directory, "filename.zip").exists())

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("fetchcode.pypi.fetch_json_response")
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_pypi_package_url(
        self, mock_get, mock_fetch_json, mock_is_safe_url
    ):
        package_url = "pkg:pypi/django@5.2"
        download_url = "https://files.pythonhosted.org/packages/Django-5.2.tar.gz"

        mock_get.return_value = make_mock_response(url=download_url)
        mock_fetch_json.return_value = {"urls": [{"url": download_url}]}

        downloaded_file = fetch.fetch_package_url(package_url)
        self.assertEqual(download_url, mock_get.call_args[0][0])
        self.assertTrue(Path(downloaded_file.directory, "Django-5.2.tar.gz").exists())

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

        with override_settings(SCANPIPE={"SKOPEO_AUTHFILE_LOCATION": "auth.json"}):
            with self.assertRaises(Exception):
                fetch.fetch_docker_image(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--authfile=auth.json", cmd_args)

        credentials = {"registry.com": "user:password"}
        with override_settings(SCANPIPE={"SKOPEO_CREDENTIALS": credentials}):
            with self.assertRaises(Exception):
                fetch.fetch_docker_image(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--src-creds=user:password", cmd_args)

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

        with override_settings(SCANPIPE={"SKOPEO_AUTHFILE_LOCATION": "auth.json"}):
            fetch.get_docker_image_platform(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--authfile=auth.json", cmd_args)
            self.assertNotIn("--no-creds", cmd_args)

        credentials = {"registry.com": "user:password"}
        with override_settings(SCANPIPE={"SKOPEO_CREDENTIALS": credentials}):
            fetch.get_docker_image_platform(url)
            cmd_args = mock_run_command_safely.call_args[0][0]
            self.assertIn("--creds=user:password", cmd_args)
            self.assertNotIn("--no-creds", cmd_args)

    def test_scanpipe_pipes_fetch_docker_image_string_injection_protection(self):
        url = 'docker://;echo${IFS}"PoC"${IFS}"'
        with self.assertRaises(ValueError) as cm:
            fetch.fetch_docker_image(url)
        self.assertEqual("Invalid Docker reference.", str(cm.exception))

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_fetch_urls(self, mock_get, mock_is_safe_url):
        urls = [
            "https://example.com/filename.zip",
            "https://example.com/archive.tar.gz",
        ]

        mock_get.return_value = make_mock_response(url="mocked_url")
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

        with override_settings(SCANPIPE={"FETCH_BASIC_AUTH": {host: credentials}}):
            session = fetch.get_request_session(url)
            self.assertEqual(request_auth.HTTPBasicAuth(*credentials), session.auth)

        with override_settings(SCANPIPE={"FETCH_DIGEST_AUTH": {host: credentials}}):
            session = fetch.get_request_session(url)
            self.assertEqual(request_auth.HTTPDigestAuth(*credentials), session.auth)

        headers = {
            host: {"Authorization": "token TOKEN"},
        }
        with override_settings(SCANPIPE={"FETCH_HEADERS": headers}):
            session = fetch.get_request_session(url)
            self.assertEqual("token TOKEN", session.headers.get("Authorization"))

    @mock.patch("git.repo.base.Repo.clone_from")
    def test_scanpipe_pipes_fetch_git_repo(self, mock_clone_from):
        mock_clone_from.return_value = None
        url = "https://github.com/aboutcode-org/scancode.io.git"
        download = fetch.fetch_git_repo(url)

        self.assertEqual(url, download.uri)
        self.assertEqual("scancode.io.git", download.filename)
        self.assertTrue(str(download.path).endswith("scancode.io.git"))
        self.assertEqual("", download.size)
        self.assertEqual("", download.sha1)
        self.assertEqual("", download.md5)

    @staticmethod
    def make_addrinfo(*ips):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in ips]

    @staticmethod
    def make_addrinfo6(*ips):
        return [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, 0, 0, 0)) for ip in ips
        ]

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_is_safe_url(self, mock_getaddrinfo):
        # Valid public URLs
        mock_getaddrinfo.return_value = self.make_addrinfo(
            "93.184.216.34"
        )  # example.com
        self.assertTrue(fetch.is_safe_url("https://example.com/file.zip"))
        self.assertTrue(fetch.is_safe_url("http://example.com/file.zip"))

        # Invalid schemes
        self.assertFalse(fetch.is_safe_url("ftp://example.com/file.zip"))
        self.assertFalse(fetch.is_safe_url("docker://example.com/image"))
        self.assertFalse(fetch.is_safe_url(""))

        # No hostname
        self.assertFalse(fetch.is_safe_url("https://"))

        # Unresolvable hostname
        mock_getaddrinfo.side_effect = socket.gaierror
        self.assertFalse(fetch.is_safe_url("https://thisdomaindoesnotexist.invalid/"))
        mock_getaddrinfo.side_effect = None

        # Private ranges
        mock_getaddrinfo.return_value = self.make_addrinfo("192.168.1.1")
        self.assertFalse(fetch.is_safe_url("http://192.168.1.1/"))
        mock_getaddrinfo.return_value = self.make_addrinfo("10.0.0.1")
        self.assertFalse(fetch.is_safe_url("http://10.0.0.1/"))
        mock_getaddrinfo.return_value = self.make_addrinfo("172.16.0.1")
        self.assertFalse(fetch.is_safe_url("http://172.16.0.1/"))

        # Loopback
        mock_getaddrinfo.return_value = self.make_addrinfo("127.0.0.1")
        self.assertFalse(fetch.is_safe_url("http://127.0.0.1/"))
        mock_getaddrinfo.return_value = self.make_addrinfo("127.0.0.1")
        self.assertFalse(fetch.is_safe_url("http://localhost/"))

        # Link-local
        mock_getaddrinfo.return_value = self.make_addrinfo("169.254.169.254")
        self.assertFalse(fetch.is_safe_url("http://169.254.169.254/"))

        # Multicast
        mock_getaddrinfo.return_value = self.make_addrinfo("224.0.0.1")
        self.assertFalse(fetch.is_safe_url("http://224.0.0.1/"))

        # One of several resolved addresses is unsafe
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34", "127.0.0.1")
        self.assertFalse(fetch.is_safe_url("http://example.com/file.zip"))

        # A backslash before the "real" host can make `urlparse` and the
        # urllib3-based HTTP client disagree on which host is contacted.
        self.assertFalse(fetch.is_safe_url("http://127.0.0.1\\@example.com/"))

        # Control characters (e.g. from a CRLF-injection attempt) are rejected
        # wherever they appear in the URL.
        self.assertFalse(fetch.is_safe_url("http://example.com/\x00file.zip"))
        self.assertFalse(fetch.is_safe_url("http://example.com/\r\nfile.zip"))

        # IPv6 loopback and link-local addresses are rejected, and a safe
        # public IPv6-only host is accepted.
        mock_getaddrinfo.return_value = self.make_addrinfo6("::1")
        self.assertFalse(fetch.is_safe_url("http://example.com/file.zip"))
        mock_getaddrinfo.return_value = self.make_addrinfo6("fe80::1")
        self.assertFalse(fetch.is_safe_url("http://example.com/file.zip"))
        mock_getaddrinfo.return_value = self.make_addrinfo6("2606:4700:4700::1111")
        self.assertTrue(fetch.is_safe_url("http://example.com/file.zip"))

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    @mock.patch("requests.sessions.Session.head")
    def test_scanpipe_pipes_fetch_check_url(self, mock_head, mock_getaddrinfo):
        url = "https://example.com/file.zip"

        # Safe and accessible URL
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34")
        mock_head.return_value = make_mock_response(url=url)
        self.assertTrue(fetch.check_url(url))

        # Unsafe URL
        mock_getaddrinfo.return_value = self.make_addrinfo("127.0.0.1")
        self.assertFalse(fetch.check_url("http://localhost/"))

        # Safe URL but request fails
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34")
        mock_head.side_effect = requests.exceptions.RequestException
        self.assertFalse(fetch.check_url(url))

    def test_scanpipe_pipes_fetch_check_url_rejects_redirect_to_unsafe_host(self):
        def getaddrinfo(host, *args, **kwargs):
            if host == "127.0.0.1":
                return self.make_addrinfo("127.0.0.1")
            return self.make_addrinfo("93.184.216.34")

        url = "https://example.com/file.zip"
        redirect_response = make_mock_response(
            url=url,
            status_code=302,
            headers={"location": "http://127.0.0.1/internal"},
        )

        with (
            mock.patch(
                "scanpipe.pipes.fetch.socket.getaddrinfo", side_effect=getaddrinfo
            ),
            mock.patch(
                "requests.sessions.Session.head", return_value=redirect_response
            ) as mock_head,
        ):
            self.assertFalse(fetch.check_url(url))
            self.assertEqual(1, mock_head.call_count)

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    @mock.patch("requests.sessions.Session.head")
    def test_scanpipe_pipes_fetch_check_urls_availability(
        self, mock_head, mock_getaddrinfo
    ):
        http_urls = [
            "https://example.com/file.zip",
            "https://example.com/archive.tar.gz",
        ]
        urls = http_urls + [
            "docker://image",
            "pkg:npm/name@version",
        ]

        # All URLs safe and accessible
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34")
        mock_head.return_value = make_mock_response(url="mocked_url")
        self.assertEqual([], fetch.check_urls_availability(urls))

        # All URLs fail
        mock_head.side_effect = requests.exceptions.RequestException
        self.assertEqual(http_urls, fetch.check_urls_availability(urls))

    @mock.patch("scanpipe.pipes.fetch.is_safe_url")
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_request_with_safe_redirects_revalidates_redirects(
        self, mock_get, mock_is_safe_url
    ):
        safe_url = "https://example.com/"
        unsafe_redirect_url = "http://127.0.0.1/internal"
        mock_is_safe_url.side_effect = lambda url: url == safe_url

        mock_get.return_value = make_mock_response(
            url=safe_url, status_code=302, headers={"location": unsafe_redirect_url}
        )

        with self.assertRaises(requests.RequestException):
            fetch._request_with_safe_redirects(safe_url, "get")

        mock_is_safe_url.assert_any_call(unsafe_redirect_url)

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_request_with_safe_redirects_follows_safe_redirect(
        self, mock_get, mock_is_safe_url
    ):
        first_url = "https://example.com/"
        final_url = "https://example.com/final"

        redirect_response = make_mock_response(
            url=first_url, status_code=302, headers={"location": final_url}
        )
        final_response = make_mock_response(url=final_url)
        mock_get.side_effect = [redirect_response, final_response]

        response = fetch._request_with_safe_redirects(first_url, "get")
        self.assertEqual(final_response, response)
        self.assertEqual(2, mock_get.call_count)

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_request_with_safe_redirects_relative_location(
        self, mock_get, mock_is_safe_url
    ):
        first_url = "https://example.com/downloads/"
        final_url = "https://example.com/downloads/final.zip"

        redirect_response = make_mock_response(
            url=first_url, status_code=302, headers={"location": "final.zip"}
        )
        final_response = make_mock_response(url=final_url)
        mock_get.side_effect = [redirect_response, final_response]

        response = fetch._request_with_safe_redirects(first_url, "get")
        self.assertEqual(final_response, response)
        mock_is_safe_url.assert_any_call(final_url)

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_request_with_safe_redirects_too_many_redirects(
        self, mock_get, mock_is_safe_url
    ):
        url = "https://example.com/"
        mock_get.return_value = make_mock_response(
            url=url, status_code=302, headers={"location": url}
        )

        with self.assertRaises(requests.RequestException):
            fetch._request_with_safe_redirects(url, "get")
        self.assertEqual(fetch.MAX_REDIRECT_HOPS + 1, mock_get.call_count)

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_request_with_safe_redirects_max_hops_allowed(
        self, mock_get, mock_is_safe_url
    ):
        url = "https://example.com/"
        redirect_response = make_mock_response(
            url=url, status_code=302, headers={"location": url}
        )
        final_response = make_mock_response(url=url)
        # One redirect response per hop, then a final non-redirect response.
        mock_get.side_effect = [redirect_response] * fetch.MAX_REDIRECT_HOPS + [
            final_response
        ]

        response = fetch._request_with_safe_redirects(url, "get")
        self.assertEqual(final_response, response)
        self.assertEqual(fetch.MAX_REDIRECT_HOPS + 1, mock_get.call_count)

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_http_rejects_unsafe_url(
        self, mock_get, mock_getaddrinfo
    ):
        mock_getaddrinfo.return_value = self.make_addrinfo("127.0.0.1")

        with self.assertRaises(requests.RequestException):
            fetch.fetch_http("http://127.0.0.1/internal")
        mock_get.assert_not_called()

    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_http_rejects_parser_differential_bypass(
        self, mock_get
    ):
        # Same payload as the SSRF advisory: `urlparse` and the urllib3-based
        # HTTP client would otherwise disagree on which host is contacted.
        with self.assertRaises(requests.RequestException):
            fetch.fetch_http("http://127.0.0.1:8081\\@8.8.8.8/")
        mock_get.assert_not_called()

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    @mock.patch("scanpipe.pipes.fetch.purl2url.get_download_url")
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_package_url_rejects_unsafe_download_url(
        self, mock_get, mock_get_download_url, mock_getaddrinfo
    ):
        mock_get_download_url.return_value = "http://127.0.0.1/evil.tar.gz"
        mock_getaddrinfo.return_value = self.make_addrinfo("127.0.0.1")

        with self.assertRaises(requests.RequestException):
            fetch.fetch_package_url("pkg:npm/d3@5.8.0")
        mock_get.assert_not_called()

    def test_scanpipe_pipes_fetch_set_project_purl_from_input_url(self):
        project = Project.objects.create(name="purl_from_url")

        # Single resolvable HTTP URL -> purl auto-filled
        fetch.set_project_purl_from_input_url(
            project, ["https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"]
        )
        project.refresh_from_db()
        self.assertEqual("pkg:npm/lodash@4.17.21", project.purl)

        # Existing purl is not overwritten
        fetch.set_project_purl_from_input_url(
            project, ["https://registry.npmjs.org/react/-/react-18.0.0.tgz"]
        )
        project.refresh_from_db()
        self.assertEqual("pkg:npm/lodash@4.17.21", project.purl)

        # Multiple URLs -> purl not set
        project2 = Project.objects.create(name="purl_from_url2")
        fetch.set_project_purl_from_input_url(
            project2,
            [
                "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                "https://registry.npmjs.org/react/-/react-18.0.0.tgz",
            ],
        )
        project2.refresh_from_db()
        self.assertEqual("", project2.purl)

        # Bad input -> no crash, no purl set
        project3 = Project.objects.create(name="purl_from_url3")
        fetch.set_project_purl_from_input_url(project3, ["not-a-url"])
        project3.refresh_from_db()
        self.assertEqual("", project3.purl)

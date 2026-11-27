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

import json
import os
import socket
import tempfile
import time
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test import override_settings

import requests
import urllib3
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
            fetch.get_fetcher("git@github.com:aboutcode-org/scancode.io.git")
        expected = "SSH 'git@' URLs are not supported. Use https:// instead."
        self.assertEqual(expected, str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            fetch.get_fetcher("git://github.com/aboutcode-org/scancode.io.git")
        expected = "Unencrypted git:// URLs are not supported. Use https:// instead."
        self.assertEqual(expected, str(cm.exception))

    def test_scanpipe_pipes_fetch_get_fetcher_refuses_unsupported_git_urls(self):
        unsupported_git_urls = [
            "/srv/repository/.git",
            "file:///srv/repository/.git",
            "ssh://host/repository.git",
        ]
        for url in unsupported_git_urls:
            with self.assertRaises(ValueError) as cm:
                fetch.get_fetcher(url)
            expected = "Only http:// and https:// Git URLs are supported."
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
    def test_scanpipe_pipes_fetch_http_keeps_download_in_directory(
        self, mock_get, mock_is_safe_url
    ):
        project = Project.objects.create(name="Analysis")
        url = "https://example.com/filename.zip"

        for filename in ("../escape.zip", "/var/escape.zip"):
            headers = {"content-disposition": f'attachment; filename="{filename}"'}
            mock_get.return_value = make_mock_response(url=url, headers=headers)
            downloaded_file = fetch.fetch_http(url, to=project.tmp_path)
            self.assertEqual(project.tmp_path / "escape.zip", downloaded_file.path)

        encoded_url = "https://example.com/..%2F..%2Fescape.zip"
        mock_get.return_value = make_mock_response(url=encoded_url)
        downloaded_file = fetch.fetch_http(encoded_url, to=project.tmp_path)
        self.assertEqual(project.tmp_path / "escape.zip", downloaded_file.path)

    def test_scanpipe_pipes_fetch_get_safe_filename(self):
        self.assertEqual("file.zip", fetch.get_safe_filename("file.zip"))
        self.assertEqual("file.zip", fetch.get_safe_filename("../../file.zip"))
        self.assertEqual("file.zip", fetch.get_safe_filename("/etc/file.zip"))

        for filename in ("", ".", "..", "../.."):
            with self.assertRaisesMessage(ValueError, "Invalid download filename"):
                fetch.get_safe_filename(filename)

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
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_url_to_directory(self, mock_get, mock_is_safe_url):
        project = Project.objects.create(name="Analysis")
        mock_get.return_value = make_mock_response(url="https://exa.com/filename.zip")

        downloaded_file = fetch.fetch_url("pkg:npm/d3@5.8.0", to=project.tmp_path)
        self.assertEqual(project.tmp_path, downloaded_file.directory)
        self.assertTrue(Path(project.tmp_path, "filename.zip").exists())

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

        project = Project.objects.create(name="Analysis")
        downloaded_file = fetch.fetch_package_url(package_url, to=project.tmp_path)
        self.assertEqual(project.tmp_path, downloaded_file.directory)
        self.assertTrue(Path(project.tmp_path, "Django-5.2.tar.gz").exists())

    def test_scanpipe_pipes_fetch_get_api_link(self):
        api_url = "https://vulnerablecode.example/api/v3"
        link_url = "http://vulnerablecode:8000/api/v3/packages/1/advisories?page=3"
        expected = f"{api_url}/packages/1/advisories?page=3"
        self.assertEqual(expected, fetch.get_api_link(link_url, api_url))

        link_url = "https://attacker.example/api/v3/packages?page=2"
        expected = f"{api_url}/packages?page=2"
        self.assertEqual(expected, fetch.get_api_link(link_url, api_url))

        proxied_api_url = "https://proxy.example/vulnerablecode/api/v3"
        link_url = "http://vulnerablecode:8000/api/v3/packages?page=2"
        expected = f"{proxied_api_url}/packages?page=2"
        self.assertEqual(expected, fetch.get_api_link(link_url, proxied_api_url))

    def test_scanpipe_pipes_fetch_get_api_link_outside_of_the_api(self):
        api_url = "https://proxy.example/vulnerablecode/api/v3"
        outside_link_urls = [
            "http://vulnerablecode/api/v3/../../../purldb/api/collect/",
            "http://vulnerablecode/api/v3/%2e%2e/%2E%2E/purldb/api/",
            "http://vulnerablecode/api/v3/./packages",
            "http://vulnerablecode/purldb/api/packages/",
            "http://vulnerablecode/",
        ]
        for link_url in outside_link_urls:
            expected = f"Link outside of the service API: {link_url}"
            with self.assertRaisesMessage(ValueError, expected):
                fetch.get_api_link(link_url, api_url)

    def test_scanpipe_pipes_fetch_is_under_path(self):
        self.assertTrue(fetch.is_under_path("/api/v3", "/api/v3"))
        self.assertTrue(fetch.is_under_path("/api/v3/packages", "/api/v3/"))
        self.assertTrue(fetch.is_under_path("/packages", ""))
        self.assertFalse(fetch.is_under_path("/api/v3x", "/api/v3"))
        self.assertFalse(fetch.is_under_path("/api", "/api/v3"))

    def test_scanpipe_pipes_fetch_get_api_link_path(self):
        api_path = "/vulnerablecode/api/v3"
        cases = [
            ("/vulnerablecode/api/v3/packages", "/vulnerablecode/api/v3/packages"),
            ("/api/v3/packages", "/vulnerablecode/api/v3/packages"),
            ("/api/v3", "/vulnerablecode/api/v3"),
            ("/v3/packages", "/vulnerablecode/api/v3/packages"),
            ("/other/packages", "/other/packages"),
            ("/api/v3x/packages", "/api/v3x/packages"),
        ]
        for link_path, expected in cases:
            api_link_path = fetch.get_api_link_path(link_path, api_path)
            self.assertEqual(expected, api_link_path, link_path)

        api_link_path = fetch.get_api_link_path("/api/packages/", "/api/")
        self.assertEqual("/api/packages/", api_link_path)
        self.assertEqual("/packages", fetch.get_api_link_path("/packages", ""))

    @mock.patch("fetchcode.pypi.fetch_json_response")
    def test_scanpipe_pipes_fetch_get_pypi_download_url(self, mock_fetch_json):
        package_url = "pkg:pypi/owned-selector@1.0"
        wheel_url = "https://files.pythonhosted.org/owned_selector-1.0-py3-none-any.whl"
        sdist_url = "https://files.pythonhosted.org/owned_selector-1.0.tar.gz"
        mock_fetch_json.return_value = {
            "urls": [
                {
                    "filename": "owned_selector-1.0-py3-none-any.whl",
                    "packagetype": "bdist_wheel",
                    "url": wheel_url,
                },
                {
                    "filename": "owned_selector-1.0.tar.gz",
                    "packagetype": "sdist",
                    "url": sdist_url,
                },
            ]
        }

        download_url = fetch.get_pypi_download_url(package_url, file_name=None)
        self.assertEqual(sdist_url, download_url)

        wheel_name = "owned_selector-1.0-py3-none-any.whl"
        download_url = fetch.get_pypi_download_url(package_url, file_name=wheel_name)
        self.assertEqual(wheel_url, download_url)

        expected = f"No OWNED_SELECTOR-1.0.tar.gz distribution found for {package_url}."
        with self.assertRaisesMessage(ValueError, expected):
            fetch.get_pypi_download_url(
                package_url, file_name="OWNED_SELECTOR-1.0.tar.gz"
            )

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("fetchcode.pypi.fetch_json_response")
    @mock.patch("requests.sessions.Session.get")
    def test_scanpipe_pipes_fetch_pypi_package_url_file_name(
        self, mock_get, mock_fetch_json, mock_is_safe_url
    ):
        wheel_name = "Django-5.2-py3-none-any.whl"
        package_url = f"pkg:pypi/django@5.2?file_name={wheel_name}"
        wheel_url = f"https://files.pythonhosted.org/packages/{wheel_name}"
        sdist_url = "https://files.pythonhosted.org/packages/Django-5.2.tar.gz"
        mock_fetch_json.return_value = {
            "urls": [
                {
                    "filename": "Django-5.2.tar.gz",
                    "packagetype": "sdist",
                    "url": sdist_url,
                },
                {
                    "filename": wheel_name,
                    "packagetype": "bdist_wheel",
                    "url": wheel_url,
                },
            ]
        }
        mock_get.return_value = make_mock_response(url=wheel_url)

        downloaded_file = fetch.fetch_package_url(package_url)
        self.assertEqual(wheel_url, mock_get.call_args[0][0])
        self.assertTrue(Path(downloaded_file.directory, wheel_name).exists())

    @mock.patch("scanpipe.pipes.fetch.validate_docker_registry")
    @mock.patch("scanpipe.pipes.fetch.get_docker_image_platform")
    @mock.patch("scanpipe.pipes.fetch._get_skopeo_location")
    @mock.patch("scanpipe.pipes.fetch.run_command_safely")
    def test_scanpipe_pipes_fetch_docker_image(
        self, mock_run_command_safely, mock_skopeo, mock_platform, mock_validate
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
            self.assertTrue(cmd_args[5].startswith("--authfile="))
            self.assertNotIn("password", " ".join(cmd_args))

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
            self.assertTrue(cmd_args[4].startswith("--authfile="))
            self.assertNotIn("password", " ".join(cmd_args))

    def test_scanpipe_pipes_fetch_skopeo_authfile(self):
        url = "docker://registry.com/busybox"
        with fetch.skopeo_authfile(url) as authfile:
            self.assertEqual("", authfile)

        with override_settings(SCANPIPE={"SKOPEO_AUTHFILE_LOCATION": "auth.json"}):
            with fetch.skopeo_authfile(url) as authfile:
                self.assertEqual("auth.json", authfile)

        credentials = {"registry.com": "user:password"}
        with override_settings(SCANPIPE={"SKOPEO_CREDENTIALS": credentials}):
            with fetch.skopeo_authfile(url) as authfile:
                authfile_path = Path(authfile)
                expected = {"auths": {"registry.com": {"auth": "dXNlcjpwYXNzd29yZA=="}}}
                self.assertEqual(expected, json.loads(authfile_path.read_text()))
                self.assertEqual(0o600, authfile_path.stat().st_mode & 0o777)
            self.assertFalse(authfile_path.exists())

    def test_scanpipe_pipes_fetch_get_docker_registry(self):
        registry_by_docker_url = {
            "docker://debian": "docker.io",
            "docker://library/debian:10.9": "docker.io",
            "docker://registry.com/debian:10.9": "registry.com",
            "docker://registry.com:5000/debian": "registry.com:5000",
            "docker://127.0.0.1:5000/image": "127.0.0.1:5000",
            "docker://localhost/image": "localhost",
            "docker://Internal/image": "Internal",
        }
        for docker_url, expected in registry_by_docker_url.items():
            self.assertEqual(expected, fetch.get_docker_registry(docker_url))

    @mock.patch("scanpipe.pipes.fetch.run_command_safely")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_docker_image_rejects_private_registry(
        self, mock_getaddrinfo, mock_run_command_safely
    ):
        mock_getaddrinfo.return_value = self.make_addrinfo("10.0.0.5")
        unsafe_docker_urls = [
            "docker://registry.internal/image",
            "docker://127.0.0.1:5000/image",
            "docker://Internal/image",
            "docker://10.0.0.1@registry.com/image",
        ]
        for docker_url in unsafe_docker_urls:
            with self.assertRaisesMessage(ValueError, "Unsafe Docker registry"):
                fetch.fetch_docker_image(docker_url)
        mock_run_command_safely.assert_not_called()

        allowed_hosts = ["registry.internal"]
        with override_settings(SCANPIPE={"ALLOWED_PRIVATE_HOSTS": allowed_hosts}):
            fetch.validate_docker_registry("docker://registry.internal/image")

        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34")
        fetch.validate_docker_registry("docker://debian")
        mock_getaddrinfo.assert_called_with("docker.io", None)

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

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("git.repo.base.Repo.clone_from")
    def test_scanpipe_pipes_fetch_git_repo(
        self, mock_clone_from, mock_is_safe_url, mock_getaddrinfo
    ):
        mock_clone_from.return_value = None
        mock_getaddrinfo.return_value = self.make_addrinfo("140.82.121.4")
        url = "https://github.com/aboutcode-org/scancode.io.git"
        download = fetch.fetch_git_repo(url)

        mock_is_safe_url.assert_called_once_with(url)
        git_env = mock_clone_from.call_args.kwargs["env"]
        self.assertEqual("http.followRedirects", git_env["GIT_CONFIG_KEY_0"])
        self.assertEqual("false", git_env["GIT_CONFIG_VALUE_0"])
        self.assertEqual("http.curloptResolve", git_env["GIT_CONFIG_KEY_1"])
        expected = "github.com:443:140.82.121.4"
        self.assertEqual(expected, git_env["GIT_CONFIG_VALUE_1"])

        self.assertEqual(url, download.uri)
        self.assertEqual("scancode.io.git", download.filename)
        self.assertTrue(str(download.path).endswith("scancode.io.git"))
        self.assertEqual("", download.size)
        self.assertEqual("", download.sha1)
        self.assertEqual("", download.md5)

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=False)
    @mock.patch("git.repo.base.Repo.clone_from")
    def test_scanpipe_pipes_fetch_git_repo_unsafe_url(
        self, mock_clone_from, mock_is_safe_url
    ):
        url = "https://internal.host/repository.git"
        with mock.patch("tempfile.mkdtemp") as mock_mkdtemp:
            with self.assertRaises(ValueError) as cm:
                fetch.fetch_git_repo(url)

        self.assertEqual(f"Unsafe URL: {url}", str(cm.exception))
        mock_mkdtemp.assert_not_called()
        mock_clone_from.assert_not_called()

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

        # Shared address space (CGNAT), used by some cloud metadata services
        mock_getaddrinfo.return_value = self.make_addrinfo("100.100.100.200")
        self.assertFalse(fetch.is_safe_url("http://100.100.100.200/"))

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

    def test_scanpipe_pipes_fetch_is_unsafe_ip_address(self):
        unsafe_ip_addresses = [
            "0.0.0.1",
            "10.0.0.1",
            "100.64.0.1",
            "100.100.100.200",
            "127.0.0.1",
            "169.254.169.254",
            "192.168.1.1",
            "224.0.0.1",
            "255.255.255.255",
            "::1",
            "::ffff:127.0.0.1",
            "::ffff:169.254.169.254",
            "fc00::1",
            "fe80::1",
            "fe80::1%eth0",
            "ff02::1",
        ]
        for ip_address in unsafe_ip_addresses:
            self.assertTrue(fetch.is_unsafe_ip_address(ip_address), msg=ip_address)

        public_ip_addresses = [
            "93.184.216.34",
            "::ffff:93.184.216.34",
            "2606:4700:4700::1111",
        ]
        for ip_address in public_ip_addresses:
            self.assertFalse(fetch.is_unsafe_ip_address(ip_address), msg=ip_address)

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_is_safe_url_host_parsing(self, mock_getaddrinfo):
        # A URL that urllib3 cannot parse is rejected without an exception.
        self.assertFalse(fetch.is_safe_url("http://[::1/"))
        mock_getaddrinfo.assert_not_called()

        # An IPv6 literal host is resolved without its brackets.
        mock_getaddrinfo.return_value = self.make_addrinfo6("2606:4700:4700::1111")
        self.assertTrue(fetch.is_safe_url("http://[2606:4700:4700::1111]:8080/"))
        mock_getaddrinfo.assert_called_once_with("2606:4700:4700::1111", None)

        mock_getaddrinfo.return_value = self.make_addrinfo6("::ffff:127.0.0.1")
        self.assertFalse(fetch.is_safe_url("http://[::ffff:127.0.0.1]/"))

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_is_safe_url_allowed_private_hosts(
        self, mock_getaddrinfo
    ):
        mock_getaddrinfo.return_value = self.make_addrinfo("10.0.0.5")
        url = "http://dejacode.internal:8000/api/"
        self.assertFalse(fetch.is_safe_url(url))

        allowed_hosts = ["dejacode.internal:8000", "10.0.0.6", "[fd00::1]:8080", ""]
        with override_settings(SCANPIPE={"ALLOWED_PRIVATE_HOSTS": allowed_hosts}):
            self.assertTrue(fetch.is_safe_url(url))
            self.assertTrue(fetch.is_safe_url("https://DEJACODE.internal:8000/"))
            self.assertFalse(fetch.is_safe_url("http://dejacode.internal/"))
            self.assertFalse(fetch.is_safe_url("http://dejacode.internal:8001/"))
            self.assertTrue(fetch.is_safe_url("http://10.0.0.6/"))
            self.assertTrue(fetch.is_safe_url("https://10.0.0.6/"))
            self.assertTrue(fetch.is_safe_url("http://10.0.0.6:80/"))
            self.assertFalse(fetch.is_safe_url("http://10.0.0.6:8080/"))
            self.assertTrue(fetch.is_safe_url("http://[fd00::1]:8080/"))
            self.assertFalse(fetch.is_safe_url("http://[fd00::1]/"))
            self.assertFalse(fetch.is_safe_url("http://other.internal/"))
            self.assertFalse(fetch.is_safe_url("http://dejacode.internal.example/"))
            self.assertFalse(fetch.is_safe_url("ftp://dejacode.internal/"))

    def test_scanpipe_pipes_fetch_get_allowed_private_addresses_purldb_url(self):
        with override_settings(PURLDB_URL=""):
            self.assertEqual(set(), fetch.get_allowed_private_addresses())

        with override_settings(PURLDB_URL="http://purldb:8000"):
            expected = {("purldb", 8000)}
            self.assertEqual(expected, fetch.get_allowed_private_addresses())
            self.assertTrue(fetch.is_allowed_private_host("purldb", 8000))
            self.assertFalse(fetch.is_allowed_private_host("purldb", 8001))

        with override_settings(PURLDB_URL="https://PURLDB.internal"):
            expected = {("purldb.internal", 443)}
            self.assertEqual(expected, fetch.get_allowed_private_addresses())

        with override_settings(PURLDB_URL="purldb:8000"):
            expected = 'Invalid PURLDB_URL setting: "purldb:8000".'
            with self.assertRaisesMessage(ImproperlyConfigured, expected):
                fetch.get_allowed_private_addresses()

    def test_scanpipe_pipes_fetch_parse_allowed_private_host(self):
        valid_entries = {
            "dejacode.internal:8000": ("dejacode.internal", 8000),
            "DEJACODE.internal": ("dejacode.internal", None),
            "10.0.0.6": ("10.0.0.6", None),
            "[fd00::1]:8080": ("fd00::1", 8080),
        }
        for allowed_entry, expected in valid_entries.items():
            parsed_entry = fetch.parse_allowed_private_host(allowed_entry)
            self.assertEqual(expected, parsed_entry)

        invalid_entries = [
            "dejacode.internal:abc",
            "http://dejacode.internal:8000",
            "dejacode.internal/path",
            "user@dejacode.internal",
            ":8000",
        ]
        for allowed_entry in invalid_entries:
            expected = (
                f'Invalid SCANCODEIO_ALLOWED_PRIVATE_HOSTS entry: "{allowed_entry}"'
            )
            with self.assertRaisesMessage(ImproperlyConfigured, expected):
                fetch.parse_allowed_private_host(allowed_entry)

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_validate_safe_url(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34")
        fetch.validate_safe_url("https://example.com/webhook")

        mock_getaddrinfo.return_value = self.make_addrinfo("127.0.0.1")
        with self.assertRaises(ValidationError) as cm:
            fetch.validate_safe_url("https://localhost/webhook")
        self.assertIn("SCANCODEIO_ALLOWED_PRIVATE_HOSTS", cm.exception.message)

    @mock.patch("urllib3.util.connection.create_connection")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_public_address_connection_pins_address(
        self, mock_getaddrinfo, mock_create_connection
    ):
        connected_socket = mock.Mock()
        mock_create_connection.return_value = connected_socket
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34")
        connection = fetch.PublicAddressHTTPSConnection("example.com", 443)

        self.assertEqual(connected_socket, connection._new_conn())
        self.assertEqual(
            ("93.184.216.34", 443), mock_create_connection.call_args.args[0]
        )
        # The host name is kept for the TLS SNI, certificate, and Host header.
        self.assertEqual("example.com", connection.host)

    @mock.patch("urllib3.util.connection.create_connection")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_public_address_connection_rejects_private_address(
        self, mock_getaddrinfo, mock_create_connection
    ):
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34", "10.0.0.1")
        connection = fetch.PublicAddressHTTPConnection("example.com", 80)

        with self.assertRaises(urllib3.exceptions.NewConnectionError):
            connection._new_conn()
        mock_create_connection.assert_not_called()

    @mock.patch("urllib3.util.connection.create_connection")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_public_address_connection_tries_each_address(
        self, mock_getaddrinfo, mock_create_connection
    ):
        connected_socket = mock.Mock()
        mock_create_connection.side_effect = [OSError("unreachable"), connected_socket]
        mock_getaddrinfo.return_value = self.make_addrinfo6(
            "2606:4700:4700::1111"
        ) + self.make_addrinfo("93.184.216.34")
        connection = fetch.PublicAddressHTTPConnection("example.com", 80)

        self.assertEqual(connected_socket, connection._new_conn())
        connected_addresses = [
            call.args[0] for call in mock_create_connection.call_args_list
        ]
        expected = [("2606:4700:4700::1111", 80), ("93.184.216.34", 80)]
        self.assertEqual(expected, connected_addresses)
        self.assertEqual("example.com", connection.host)

    @mock.patch("urllib3.util.connection.create_connection")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_public_address_connection_allowed_private_host(
        self, mock_getaddrinfo, mock_create_connection
    ):
        connected_socket = mock.Mock()
        mock_create_connection.return_value = connected_socket
        mock_getaddrinfo.return_value = self.make_addrinfo("10.0.0.5")
        connection = fetch.PublicAddressHTTPConnection("dejacode.internal", 8000)

        allowed_hosts = ["dejacode.internal:8000"]
        with override_settings(SCANPIPE={"ALLOWED_PRIVATE_HOSTS": allowed_hosts}):
            self.assertEqual(connected_socket, connection._new_conn())
        self.assertEqual(
            ("dejacode.internal", 8000), mock_create_connection.call_args.args[0]
        )

        other_port_connection = fetch.PublicAddressHTTPConnection(
            "dejacode.internal", 8001
        )
        with override_settings(SCANPIPE={"ALLOWED_PRIVATE_HOSTS": allowed_hosts}):
            with self.assertRaises(urllib3.exceptions.NewConnectionError):
                other_port_connection._new_conn()
        self.assertEqual(1, mock_create_connection.call_count)

    @mock.patch("urllib3.util.connection.create_connection")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_check_url_rejects_changed_dns_answer(
        self, mock_getaddrinfo, mock_create_connection
    ):
        # A public address when the URL is checked, then a private one when the
        # connection resolves the host again.
        mock_getaddrinfo.side_effect = [
            self.make_addrinfo("93.184.216.34"),
            self.make_addrinfo("127.0.0.1"),
        ]
        mock_create_connection.side_effect = OSError("blocked in tests")

        self.assertFalse(fetch.check_url("http://rebinding.example/file.zip"))
        mock_create_connection.assert_not_called()

    @mock.patch("urllib3.util.connection.create_connection")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_get_request_session_pins_proxy_address(
        self, mock_getaddrinfo, mock_create_connection
    ):
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.35")
        mock_create_connection.side_effect = OSError("blocked in tests")
        proxies = {"https": "http://proxy.example:3128"}

        session = fetch.get_request_session("https://example.com/")
        with self.assertRaises(requests.exceptions.ConnectionError):
            session.get("https://example.com/", proxies=proxies, timeout=1)
        self.assertEqual(
            ("93.184.216.35", 3128), mock_create_connection.call_args.args[0]
        )

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_get_request_session_without_credentials(
        self, mock_getaddrinfo
    ):
        url = "https://example.com/filename.zip"
        fetch_settings = {
            "FETCH_BASIC_AUTH": {"example.com": ("user", "password")},
            "FETCH_HEADERS": {"example.com": {"X-Api-Key": "secret"}},
        }
        with override_settings(SCANPIPE=fetch_settings):
            session = fetch.get_request_session(url, include_credentials=False)

        self.assertIsInstance(session.auth, fetch.NoCredentialsAuth)
        self.assertNotIn("X-Api-Key", session.headers)
        adapter = session.get_adapter(url)
        self.assertIsInstance(adapter, fetch.PublicAddressHTTPAdapter)

    def test_scanpipe_pipes_fetch_get_request_session_without_netrc_credentials(self):
        url = "http://packages.example/private.zip"
        request = requests.Request("GET", url)

        with tempfile.TemporaryDirectory() as netrc_directory:
            netrc_file = Path(netrc_directory) / "netrc"
            netrc_file.write_text("machine packages.example login user password pass")

            with mock.patch.dict(os.environ, {"NETRC": str(netrc_file)}):
                session = fetch.get_request_session(url)
                prepared_request = session.prepare_request(request)
                self.assertIn("Authorization", prepared_request.headers)

                session = fetch.get_request_session(url, include_credentials=False)
                prepared_request = session.prepare_request(request)
                self.assertNotIn("Authorization", prepared_request.headers)

    @mock.patch("requests.sessions.Session.post")
    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_send_safe_request(self, mock_getaddrinfo, mock_post):
        url = "https://example.com/webhook"
        mock_getaddrinfo.return_value = self.make_addrinfo("93.184.216.34")
        mock_post.return_value = make_mock_response(url=url)

        response = fetch.send_safe_request(url, "post", data="{}", timeout=5)
        self.assertEqual(200, response.status_code)
        mock_post.assert_called_once_with(
            url, allow_redirects=False, data="{}", timeout=5
        )

        mock_post.reset_mock()
        mock_getaddrinfo.return_value = self.make_addrinfo("169.254.169.254")
        with self.assertRaisesMessage(requests.RequestException, "Unsafe URL"):
            fetch.send_safe_request(url, "post")
        mock_post.assert_not_called()

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get", autospec=True)
    def test_scanpipe_pipes_fetch_request_with_safe_redirects_scopes_credentials(
        self, mock_get, mock_is_safe_url
    ):
        first_url = "https://packages.example/private.zip"
        redirect_url = "https://unrelated.example/artifact.zip"
        mock_get.side_effect = [
            make_mock_response(
                url=first_url, status_code=302, headers={"location": redirect_url}
            ),
            make_mock_response(url=redirect_url),
        ]
        fetch_settings = {
            "FETCH_BASIC_AUTH": {"packages.example": ("user", "password")},
            "FETCH_HEADERS": {"packages.example": {"X-Api-Key": "secret"}},
        }

        with override_settings(SCANPIPE=fetch_settings):
            fetch._request_with_safe_redirects(first_url, "get")

        first_session = mock_get.call_args_list[0].args[0]
        expected_auth = request_auth.HTTPBasicAuth("user", "password")
        self.assertEqual(expected_auth, first_session.auth)
        self.assertEqual("secret", first_session.headers.get("X-Api-Key"))
        redirect_session = mock_get.call_args_list[1].args[0]
        self.assertIsNone(redirect_session.auth)
        self.assertNotIn("X-Api-Key", redirect_session.headers)

    @mock.patch("scanpipe.pipes.fetch.is_safe_url", return_value=True)
    @mock.patch("requests.sessions.Session.get", autospec=True)
    def test_scanpipe_pipes_fetch_request_with_safe_redirects_https_downgrade(
        self, mock_get, mock_is_safe_url
    ):
        https_url = "https://packages.example/private.zip"
        same_host_https_url = "https://packages.example/mirror/private.zip"
        http_url = "http://packages.example/private.zip"
        mock_get.side_effect = [
            make_mock_response(
                url=https_url,
                status_code=302,
                headers={"location": same_host_https_url},
            ),
            make_mock_response(
                url=same_host_https_url,
                status_code=302,
                headers={"location": http_url},
            ),
            make_mock_response(url=http_url),
        ]
        fetch_settings = {
            "FETCH_DIGEST_AUTH": {"packages.example": ("user", "password")},
            "FETCH_HEADERS": {"packages.example": {"X-Api-Key": "secret"}},
        }

        with override_settings(SCANPIPE=fetch_settings):
            fetch._request_with_safe_redirects(https_url, "get")

        expected_auth = request_auth.HTTPDigestAuth("user", "password")
        same_host_https_session = mock_get.call_args_list[1].args[0]
        self.assertEqual(expected_auth, same_host_https_session.auth)
        self.assertEqual("secret", same_host_https_session.headers.get("X-Api-Key"))
        http_session = mock_get.call_args_list[2].args[0]
        self.assertIsInstance(http_session.auth, fetch.NoCredentialsAuth)
        self.assertNotIn("X-Api-Key", http_session.headers)

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_get_git_environment(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = self.make_addrinfo6(
            "2606:4700:4700::1111"
        ) + self.make_addrinfo("93.184.216.34")

        git_environment = fetch.get_git_environment("http://Example.com:8080/a.git")
        expected = {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "http.followRedirects",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "http.curloptResolve",
            "GIT_CONFIG_VALUE_1": (
                "example.com:8080:[2606:4700:4700::1111],93.184.216.34"
            ),
        }
        self.assertEqual(expected, git_environment)

        mock_getaddrinfo.return_value = self.make_addrinfo("10.0.0.5")
        url = "https://git.internal/repository.git"
        with self.assertRaisesMessage(ValueError, f"Unsafe URL: {url}"):
            fetch.get_git_environment(url)

        with override_settings(SCANPIPE={"ALLOWED_PRIVATE_HOSTS": ["git.internal"]}):
            git_environment = fetch.get_git_environment(url)
        self.assertEqual("1", git_environment["GIT_CONFIG_COUNT"])
        self.assertNotIn("GIT_CONFIG_KEY_1", git_environment)

        for unsupported_url in ["file:///srv/repository.git", "ssh://host/repo.git"]:
            with self.assertRaisesMessage(ValueError, "Unsafe URL"):
                fetch.get_git_environment(unsupported_url)

    @mock.patch("scanpipe.pipes.fetch.socket.getaddrinfo")
    def test_scanpipe_pipes_fetch_get_curl_resolve_entry_rejects_changed_answer(
        self, mock_getaddrinfo
    ):
        # The pinned addresses come from their own validated DNS resolution.
        mock_getaddrinfo.side_effect = [
            self.make_addrinfo("93.184.216.34"),
            self.make_addrinfo("127.0.0.1"),
        ]
        url = "https://rebinding.example/repository.git"
        with self.assertRaisesMessage(ValueError, f"Unsafe URL: {url}"):
            fetch.get_git_environment(url)

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

    def test_scanpipe_pipes_fetch_is_url_safe_for_purl_inference(self):
        supported_urls = [
            "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
            "https://github.com/nexB/scancode-toolkit/archive/v3.1.1.zip",
            "https://files.pythonhosted.org/packages/py2.py3/w/wheel/"
            "wheel-0.29.0-py2.py3-none-any.whl",
        ]
        for url in supported_urls:
            self.assertTrue(fetch.is_url_safe_for_purl_inference(url), msg=url)

        rejected_urls = [
            "https://github.com/a/b/archive/" + "x/" * 24 + "oops",
            "https://github.com/a/b/archive/" + "x%2F" * 24 + "oops",
            "https://pypi.org/packages/" + "a-" * 128 + "a%0A.whl",
            "https://pypi.org/packages/" + "a-" * 128 + "a\n.whl",
            "https://example.com/" + "a" * 512,
        ]
        for url in rejected_urls:
            self.assertFalse(fetch.is_url_safe_for_purl_inference(url), msg=url)

    @mock.patch("packageurl.contrib.url2purl.get_purl")
    def test_scanpipe_pipes_fetch_set_project_purl_from_input_url_unsafe_url(
        self, mock_get_purl
    ):
        project = Project.objects.create(name="purl_from_unsafe_url")
        unsafe_urls = [
            "https://github.com/a/b/archive/" + "x/" * 32 + "oops",
            "https://pypi.org/packages/" + "a-" * 256 + "a%0A.whl",
        ]
        for url in unsafe_urls:
            fetch.set_project_purl_from_input_url(project, [url])
        mock_get_purl.assert_not_called()

    def test_scanpipe_pipes_fetch_set_project_purl_from_input_url_bounded_time(self):
        project = Project.objects.create(name="purl_from_url_bounded_time")
        unsafe_urls = [
            "https://github.com/a/b/archive/" + "x/" * 32 + "oops",
            "https://pypi.org/packages/" + "a-" * 128 + "a%0A.whl",
            "https://pypi.org/packages/" + "a-" * 256 + "a%0A.whl",
        ]
        for url in unsafe_urls:
            start_time = time.monotonic()
            fetch.set_project_purl_from_input_url(project, [url])
            elapsed_seconds = time.monotonic() - start_time
            self.assertLess(elapsed_seconds, 1, msg=url)

        project.refresh_from_db()
        self.assertEqual("", project.purl)

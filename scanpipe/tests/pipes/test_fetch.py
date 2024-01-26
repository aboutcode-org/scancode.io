#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

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
        url = "docker://debian:10.9"

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
            "docker://debian:10.9",
        )
        self.assertEqual(expected, cmd_args[0:6])
        self.assertTrue(cmd_args[-1].endswith("debian_10_9.tar"))

    def test_scanpipe_pipes_fetch_docker_image_string_injection_protection(self):
        url = 'docker://;echo${IFS}"PoC"${IFS}"'
        with self.assertRaises(ValueError) as cm:
            fetch.fetch_docker_image(url)
        self.assertEqual("Invalid Docker reference.", str(cm.exception))

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

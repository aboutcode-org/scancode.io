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

import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.test import override_settings

import requests
from packageurl import PackageURL

from scanpipe.pipes import nix
from scanpipe.tests import make_project


class ScanPipeNixPipesTest(TestCase):
    def setUp(self):
        nix._resolved_nix_image = None
        nix._NIXPKGS_WORKTREE_CACHE.clear()
        self.project = make_project("nix-pipes-test")

    @mock.patch("scanpipe.pipes.nix.verify_commit_in_nixpkgs", return_value=True)
    def test_scanpipe_nix_check_input_and_return_purl(self, mock_verify):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit="
            "1234567890abcdef1234567890abcdef12345678"
        ]

        expected = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit="
            "1234567890abcdef1234567890abcdef12345678"
        )
        self.assertEqual(nix.check_input_and_return_purl(project), expected)
        mock_verify.assert_called_once()

    def test_scanpipe_nix_check_input_and_return_purl_validation(self):
        cases = [
            ([], "Only 1 nix purl is accepted."),
            (
                [
                    "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux",
                    "pkg:nix/nixpkgs/world@2.40.0?system=x86_64-linux",
                ],
                "Only 1 nix purl is accepted.",
            ),
            (["pkg:npm/test@1.0"], "Only nix purl is supported."),
            (
                ["pkg:nix/namespace/hello@2.12.1?system=x86_64-linux"],
                "Only official nixpkgs repository is supported",
            ),
            (
                ["pkg:nix/nixpkgs/hello?system=x86_64-linux"],
                "Version or a 'commit' qualifier is required.",
            ),
            (
                ["pkg:nix/nixpkgs/hello@2.12.1"],
                "The 'system' qualifier is required",
            ),
            (
                ["pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit=bad"],
                "Invalid commit hash",
            ),
            (
                ["pkg:nix/nixpkgs/.hidden@2.12.1?system=x86_64-linux"],
                "Invalid Nix package name",
            ),
            (
                ["pkg:nix/nixpkgs/hello@2.12.1?system=invalid"],
                "Invalid system",
            ),
            (
                ["pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&output=UPPERCASE"],
                "Invalid output",
            ),
        ]
        project = mock.Mock()
        for inputs, expected in cases:
            with self.subTest(expected=expected):
                project.inputsources.all.return_value = inputs
                with self.assertRaisesMessage(ValueError, expected):
                    nix.check_input_and_return_purl(project)

    @mock.patch("scanpipe.pipes.nix.verify_commit_in_nixpkgs", return_value=True)
    def test_scanpipe_nix_purl_qualifiers_reject_trailing_newline(self, mock_verify):
        commit = "1234567890abcdef1234567890abcdef12345678"
        cases = [
            (
                f"pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux%0A&commit={commit}",
                "Invalid system",
            ),
            (
                f"pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
                f"&output=out%0A&commit={commit}",
                "Invalid output",
            ),
            (
                f"pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit={commit}%0A",
                "Invalid commit hash",
            ),
        ]
        project = mock.Mock()
        for purl_str, expected in cases:
            with self.subTest(expected=expected):
                project.inputsources.all.return_value = [purl_str]
                with self.assertRaisesMessage(ValueError, expected):
                    nix.check_input_and_return_purl(project)

    @mock.patch(
        "scanpipe.pipes.nix.verify_commit_in_nixpkgs",
        side_effect=ValueError("Could not verify that commit ..."),
    )
    def test_scanpipe_nix_check_input_purl_verify_unavailable(self, mock_verify):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit="
            "1234567890abcdef1234567890abcdef12345678"
        ]
        with self.assertRaisesMessage(ValueError, "Could not verify"):
            nix.check_input_and_return_purl(project)

    @mock.patch("scanpipe.pipes.nix.verify_commit_in_nixpkgs", return_value=False)
    def test_scanpipe_nix_check_input_purl_not_official(self, mock_verify):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit="
            "1234567890abcdef1234567890abcdef12345678"
        ]
        with self.assertRaisesMessage(ValueError, "not reachable"):
            nix.check_input_and_return_purl(project)

    @mock.patch("scanpipe.pipes.fetch.get_request_session")
    def test_scanpipe_nix_github_api_session(self, mock_get_session):
        mock_session = mock.Mock()
        mock_session.headers = {}
        mock_get_session.return_value = mock_session

        nix._github_api_session()

        mock_get_session.assert_called_once_with("https://api.github.com/")
        self.assertEqual("application/vnd.github+json", mock_session.headers["Accept"])

    @mock.patch("scanpipe.pipes.nix._github_api_session")
    def test_scanpipe_nix_verify_commit_in_nixpkgs(self, mock_session_helper):
        commit = "1234567890abcdef1234567890abcdef12345678"
        mock_session = mock.Mock()
        mock_session_helper.return_value = mock_session

        # Each case: (label, [(status, json_body, links), ...], expected).
        cases = [
            (
                "commit on first trusted branch",
                [
                    (200, {}, {}),
                    (200, {"status": "ahead"}, {}),
                ],
                True,
            ),
            (
                "commit identical to branch tip",
                [
                    (200, {}, {}),
                    (200, {"status": "diverged"}, {}),
                    (200, {"status": "identical"}, {}),
                ],
                True,
            ),
            (
                "backport only on release-23.05",
                [
                    (200, {}, {}),
                    (200, {"status": "diverged"}, {}),  # master
                    (200, {"status": "diverged"}, {}),  # nixos-unstable
                    (200, {"status": "diverged"}, {}),  # nixpkgs-unstable
                    (200, {"status": "diverged"}, {}),  # nixos-unstable-small
                    (200, [{"name": "release-23.05"}], {}),  # branches page 1
                    (200, {"status": "ahead"}, {}),  # compare release-23.05
                ],
                True,
            ),
            (
                "unmerged PR commit (not on any branch)",
                [
                    (200, {}, {}),
                    (200, {"status": "diverged"}, {}),  # master
                    (200, {"status": "behind"}, {}),  # nixos-unstable
                    (200, {"status": "behind"}, {}),  # nixpkgs-unstable
                    (200, {"status": "behind"}, {}),  # nixos-unstable-small
                    (200, [], {}),  # branches page 1 (empty)
                ],
                False,
            ),
            (
                "unknown SHA (404 on existence check)",
                [(404, {}, {})],
                False,
            ),
        ]

        for label, responses, expected in cases:
            with self.subTest(label):
                mock_session.reset_mock()
                mocks = []
                for status_code, json_data, links in responses:
                    mock_response = mock.Mock(status_code=status_code, links=links)
                    mock_response.json.return_value = json_data
                    mocks.append(mock_response)
                mock_session.get.side_effect = mocks
                self.assertEqual(nix.verify_commit_in_nixpkgs(commit), expected)

        # Rate-limited on existence check
        mock_session.reset_mock()
        mock_session.get.side_effect = [mock.Mock(status_code=403, links={})]
        with self.assertRaisesMessage(ValueError, "Could not verify"):
            nix.verify_commit_in_nixpkgs(commit)

        # Network error
        mock_session.reset_mock()
        mock_session.get.side_effect = requests.RequestException("network")
        with self.assertRaisesMessage(ValueError, "Could not verify"):
            nix.verify_commit_in_nixpkgs(commit)

        # Invalid hash
        mock_session_helper.reset_mock()
        for invalid in ("not-a-commit", commit + "\n"):
            self.assertFalse(nix.verify_commit_in_nixpkgs(invalid))
        mock_session_helper.assert_not_called()

    @mock.patch("scanpipe.pipes.nix._github_api_session")
    def test_scanpipe_nix_verify_commit_branches_pagination(self, mock_session_helper):
        commit = "1234567890abcdef1234567890abcdef12345678"
        mock_session = mock.Mock()
        mock_session_helper.return_value = mock_session

        mock_session.get.side_effect = [
            mock.Mock(status_code=200, links={}, json=lambda: {}),
            # Trusted branches: all diverged
            mock.Mock(
                status_code=200, links={}, json=lambda: {"status": "diverged"}
            ),  # master
            mock.Mock(
                status_code=200, links={}, json=lambda: {"status": "diverged"}
            ),  # nixos-unstable
            mock.Mock(
                status_code=200, links={}, json=lambda: {"status": "diverged"}
            ),  # nixpkgs-unstable
            mock.Mock(
                status_code=200, links={}, json=lambda: {"status": "diverged"}
            ),  # nixos-unstable-small

            mock.Mock(
                status_code=200,
                links={"next": {"url": "https://api.github.com/page=2"}},
                json=lambda: [{"name": "release-23.05"}],
            ),
            mock.Mock(
                status_code=200,
                links={},
                json=lambda: [{"name": "release-22.11"}],
            ),
            # Release branches: ancestor only on the last one
            mock.Mock(
                status_code=200, links={}, json=lambda: {"status": "diverged"}
            ),  # release-23.05
            mock.Mock(
                status_code=200, links={}, json=lambda: {"status": "ahead"}
            ),  # release-22.11
        ]

        self.assertTrue(nix.verify_commit_in_nixpkgs(commit))

        requested_urls = [call.args[0] for call in mock_session.get.call_args_list]

        # Second /branches request must have used the Link URL from page 1.
        second_branches_page_url = requested_urls[6]
        self.assertEqual(second_branches_page_url, "https://api.github.com/page=2")

        # Both release branches must have been checked for ancestry,
        # even though release-22.11 only appeared on page 2.
        compare_urls = requested_urls[7:]
        self.assertTrue(any("...release-23.05" in url for url in compare_urls))
        self.assertTrue(any("...release-22.11" in url for url in compare_urls))

    @mock.patch("scanpipe.pipes.nix._github_api_session")
    def test_scanpipe_nix_verify_commit_skips_branches_listing(
        self, mock_session_helper
    ):
        mock_session = mock.Mock()
        mock_session_helper.return_value = mock_session

        mock_session.get.side_effect = [
            mock.Mock(status_code=200, links={}, json=lambda: {}),  # existence
            mock.Mock(
                status_code=200, links={}, json=lambda: {"status": "ahead"}
            ),
        ]

        commit = "1234567890abcdef1234567890abcdef12345678"
        self.assertTrue(nix.verify_commit_in_nixpkgs(commit))

        requested_urls = [call.args[0] for call in mock_session.get.call_args_list]
        self.assertFalse(
            any("/branches" in url for url in requested_urls),
            f"branches listing must not be requested, got: {requested_urls}",
        )

    @mock.patch("scanpipe.pipes.nix.fetch_json_response")
    def test_scanpipe_nix_get_package_data(self, mock_fetch):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        mock_data = {"releases": [{"version": "2.12.1"}]}

        mock_fetch.return_value = mock_data
        self.assertEqual(nix.get_package_data(purl), mock_data)
        mock_fetch.assert_called_once_with("https://search.devbox.sh/v2/pkg?name=hello")

        mock_fetch.side_effect = requests.RequestException("network error")
        with self.assertLogs("scanpipe.pipes.nix", level="WARNING"):
            self.assertIsNone(nix.get_package_data(purl))

    @mock.patch("scanpipe.pipes.nix.fetch_json_response")
    def test_scanpipe_nix_get_package_data_url_encodes_name(self, mock_fetch):
        mock_fetch.return_value = {}
        purl = mock.Mock()
        purl.name = "gtk+"

        nix.get_package_data(purl)

        mock_fetch.assert_called_once_with(
            "https://search.devbox.sh/v2/pkg?name=gtk%2B"
        )

    def test_scanpipe_nix_get_commit_hash_nix_store_path(self):
        data = {
            "releases": [
                {
                    "version": "2.12.1",
                    "platforms": [
                        {
                            "system": "x86_64-linux",
                            "commit_hash": "1234abcd",
                            "outputs": [
                                {
                                    "name": "out",
                                    "path": "/nix/store/aaaaaaa-hello-2.12.1",
                                },
                                {
                                    "name": "debug",
                                    "path": "/nix/store/aaaaaaa-hello-2.12.1-debug",
                                },
                            ],
                        }
                    ],
                }
            ]
        }

        commit, store_path = nix.get_commit_hash_nix_store_path(
            data, "x86_64-linux", "out", "2.12.1", "1234abcd"
        )
        self.assertEqual(commit, "1234abcd")
        self.assertEqual(store_path, "/nix/store/aaaaaaa-hello-2.12.1")

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_get_nix_store_path_with_nix(
        self, mock_run, mock_wt, mock_img
    ):
        mock_run.return_value = mock.Mock(stdout="  /nix/store/evaluated-path-out \n")
        path = nix.get_nix_store_path_with_nix(
            "hello", "x86_64-linux", "out", "1234abcd"
        )
        self.assertEqual(path, "/nix/store/evaluated-path-out")

    @mock.patch("scanpipe.pipes.nix.get_commit_hash_nix_store_path")
    def test_scanpipe_nix_get_nix_store_path(self, mock_get_commit):
        mock_get_commit.return_value = ("1234abcd", "/nix/store/hello-path")
        output_fmt, path, commit = nix.get_nix_store_path(
            data={"releases": []},
            name="hello",
            version="2.12.1",
            system="x86_64-linux",
            commit_hash="1234abcd",
            user_output="",
        )
        self.assertEqual(output_fmt, "debug")
        self.assertEqual(path, "/nix/store/hello-path")
        self.assertEqual(commit, "1234abcd")

        with self.assertRaisesMessage(
            Exception, "Please provide a 'commit' qualifier in the PURL"
        ):
            nix.get_nix_store_path({}, "hello", "2.12.1", "x86_64-linux", "", "")

    def test_scanpipe_nix_nixpkgs_import_expr(self):
        with_worktree = nix._nixpkgs_import_expr(
            "1234abcd", "/worktree", 'system = "x86_64-linux";', "config = {};"
        )
        self.assertIn("import /nixpkgs-local", with_worktree)
        self.assertNotIn("fetchTarball", with_worktree)

        without_worktree = nix._nixpkgs_import_expr(
            "1234abcd", "", 'system = "x86_64-linux";', "config = {};"
        )
        self.assertIn("fetchTarball", without_worktree)
        self.assertIn("1234abcd", without_worktree)

    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    def test_scanpipe_nix_build_nixpkgs_import(self, mock_wt):
        linux_import = nix._build_nixpkgs_import("1234abcd", "x86_64-linux")
        self.assertIn('crossSystem = "x86_64-linux"', linux_import)
        self.assertIn("allowUnsupportedSystem = true", linux_import)

        macos_import = nix._build_nixpkgs_import("1234abcd", "aarch64-darwin")
        self.assertNotIn("crossSystem", macos_import)
        self.assertIn("allowUnsupportedSystem = true", macos_import)

    @mock.patch("scanpipe.pipes.nix.get_narinfo_url")
    def test_scanpipe_nix_get_nix_download_url(self, mock_get_narinfo):
        mock_get_narinfo.return_value = "nar/abc.nar.xz"
        url = nix.get_nix_download_url("/nix/store/hello-2.12.1")
        self.assertEqual(url, "https://cache.nixos.org/nar/abc.nar.xz")

    @mock.patch("scanpipe.pipes.nix.requests.get")
    def test_scanpipe_nix_get_narinfo_url(self, mock_get):
        """200 success, 404 permanent, and 500→200 retry."""
        mock_get.return_value = mock.Mock(
            status_code=200, text="StorePath: /nix/store/xyz\nURL: nar/123.nar.xz"
        )
        self.assertEqual(
            nix.get_narinfo_url("https://cache.nixos.org/test.narinfo"),
            "nar/123.nar.xz",
        )

        mock_get.reset_mock()
        mock_get.return_value = mock.Mock(status_code=404)
        self.assertEqual(
            nix.get_narinfo_url("https://cache.nixos.org/test.narinfo"), ""
        )

        mock_get.reset_mock()
        mock_get.side_effect = [
            mock.Mock(status_code=500, headers={}),
            mock.Mock(status_code=200, text="URL: nar/123.nar.xz"),
        ]
        with mock.patch("scanpipe.pipes.nix.time.sleep") as mock_sleep:
            self.assertEqual(
                nix.get_narinfo_url("https://cache.nixos.org/test.narinfo", retries=2),
                "nar/123.nar.xz",
            )
        mock_sleep.assert_called_once()

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_get_nix_package_metadata(self, mock_run, mock_wt, mock_img):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )

        mock_run.return_value = mock.Mock(
            stdout=(
                '{"license": "GPL-2.0-or-later", '
                '"homepage": "https://gnu.org", "description": "Hello"}'
            )
        )
        self.assertEqual(
            nix.get_nix_package_metadata(purl=purl, commit_hash="1234abcd"),
            {
                "license": "GPL-2.0-or-later",
                "homepage": "https://gnu.org",
                "description": "Hello",
            },
        )

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_get_nix_package_metadata_no_commit(
        self, mock_run, mock_wt, mock_img
    ):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        self.assertEqual(nix.get_nix_package_metadata(purl=purl, commit_hash=""), {})
        mock_run.assert_not_called()

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_get_nix_package_metadata_error_paths(
        self, mock_run, mock_wt, mock_img
    ):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )

        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["docker"], stderr="nix-instantiate: error"
        )
        with self.assertLogs("scanpipe.pipes.nix", level="ERROR"):
            self.assertEqual(
                nix.get_nix_package_metadata(purl=purl, commit_hash="1234abcd"),
                {},
            )

        mock_run.side_effect = None
        mock_run.return_value = mock.Mock(stdout="invalid-json")
        with self.assertLogs("scanpipe.pipes.nix", level="WARNING"):
            self.assertEqual(
                nix.get_nix_package_metadata(purl=purl, commit_hash="1234abcd"),
                {},
            )

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_get_nix_package_metadata_nested_name(
        self, mock_run, _mock_wt, _mock_img
    ):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/haskellPackages.aasam@1.0?system=x86_64-linux"
        )
        mock_run.return_value = mock.Mock(stdout='{"license": "MIT"}')

        nix.get_nix_package_metadata(
            purl=purl,
            commit_hash="1234567890abcdef1234567890abcdef12345678",
        )

        cmd = mock_run.call_args[0][0]
        nix_expression = cmd[cmd.index("-E") + 1]
        self.assertIn(
            'pkgs.lib.getAttrFromPath (pkgs.lib.splitString "." name) pkgs',
            nix_expression,
        )
        self.assertNotIn("pkgs.${name}", nix_expression)

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_get_nix_package_metadata_multiple_licenses(
        self, mock_run, _mock_wt, _mock_img
    ):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        mock_run.return_value = mock.Mock(stdout='{"license": "MIT AND GPL-2.0"}')

        nix.get_nix_package_metadata(purl=purl, commit_hash="1234abcd")

        cmd = mock_run.call_args[0][0]
        nix_expression = cmd[cmd.index("-E") + 1]
        self.assertIn("builtins.concatStringsSep", nix_expression)
        self.assertIn("getLicenseId", nix_expression)
        # The previous single-attrset-only path should be be gone.
        self.assertNotIn(
            "builtins.isAttrs license && license ? spdxId",
            nix_expression,
        )

    def test_scanpipe_nix_create_package_from_nix_metadata(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        metadata = {
            "license": "GPL-2.0-or-later",
            "homepage": "https://gnu.org",
            "description": "Hello program",
        }
        package = nix.create_package_from_nix_metadata(self.project, purl, metadata)
        self.assertEqual(package.type, "nix")
        self.assertEqual(package.namespace, "nixpkgs")
        self.assertEqual(package.name, "hello")
        self.assertEqual(package.version, "2.12.1")
        self.assertEqual(package.declared_license_expression, "gpl-2.0-plus")
        self.assertEqual(package.declared_license_expression_spdx, "GPL-2.0-or-later")

    def test_scanpipe_nix_add_codebase_resources_to_package(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        package = nix.create_package_from_nix_metadata(
            self.project, purl, {"license": "MIT"}
        )

        for path, tag in (
            ("from/a", "from"),
            ("from/b", "from"),
            ("to/c", "to"),
        ):
            self.project.codebaseresources.create(path=path, tag=tag)

        qs = self.project.codebaseresources.filter(path__startswith="from/")
        nix.add_codebase_resources_to_package(package, qs)

        self.assertCountEqual(
            ["from/a", "from/b"],
            package.codebase_resources.values_list("path", flat=True),
        )

        # Second call must not raise nor duplicate rows (ignore_conflicts=True).
        nix.add_codebase_resources_to_package(package, qs)
        self.assertEqual(2, package.codebase_resources.count())

        # Empty queryset is a no-op.
        empty_qs = self.project.codebaseresources.filter(path="does-not-exist")
        nix.add_codebase_resources_to_package(package, empty_qs)
        self.assertEqual(2, package.codebase_resources.count())

    def test_scanpipe_nix_create_package_from_nix_metadata_homepage_list(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        metadata = {
            "license": "MIT",
            "homepage": ["https://first.example.com", "https://second.example.com"],
        }
        package = nix.create_package_from_nix_metadata(self.project, purl, metadata)
        self.assertEqual("https://first.example.com", package.homepage_url)

    def test_scanpipe_nix_create_package_from_nix_metadata_homepage_empty_list(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        metadata = {"license": "MIT", "homepage": []}
        package = nix.create_package_from_nix_metadata(self.project, purl, metadata)
        self.assertEqual("", package.homepage_url)

    def test_scanpipe_nix_create_package_from_nix_metadata_unconvertible_spdx(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        metadata = {
            "license": "InvalidSpdxIdentifier",
            "homepage": "https://example.com",
        }

        package = nix.create_package_from_nix_metadata(self.project, purl, metadata)

        self.assertEqual(
            "InvalidSpdxIdentifier",
            package.declared_license_expression_spdx,
        )
        # Falls back to "unknown" when conversion cannot map the SPDX id to
        # a ScanCode license key.
        self.assertEqual("unknown", package.declared_license_expression)

    @mock.patch("scanpipe.pipes.nix.get_package_data", return_value=None)
    @mock.patch(
        "scanpipe.pipes.nix.get_nix_store_path_with_nix",
        return_value="/nix/store/aaaaaaaaaa",
    )
    @mock.patch("scanpipe.pipes.nix.get_nix_download_url")
    @mock.patch("scanpipe.pipes.nix.get_patched_source_with_docker")
    @mock.patch("scanpipe.pipes.nix.build_binary_with_docker")
    @mock.patch("scanpipe.pipes.fetch.fetch_url")
    def test_scanpipe_nix_fetch_inputs(
        self,
        mock_fetch_url,
        mock_build,
        mock_patched,
        mock_download,
        mock_store,
        mock_pkg,
    ):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux&commit=1234abcd"
        )
        mock_patched.return_value = nix.PatchedSourceResult("/from", False, "", "")

        mock_download.return_value = "https://cache.nixos.org/nar/hello.nar.xz"
        mock_fetch_url.return_value = mock.Mock(path="/to/debug")
        with tempfile.TemporaryDirectory() as tmp:
            src, bin_p, fmt, commit, errs, warns = nix.fetch_inputs(purl, tmp)
        self.assertEqual(
            (src, bin_p, fmt, commit), ("/from", "/to/debug", "debug", "1234abcd")
        )
        self.assertEqual(errs, [])
        mock_fetch_url.assert_called_once()
        mock_build.assert_not_called()

        mock_fetch_url.reset_mock()

        mock_download.return_value = ""
        mock_fetch_url.return_value = None
        mock_build.return_value = ("/built/to", "")
        with tempfile.TemporaryDirectory() as tmp:
            src, bin_p, fmt, commit, errs, warns = nix.fetch_inputs(purl, tmp)
        self.assertEqual(bin_p, "/built/to")
        self.assertTrue(any("Built locally using commit" in m for m in warns))
        mock_build.assert_called_once()

        mock_build.return_value = ("", "build error")
        mock_patched.return_value = nix.PatchedSourceResult(
            "", False, "", "patch error"
        )
        with tempfile.TemporaryDirectory() as tmp:
            src, bin_p, fmt, commit, errs, warns = nix.fetch_inputs(purl, tmp)
        self.assertEqual((src, bin_p), ("", ""))
        self.assertTrue(any("build error" in e for e in errs))
        self.assertTrue(any("patched source" in e.lower() for e in errs))

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_get_patched_source_with_docker(
        self, mock_run, mock_wt, mock_img
    ):
        with tempfile.TemporaryDirectory() as tmp:
            from_dir = Path(tmp) / "from"
            from_dir.mkdir()
            (from_dir / "file").touch()

            mock_run.return_value = mock.Mock(stderr="", returncode=0)
            res = nix.get_patched_source_with_docker(
                "hello", tmp, "x86_64-linux", "1234abcd"
            )
            self.assertEqual(res.path, str(from_dir))
            self.assertFalse(res.used_fallback)

            mock_run.return_value = mock.Mock(
                stderr="PATCHED_SOURCE_FALLBACK_REASON=only env-vars", returncode=0
            )
            res = nix.get_patched_source_with_docker(
                "hello", tmp, "x86_64-linux", "1234abcd"
            )
            self.assertTrue(res.used_fallback)
            self.assertEqual(res.fallback_reason, "only env-vars")

        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["docker"], stderr="error: build failed"
        )
        with tempfile.TemporaryDirectory() as tmp:
            res = nix.get_patched_source_with_docker(
                "hello", tmp, "x86_64-linux", "1234abcd"
            )
        self.assertEqual(res.path, "")
        self.assertIn("error: build failed", res.failure_detail)

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_extract_nar_archive(self, mock_run, mock_img):
        mock_run.return_value = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "hello-bin.nar.xz"
            self.assertEqual(
                nix.extract_nar_archive(str(archive), tmp, "debug"),
                str(Path(tmp).resolve() / "to" / "debug"),
            )

        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["docker"], stderr="restore failed"
        )
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "hello-bin.nar.xz"
            self.assertEqual(nix.extract_nar_archive(str(archive), tmp, "debug"), "")

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image")
    @mock.patch("scanpipe.pipes.nix.shutil.copy2")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_extract_nar_archive_stages_from_tmp(
        self, mock_run_container, mock_copy2, mock_ensure_image
    ):
        """Archive outside output_dir is staged into it before docker run."""
        mock_ensure_image.return_value = "nixos/nix:test"
        mock_run_container.return_value = mock.Mock(returncode=0)

        with (
            tempfile.TemporaryDirectory() as source_dir,
            tempfile.TemporaryDirectory() as output_dir,
        ):
            archive_path = Path(source_dir) / "hello-bin.nar.xz"

            result = nix.extract_nar_archive(
                archive_path=str(archive_path), output_dir=output_dir, output="debug"
            )

            expected_extracted_path = str(Path(output_dir).resolve() / "to" / "debug")
            self.assertEqual(result, expected_extracted_path)

            # Staging must have happened exactly once
            mock_copy2.assert_called_once()
            src, dst = mock_copy2.call_args[0]
            self.assertEqual(Path(src), Path(source_dir).resolve() / "hello-bin.nar.xz")
            self.assertEqual(Path(dst), Path(output_dir).resolve() / "hello-bin.nar.xz")

            # The docker mount source must be output_dir, not the /tmp source
            cmd = mock_run_container.call_args[0][0]
            volume_mounts = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-v"]
            self.assertTrue(
                any(str(Path(output_dir).resolve()) in v for v in volume_mounts),
                f"expected staged mount in {volume_mounts}",
            )
            self.assertFalse(
                any(str(Path(source_dir).resolve()) in v for v in volume_mounts),
                f"unexpected source mount in {volume_mounts}",
            )

    @mock.patch("scanpipe.pipes.nix.extract_nar_archive")
    def test_scanpipe_nix_extract_nar_archive_to_codebase(self, mock_extract):
        with tempfile.TemporaryDirectory() as codebase_dir:
            to_dir = Path(codebase_dir) / "to" / "debug"
            to_dir.mkdir(parents=True)
            (to_dir / "file").touch()
            mock_extract.return_value = str(to_dir)
            success, error = nix.extract_nar_archive_to_codebase(
                Path(tempfile.gettempdir()) / "x.nar", codebase_dir, "debug"
            )
        self.assertTrue(success)
        self.assertEqual(error, "")

        with tempfile.TemporaryDirectory() as codebase_dir:
            to_dir = Path(codebase_dir) / "to"
            to_dir.mkdir(parents=True)
            mock_extract.return_value = str(to_dir)
            success, error = nix.extract_nar_archive_to_codebase(
                Path(tempfile.gettempdir()) / "x.nar", codebase_dir, "debug"
            )
        self.assertFalse(success)
        self.assertIn("Failed to extract NAR archive", error)
        self.assertFalse(to_dir.exists())

    def test_scanpipe_nix_extract_nar_archive_rejects_trailing_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesMessage(ValueError, "Invalid output"):
                nix.extract_nar_archive("x.nar", tmp, "debug\n")

    def test_scanpipe_nix_decompress_pipeline_for(self):
        for filename, expected in [
            ("foo.nar.xz", "xzcat /input/foo.nar.xz"),
            ("foo.nar.zst", "zstdcat /input/foo.nar.zst"),
            ("foo.nar.bz2", "bzcat /input/foo.nar.bz2"),
            ("foo.nar.gz", "zcat /input/foo.nar.gz"),
            ("foo.nar", "cat /input/foo.nar"),
        ]:
            self.assertEqual(nix._decompress_pipeline_for(filename), expected)

    @mock.patch("scanpipe.pipes.nix.shutil.copy2")
    def test_scanpipe_nix_stage_archive(self, mock_copy):
        with (
            tempfile.TemporaryDirectory() as tmp1,
            tempfile.TemporaryDirectory() as tmp2,
        ):
            out_dir = Path(tmp1).resolve()
            src = Path(tmp2).resolve() / "test.nar.xz"
            src.write_bytes(b"data")

            _, staged = nix._stage_archive(out_dir / "test.nar.xz", out_dir)
            self.assertFalse(staged)
            mock_copy.assert_not_called()

            _, staged = nix._stage_archive(src, out_dir)
            self.assertTrue(staged)
            mock_copy.assert_called_once_with(src, out_dir / "test.nar.xz")

            mock_copy.reset_mock()
            (out_dir / "test.nar.xz").write_bytes(b"data")
            _, staged = nix._stage_archive(src, out_dir)
            self.assertFalse(staged)
            mock_copy.assert_not_called()

    @mock.patch("scanpipe.pipes.nix.utils.docker_image_exists")
    @mock.patch("scanpipe.pipes.nix.utils.file_lock")
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_ensure_nix_image(self, mock_run, mock_lock, mock_exists):
        mock_exists.return_value = False
        mock_run.return_value = mock.Mock(returncode=0)
        self.assertEqual(nix._ensure_nix_image(), nix.NIX_IMAGE)
        mock_run.assert_called_once()

    @mock.patch("scanpipe.pipes.nix._nixpkgs_gc_timestamp_path")
    @override_settings(SCANPIPE={"NIXPKGS_GC_INTERVAL_HOURS": 1})
    def test_scanpipe_nixpkgs_gc_due(self, mock_ts):
        now = 10000

        # No timestamp file
        mock_ts.return_value.exists.return_value = False
        self.assertTrue(nix._gc_due(now))

        # Timestamp older than interval
        mock_ts.return_value.exists.return_value = True
        mock_ts.return_value.read_text.return_value = "5000"
        self.assertTrue(nix._gc_due(now))

        # Timestamp within interval
        mock_ts.return_value.read_text.return_value = "9500"
        self.assertFalse(nix._gc_due(now))

        # Corrupt timestamp
        mock_ts.return_value.read_text.return_value = "not-a-number"
        self.assertTrue(nix._gc_due(now))

        # Interval disabled (always not due)
        with override_settings(SCANPIPE={"NIXPKGS_GC_INTERVAL_HOURS": 0}):
            self.assertFalse(nix._gc_due(now))

    @mock.patch("scanpipe.pipes.nix._gc_due", return_value=False)
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_run_nixpkgs_gc_if_due_not_due(self, mock_run, _mock_gc_due):
        nix._run_nixpkgs_gc_if_due()
        mock_run.assert_not_called()

    @mock.patch("scanpipe.pipes.nix._nixpkgs_gc_timestamp_path")
    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix.utils.file_lock")
    @mock.patch("scanpipe.pipes.nix._gc_due", return_value=True)
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    @override_settings(
        SCANPIPE={
            "NIXPKGS_GC_INTERVAL_HOURS": 1,
            "NIXPKGS_GC_OLDER_THAN": "12h",
        }
    )
    def test_scanpipe_nix_run_nixpkgs_gc_if_due_success(
        self, mock_run, _mock_gc_due, _mock_lock, _mock_img, mock_ts
    ):
        mock_run.return_value = mock.Mock(returncode=0)

        nix._run_nixpkgs_gc_if_due()

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("nix-collect-garbage", cmd)
        self.assertIn("--delete-older-than", cmd)
        self.assertIn("12h", cmd)
        self.assertEqual(cmd[0], "docker")

        mock_ts.return_value.write_text.assert_called_once()

    @mock.patch("scanpipe.pipes.nix._nixpkgs_gc_timestamp_path")
    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix.utils.file_lock")
    @mock.patch("scanpipe.pipes.nix._gc_due", return_value=True)
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_run_nixpkgs_gc_if_due_timeout(
        self, mock_run, _mock_gc_due, _mock_lock, _mock_img, mock_ts
    ):
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 1)

        nix._run_nixpkgs_gc_if_due()
        mock_ts.return_value.write_text.assert_not_called()

    @mock.patch("scanpipe.pipes.nix._nixpkgs_gc_timestamp_path")
    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix.utils.file_lock")
    @mock.patch("scanpipe.pipes.nix._gc_due", return_value=True)
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_run_nixpkgs_gc_if_due_timestamp_write_fails(
        self, mock_run, _mock_gc_due, _mock_lock, _mock_img, mock_ts
    ):
        mock_run.return_value = mock.Mock(returncode=0)
        mock_ts.return_value.write_text.side_effect = OSError("read-only")

        nix._run_nixpkgs_gc_if_due()
        mock_run.assert_called_once()

    def test_scanpipe_nix_is_non_linux_system(self):
        self.assertFalse(nix._is_non_linux_system("x86_64-linux"))
        self.assertTrue(nix._is_non_linux_system("aarch64-darwin"))
        self.assertTrue(nix._is_non_linux_system("x86_64-windows"))

    def test_scanpipe_nix_system_barrier_message(self):
        self.assertEqual(nix._system_barrier_message("x86_64-linux"), "")
        self.assertIn(
            "Target system 'aarch64-darwin'",
            nix._system_barrier_message("aarch64-darwin"),
        )

    def test_scanpipe_nix_summarize_nix_build_error(self):
        self.assertEqual(nix._summarize_nix_build_error(""), "")
        self.assertEqual(
            nix._summarize_nix_build_error("first\nsecond\nlast line\n"),
            "last line",
        )
        for stderr, expected in [
            (
                "copying...\nerror: Cannot build '/nix/store/foo.drv'.\nreason",
                "error: Cannot build",
            ),
            (
                "Encountered missing or private dependencies:\n  base\n",
                "Hint: this Haskell package targets an older compiler",
            ),
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, nix._summarize_nix_build_error(stderr))

    @mock.patch("scanpipe.pipes.nix._ensure_nix_image", return_value="nixos/nix:test")
    @mock.patch("scanpipe.pipes.nix._get_nixpkgs_worktree", return_value="")
    @mock.patch("scanpipe.pipes.utils.run_docker_container")
    def test_scanpipe_nix_build_binary_with_docker(self, mock_run, mock_wt, mock_img):
        with tempfile.TemporaryDirectory() as out_dir:
            Path(out_dir, "hello-bin.nar").write_bytes(b"nar")
            mock_run.return_value = mock.Mock(returncode=0)
            path, error = nix.build_binary_with_docker(
                "hello", out_dir, "x86_64-linux", "1234abcd", "debug"
            )
            self.assertEqual(path, str(Path(out_dir) / "hello-bin.nar"))
            self.assertEqual(error, "")
            cmd = mock_run.call_args[0][0]
            mounts = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-v"]
            self.assertTrue(any(":/build_output" in v for v in mounts))

        # Build error
        with tempfile.TemporaryDirectory() as out_dir:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["docker"], stderr="error: builder failed"
            )
            path, error = nix.build_binary_with_docker(
                "hello", out_dir, "x86_64-linux", "1234abcd", "debug"
            )
        self.assertEqual(path, "")
        self.assertIn("error: builder failed", error)

        # Timeout
        with tempfile.TemporaryDirectory() as out_dir:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 1)
            path, error = nix.build_binary_with_docker(
                "hello", out_dir, "x86_64-linux", "1234abcd", "debug"
            )
        self.assertEqual(path, "")
        self.assertIn("timed out", error)

        # Container "succeeded" but produced no .nar.
        with tempfile.TemporaryDirectory() as out_dir:
            mock_run.side_effect = None
            mock_run.return_value = mock.Mock(returncode=0)
            path, error = nix.build_binary_with_docker(
                "hello", out_dir, "x86_64-linux", "1234abcd", "debug"
            )
        self.assertEqual(path, "")
        self.assertIn("did not produce hello-bin.nar", error)

    @mock.patch("scanpipe.pipes.nix.shutil.rmtree")
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    @mock.patch("scanpipe.pipes.nix._nixpkgs_cache_dir")
    def test_scanpipe_nix_clone_nixpkgs_bare_repo(
        self, mock_cache_dir, mock_run, mock_rmtree
    ):
        with tempfile.TemporaryDirectory() as tmp:
            mock_cache_dir.return_value = Path(tmp)

            # Success
            mock_run.return_value = mock.Mock(returncode=0)
            self.assertTrue(nix._clone_nixpkgs_bare_repo().endswith("nixpkgs.git"))
            mock_rmtree.assert_not_called()

            # CalledProcessError
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["git"], stderr="clone failed"
            )
            self.assertEqual(nix._clone_nixpkgs_bare_repo(), "")
            mock_rmtree.assert_any_call(Path(tmp) / "nixpkgs.git", ignore_errors=True)

            # TimeoutExpired
            mock_run.side_effect = subprocess.TimeoutExpired("git", 1)
            self.assertEqual(nix._clone_nixpkgs_bare_repo(), "")
            mock_rmtree.assert_any_call(Path(tmp) / "nixpkgs.git", ignore_errors=True)

    @mock.patch("scanpipe.pipes.nix.shutil.which", return_value="/usr/bin/git")
    @mock.patch("scanpipe.pipes.nix._clone_nixpkgs_bare_repo")
    @mock.patch("scanpipe.pipes.nix._nixpkgs_bare_repo")
    def test_scanpipe_nix_ensure_nixpkgs_bare_repo_already_exists(
        self, mock_bare, mock_clone, mock_which
    ):
        with tempfile.TemporaryDirectory() as tmp:
            mock_bare.return_value = Path(tmp)
            self.assertEqual(nix._ensure_nixpkgs_bare_repo(), tmp)
            mock_clone.assert_not_called()

    @mock.patch("scanpipe.pipes.nix.shutil.which", return_value="/usr/bin/git")
    @mock.patch("scanpipe.pipes.nix.utils.file_lock")
    @mock.patch("scanpipe.pipes.nix._clone_nixpkgs_bare_repo")
    @mock.patch("scanpipe.pipes.nix._nixpkgs_bare_repo")
    def test_scanpipe_nix_ensure_nixpkgs_bare_repo_clones(
        self, mock_bare, mock_clone, mock_lock, mock_which
    ):
        with tempfile.TemporaryDirectory() as tmp:
            mock_bare.return_value = Path(tmp) / "nixpkgs.git"
            mock_clone.return_value = str(mock_bare.return_value)
            self.assertEqual(
                nix._ensure_nixpkgs_bare_repo(), str(mock_bare.return_value)
            )
            mock_clone.assert_called_once()

    @override_settings(SCANPIPE={"NIXPKGS_USE_LOCAL_CACHE": False})
    def test_scanpipe_nix_ensure_nixpkgs_bare_repo_disabled(self):
        self.assertEqual(nix._ensure_nixpkgs_bare_repo(), "")

    @mock.patch("scanpipe.pipes.nix.shutil.which", return_value=None)
    def test_scanpipe_nix_ensure_nixpkgs_bare_repo_no_git(self, mock_which):
        with self.assertLogs("scanpipe.pipes.nix", level="WARNING") as cm:
            self.assertEqual(nix._ensure_nixpkgs_bare_repo(), "")
        self.assertIn("git is not available", cm.output[0])

    def test_scanpipe_nix_prepare_nixpkgs_worktree(self):
        with mock.patch(
            "scanpipe.pipes.nix._ensure_nixpkgs_bare_repo", return_value=""
        ):
            self.assertEqual(nix._prepare_nixpkgs_worktree("abc123"), "")

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)

            # Fetch failure
            with (
                mock.patch(
                    "scanpipe.pipes.nix._nixpkgs_cache_dir", return_value=cache_dir
                ),
                mock.patch("scanpipe.pipes.nix.utils.file_lock"),
                mock.patch(
                    "scanpipe.pipes.nix._ensure_nixpkgs_bare_repo", return_value="/repo"
                ),
                mock.patch("scanpipe.pipes.nix.subprocess.run") as mock_run,
                mock.patch("scanpipe.pipes.nix.shutil.rmtree") as mock_rmtree,
            ):
                mock_run.side_effect = subprocess.CalledProcessError(
                    1, ["git"], stderr="fetch failed"
                )
                self.assertEqual(nix._prepare_nixpkgs_worktree("abc123"), "")
                mock_rmtree.assert_called_once()
                self.assertIn("abc123", str(mock_rmtree.call_args[0][0]))

            with (
                mock.patch(
                    "scanpipe.pipes.nix._nixpkgs_cache_dir", return_value=cache_dir
                ),
                mock.patch("scanpipe.pipes.nix.utils.file_lock"),
                mock.patch(
                    "scanpipe.pipes.nix._ensure_nixpkgs_bare_repo", return_value="/repo"
                ),
                mock.patch(
                    "scanpipe.pipes.nix.subprocess.run",
                    return_value=mock.Mock(returncode=0),
                ),
                mock.patch("scanpipe.pipes.nix.shutil.rmtree") as mock_rmtree,
            ):
                result = nix._prepare_nixpkgs_worktree("abc123")
                self.assertIn("abc123", result)
                mock_rmtree.assert_not_called()

    @mock.patch(
        "scanpipe.pipes.nix._prepare_nixpkgs_worktree", return_value="/new/worktree"
    )
    def test_scanpipe_nix_get_nixpkgs_worktree(self, mock_prepare):
        nix._NIXPKGS_WORKTREE_CACHE["commit-x"] = "/cached/worktree"
        self.assertEqual(nix._get_nixpkgs_worktree("commit-x"), "/cached/worktree")
        mock_prepare.assert_not_called()

        mock_prepare.reset_mock()
        self.assertEqual(nix._get_nixpkgs_worktree("commit-y"), "/new/worktree")
        self.assertEqual(nix._NIXPKGS_WORKTREE_CACHE["commit-y"], "/new/worktree")

    def test_scanpipe_nix_remove_nixpkgs_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch(
                    "scanpipe.pipes.nix._nixpkgs_bare_repo",
                    return_value=Path(tmp) / "does-not-exist",
                ),
                mock.patch("scanpipe.pipes.nix.shutil.rmtree") as mock_rmtree,
                mock.patch("scanpipe.pipes.nix.subprocess.run") as mock_run,
            ):
                nix._remove_nixpkgs_worktree(str(Path(tmp) / "wt"))
                mock_rmtree.assert_called_once_with(
                    str(Path(tmp) / "wt"), ignore_errors=True
                )
                mock_run.assert_not_called()

        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch(
                    "scanpipe.pipes.nix._nixpkgs_bare_repo", return_value=Path(tmp)
                ),
                mock.patch("scanpipe.pipes.nix.utils.file_lock"),
                mock.patch(
                    "scanpipe.pipes.nix.subprocess.run",
                    return_value=mock.Mock(returncode=0),
                ) as mock_run,
                mock.patch("scanpipe.pipes.nix.shutil.rmtree") as mock_rmtree,
            ):
                nix._remove_nixpkgs_worktree(str(Path(tmp) / "wt"))
                mock_run.assert_called_once()
                cmd = mock_run.call_args[0][0]
                self.assertEqual(cmd[:4], ["git", "-C", str(Path(tmp)), "worktree"])
                mock_rmtree.assert_not_called()

    @mock.patch("scanpipe.pipes.nix._remove_nixpkgs_worktree")
    def test_scanpipe_nix_cleanup_nixpkgs_worktrees(self, mock_remove):
        nix._NIXPKGS_WORKTREE_CACHE["a"] = "/wt/a"
        nix._NIXPKGS_WORKTREE_CACHE["b"] = "/wt/b"
        nix.cleanup_nixpkgs_worktrees()
        self.assertEqual(nix._NIXPKGS_WORKTREE_CACHE, {})
        self.assertEqual(mock_remove.call_count, 2)

    @mock.patch("scanpipe.pipes.nix._fetch_or_build_binary", return_value=("", [], []))
    @mock.patch("scanpipe.pipes.nix._fetch_patched_source", return_value=("", [], []))
    @mock.patch("scanpipe.pipes.nix.verify_commit_in_nixpkgs", return_value=True)
    @mock.patch("scanpipe.pipes.nix.get_package_data")
    def test_scanpipe_nix_fetch_inputs_validates_resolved_commit(
        self, mock_pkg, mock_verify, mock_fetch_patched, mock_fetch_bin
    ):
        resolved_commit = "1234567890abcdef1234567890abcdef12345678"
        mock_pkg.return_value = {
            "releases": [
                {
                    "version": "2.12.1",
                    "platforms": [
                        {
                            "system": "x86_64-linux",
                            "commit_hash": resolved_commit,
                            "outputs": [{"name": "debug", "path": "/nix/store/abc"}],
                        }
                    ],
                }
            ]
        }
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.1?system=x86_64-linux"
        )
        with tempfile.TemporaryDirectory() as tmp:
            nix.fetch_inputs(purl, tmp)

        mock_verify.assert_called_once_with(resolved_commit)

    @mock.patch("scanpipe.pipes.nix.verify_commit_in_nixpkgs", return_value=True)
    def test_scanpipe_nix_validate_resolved_commit_hash_official(self, mock_verify):
        commit = "1234567890abcdef1234567890abcdef12345678"
        self.assertEqual(nix._validate_resolved_commit_hash(commit, ""), commit)
        mock_verify.assert_called_once_with(commit)

    @mock.patch("scanpipe.pipes.nix.verify_commit_in_nixpkgs")
    def test_scanpipe_nix_validate_resolved_commit_hash_skips_user_commit(
        self, mock_verify
    ):
        commit = "1234567890abcdef1234567890abcdef12345678"
        self.assertEqual(nix._validate_resolved_commit_hash(commit, commit), commit)
        mock_verify.assert_not_called()

    def test_scanpipe_nix_validate_resolved_commit_hash_empty(self):
        self.assertEqual(nix._validate_resolved_commit_hash("", "abc"), "")

    def test_scanpipe_nix_validate_resolved_commit_hash_invalid_format(self):
        cases = [
            ("not-a-commit", "not a SHA at all"),
            ("1234567890abcdef", "too short"),
            ("1234567890abcdef1234567890abcdef1234567\n", "trailing newline"),
            ("../1234567890abcdef1234567890abcdef1234567", "path traversal"),
        ]
        for invalid, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesMessage(ValueError, "Invalid resolved commit"):
                    nix._validate_resolved_commit_hash(invalid, "")

    @mock.patch("scanpipe.pipes.nix.verify_commit_in_nixpkgs", return_value=False)
    def test_scanpipe_nix_validate_resolved_commit_hash_not_official(self, mock_verify):
        commit = "1234567890abcdef1234567890abcdef12345678"
        with self.assertRaisesMessage(ValueError, "not reachable"):
            nix._validate_resolved_commit_hash(commit, "")

    @mock.patch(
        "scanpipe.pipes.nix.verify_commit_in_nixpkgs",
        side_effect=ValueError("Could not verify that commit ..."),
    )
    def test_scanpipe_nix_validate_resolved_commit_hash_unavailable(self, mock_verify):
        commit = "1234567890abcdef1234567890abcdef12345678"
        with self.assertRaisesMessage(ValueError, "Could not verify"):
            nix._validate_resolved_commit_hash(commit, "")

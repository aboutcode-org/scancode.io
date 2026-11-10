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
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

import requests
from packageurl import PackageURL

from scanpipe.pipes import nix
from scanpipe.tests import make_package
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_file

COMMIT = "55ba7f49ef2962b42cbd126522b7df5f95037679"


def make_response(status_code=200, json_data=None, text="", links=None, headers=None):
    response = mock.Mock(
        status_code=status_code, text=text, links=links or {}, headers=headers or {}
    )
    response.json.return_value = json_data
    return response


class ScanPipeNixPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data" / "nix"

    def setUp(self):
        self.project = make_project()

    @mock.patch("scanpipe.pipes.nix.shutil.which")
    def test_scanpipe_nix_get_missing_commands(self, mock_which):
        def which(command):
            if command != "zstd":
                return f"/usr/bin/{command}"

        mock_which.side_effect = which
        self.assertEqual(["zstd"], nix.get_missing_commands())

    def test_scanpipe_nix_get_nix_purl(self):
        purl = f"pkg:nix/nixpkgs/hello@2.12.3?commit={COMMIT}&system=x86_64-linux"
        self.project.add_input_source(download_url=purl)
        self.assertEqual(PackageURL.from_string(purl), nix.get_nix_purl(self.project))

        self.project.add_input_source(download_url="pkg:nix/nixpkgs/other@1.0")
        with self.assertRaisesMessage(ValueError, "Only 1 Nix PURL is accepted"):
            nix.get_nix_purl(self.project)

    def test_scanpipe_nix_get_binary_group(self):
        self.assertEqual("Elf", nix.get_binary_group(self.project))

        cases = [
            ("pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux", "Elf"),
            ("pkg:nix/nixpkgs/hello@2.12.3?system=aarch64-darwin", "MacOS"),
            ("pkg:nix/nixpkgs/hello@2.12.3", "Elf"),
            ("not a purl", "Elf"),
        ]
        for download_url, expected in cases:
            with self.subTest(download_url=download_url):
                project = make_project()
                project.add_input_source(download_url=download_url)
                self.assertEqual(expected, nix.get_binary_group(project))

    def test_scanpipe_nix_validate_nix_purl(self):
        valid_purls = [
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux",
            f"pkg:nix/nixpkgs/haskellPackages.aeson?system=x86_64-linux&commit={COMMIT}",
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux&output=man",
        ]
        for purl in valid_purls:
            with self.subTest(purl=purl):
                nix.validate_nix_purl(PackageURL.from_string(purl))

        invalid_purls = [
            ("pkg:npm/hello@1.0?system=x86_64-linux", "Only pkg:nix/nixpkgs/"),
            ("pkg:nix/other/hello@1.0?system=x86_64-linux", "Only pkg:nix/nixpkgs/"),
            ("pkg:nix/nixpkgs/.hello@1.0?system=x86_64-linux", "Invalid Nix package"),
            (
                "pkg:nix/nixpkgs/hello@1.0?system=x86_64-linux&outptu=out",
                "Unsupported qualifiers: outptu. The supported qualifiers are: "
                "commit, output, system",
            ),
            (
                "pkg:nix/nixpkgs/hello@1.0?sytem=x86_64-linux&arch=x86",
                "Unsupported qualifiers: arch, sytem.",
            ),
            ("pkg:nix/nixpkgs/hello@1.0", "A valid 'system' qualifier"),
            ("pkg:nix/nixpkgs/hello@1.0?system=x86_64-linux%0A", "A valid 'system'"),
            (
                "pkg:nix/nixpkgs/hello@1.0?system=x86_64-linux&commit=abc",
                "Invalid commit",
            ),
            ("pkg:nix/nixpkgs/hello?system=x86_64-linux", "A version or a 'commit'"),
            (
                "pkg:nix/nixpkgs/hello@1.0?system=x86_64-linux&output=..",
                "Invalid output",
            ),
        ]
        for purl, expected_message in invalid_purls:
            with self.subTest(purl=purl):
                with self.assertRaisesMessage(ValueError, expected_message):
                    nix.validate_nix_purl(PackageURL.from_string(purl))

    @mock.patch("scanpipe.pipes.nix.is_official_nixpkgs_commit")
    @mock.patch("scanpipe.pipes.nix.find_release_commit")
    def test_scanpipe_nix_get_nixpkgs_commit(self, mock_find, mock_official):
        mock_official.return_value = True
        purl = PackageURL.from_string(
            f"pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux&commit={COMMIT}"
        )
        self.assertEqual(COMMIT, nix.get_nixpkgs_commit(purl))
        mock_find.assert_not_called()

        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux"
        )
        mock_find.return_value = COMMIT
        self.assertEqual(COMMIT, nix.get_nixpkgs_commit(purl))

        mock_find.return_value = "not-a-commit"
        with self.assertRaisesMessage(ValueError, "Invalid commit"):
            nix.get_nixpkgs_commit(purl)

        mock_find.return_value = COMMIT
        mock_official.return_value = False
        with self.assertRaisesMessage(ValueError, "is not part of the official"):
            nix.get_nixpkgs_commit(purl)

    @mock.patch("scanpipe.pipes.nix.fetch.get_request_session")
    def test_scanpipe_nix_get_devbox_releases(self, mock_session):
        devbox_data = json.loads((self.data / "devbox-hello.json").read_text())
        mock_session.return_value.get.return_value = make_response(
            json_data=devbox_data
        )
        self.assertEqual(devbox_data["releases"], nix.get_devbox_releases("hello"))
        requested_url = mock_session.return_value.get.call_args.args[0]
        self.assertEqual("https://search.devbox.sh/v2/pkg?name=hello", requested_url)

        mock_session.return_value.get.return_value = make_response(status_code=404)
        self.assertEqual([], nix.get_devbox_releases("unknown"))

    @mock.patch("scanpipe.pipes.nix.get_devbox_releases")
    def test_scanpipe_nix_find_release_commit(self, mock_releases):
        devbox_data = json.loads((self.data / "devbox-hello.json").read_text())
        mock_releases.return_value = devbox_data["releases"]

        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux"
        )
        self.assertEqual(COMMIT, nix.find_release_commit(purl))

        purl = PackageURL.from_string("pkg:nix/nixpkgs/hello@1.0?system=x86_64-linux")
        with self.assertRaisesMessage(ValueError, "No nixpkgs commit found"):
            nix.find_release_commit(purl)

        mock_releases.return_value = []
        purl = PackageURL.from_string("pkg:nix/nixpkgs/unknown@1.0?system=x86_64-linux")
        with self.assertRaisesMessage(ValueError, "No nixpkgs commit found"):
            nix.find_release_commit(purl)

    @mock.patch("scanpipe.pipes.nix.get_release_branches")
    @mock.patch("scanpipe.pipes.nix.is_commit_on_branch")
    @mock.patch("scanpipe.pipes.nix.fetch.get_request_session")
    def test_scanpipe_nix_is_official_nixpkgs_commit(
        self, mock_session, mock_on_branch, mock_release_branches
    ):
        mock_on_branch.return_value = True
        self.assertTrue(nix.is_official_nixpkgs_commit(COMMIT))
        mock_release_branches.assert_not_called()

        def on_release_branch(session, commit, branch):
            return branch == "release-25.05"

        mock_on_branch.side_effect = on_release_branch
        mock_release_branches.return_value = ["release-25.11", "release-25.05"]
        self.assertTrue(nix.is_official_nixpkgs_commit(COMMIT))

        mock_release_branches.return_value = ["release-25.11"]
        self.assertFalse(nix.is_official_nixpkgs_commit(COMMIT))

    def test_scanpipe_nix_check_github_response(self):
        nix.check_github_response(make_response())

        rate_limited_responses = [
            make_response(status_code=403, headers={"x-ratelimit-remaining": "0"}),
            make_response(status_code=429),
        ]
        for response in rate_limited_responses:
            with self.subTest(status_code=response.status_code):
                with self.assertRaisesMessage(
                    requests.HTTPError, "SCANCODEIO_FETCH_HEADERS"
                ):
                    nix.check_github_response(response)
                response.raise_for_status.assert_not_called()

        response = make_response(status_code=500)
        response.raise_for_status.side_effect = requests.HTTPError("500")
        with self.assertRaisesMessage(requests.HTTPError, "500"):
            nix.check_github_response(response)

    def test_scanpipe_nix_is_commit_on_branch(self):
        session = mock.Mock()
        cases = [
            (make_response(json_data={"status": "ahead"}), True),
            (make_response(json_data={"status": "identical"}), True),
            (make_response(json_data={"status": "diverged"}), False),
            (make_response(json_data={"status": "behind"}), False),
            (make_response(status_code=404), False),
        ]
        for response, expected in cases:
            with self.subTest(response=response.json.return_value):
                session.get.return_value = response
                self.assertEqual(
                    expected, nix.is_commit_on_branch(session, COMMIT, "master")
                )

        compare_url = session.get.call_args.args[0]
        expected_url = (
            f"https://api.github.com/repos/NixOS/nixpkgs/compare/{COMMIT}...master"
        )
        self.assertEqual(expected_url, compare_url)

    def test_scanpipe_nix_get_release_branches(self):
        session = mock.Mock()
        session.get.side_effect = [
            make_response(
                json_data=[{"ref": "refs/heads/release-24.11"}],
                links={"next": {"url": "https://api.github.com/page-2"}},
            ),
            make_response(json_data=[{"ref": "refs/heads/release-25.05"}]),
        ]
        self.assertEqual(
            ["release-25.05", "release-24.11"], nix.get_release_branches(session)
        )
        self.assertEqual(
            "https://api.github.com/page-2", session.get.call_args_list[1].args[0]
        )

    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    def test_scanpipe_nix_run_nix_command(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="output", stderr=""
        )
        self.assertEqual("output", nix.run_nix_command(["nix-store", "--gc"], 10))
        self.assertIsNone(mock_run.call_args.kwargs["env"])

        nix.run_nix_command(["nix-build"], 10, cache_directory=Path("/project/tmp"))
        environment = mock_run.call_args.kwargs["env"]
        self.assertEqual("/project/tmp", environment["XDG_CACHE_HOME"])
        self.assertEqual(os.environ["PATH"], environment["PATH"])

        error_lines = [f"line {index}" for index in range(30)]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="\n".join(error_lines)
        )
        with self.assertRaises(nix.NixCommandError) as context:
            nix.run_nix_command(["nix-store", "--gc"], 10)
        self.assertEqual("\n".join(error_lines[-20:]), str(context.exception))

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="nix-build", timeout=10)
        expected_message = "nix-build timed out after 10 seconds"
        with self.assertRaisesMessage(nix.NixCommandError, expected_message):
            nix.run_nix_command(["nix-build"], 10)

    def test_scanpipe_nix_get_nix_expression_arguments(self):
        expected = ["--argstr", "attributePath", "hello", "--argstr", "commit", COMMIT]
        self.assertEqual(expected, nix.get_nix_expression_arguments("hello", COMMIT))

        expected += ["--argstr", "system", "x86_64-linux"]
        self.assertEqual(
            expected, nix.get_nix_expression_arguments("hello", COMMIT, "x86_64-linux")
        )

    @mock.patch("scanpipe.pipes.nix.run_nix_command")
    def test_scanpipe_nix_get_package_metadata(self, mock_run):
        metadata = {
            "version": "2.12.3",
            "description": "Program that produces a familiar, friendly greeting",
            "homepage": "https://www.gnu.org/software/hello/manual/",
            "licenses": ["GPL-3.0-or-later"],
            "outputs": {"out": "/nix/store/5z2yp3ysx8476c8g5w25b0smlgkjvaq3-hello"},
        }
        mock_run.return_value = json.dumps(metadata)

        cache_directory = Path("/project/tmp")
        self.assertEqual(
            metadata,
            nix.get_package_metadata("hello", COMMIT, "x86_64-linux", cache_directory),
        )
        arguments = mock_run.call_args.args[0]
        self.assertEqual(["nix-instantiate", "--eval", "--strict"], arguments[:3])
        self.assertIn("x86_64-linux", arguments)
        self.assertEqual(nix.METADATA_EXPRESSION, arguments[-1])
        self.assertEqual(cache_directory, mock_run.call_args.kwargs["cache_directory"])

    def test_scanpipe_nix_get_selected_outputs(self):
        outputs = {
            "bin": "/nix/store/aaa-curl-bin",
            "dev": "/nix/store/bbb-curl-dev",
            "out": "/nix/store/ccc-curl",
            "man": "/nix/store/ddd-curl-man",
            "devdoc": "/nix/store/eee-curl-devdoc",
            "debug": "/nix/store/fff-curl-debug",
        }
        expected = {
            "bin": "/nix/store/aaa-curl-bin",
            "out": "/nix/store/ccc-curl",
            "debug": "/nix/store/fff-curl-debug",
        }
        self.assertEqual(expected, nix.get_selected_outputs(outputs))

        expected = {"man": "/nix/store/ddd-curl-man"}
        self.assertEqual(expected, nix.get_selected_outputs(outputs, "man"))

        expected_message = (
            "The output 'lib' does not exist, available outputs: "
            "bin, debug, dev, devdoc, man, out"
        )
        with self.assertRaisesMessage(ValueError, expected_message):
            nix.get_selected_outputs(outputs, "lib")

        documentation_outputs = {"dev": "/nix/store/aaa-dev", "doc": "/nix/store/b"}
        self.assertEqual(
            documentation_outputs, nix.get_selected_outputs(documentation_outputs)
        )

    def test_scanpipe_nix_add_metadata_warnings(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux"
        )
        metadata = {"version": "2.12.3", "source_provenance": ["fromSource"]}
        nix.add_metadata_warnings(self.project, purl, COMMIT, metadata)
        self.assertEqual(0, self.project.projectmessages.count())

        metadata = {"version": "2.12.2", "source_provenance": ["binaryNativeCode"]}
        nix.add_metadata_warnings(self.project, purl, COMMIT, metadata)
        warnings = self.project.projectmessages.order_by("created_date")
        expected = [
            "The PURL version 2.12.3 differs from the nixpkgs version 2.12.2 at "
            f"commit {COMMIT}.",
            "The nixpkgs package repackages prebuilt binaries (binaryNativeCode): its "
            "source is not the one of the deployed code.",
        ]
        self.assertEqual(expected, [warning.description for warning in warnings])
        self.assertEqual(
            {"add_metadata_warnings"}, {warning.model for warning in warnings}
        )

    @mock.patch("scanpipe.pipes.nix.fetch_source")
    def test_scanpipe_nix_fetch_codebase_source(self, mock_fetch):
        mock_fetch.return_value = ""
        nix.fetch_codebase_source(self.project, "hello", COMMIT)
        mock_fetch.assert_called_once_with(
            attribute_path="hello",
            commit=COMMIT,
            destination=self.project.codebase_path / "from",
            cache_directory=self.project.tmp_path,
        )
        self.assertEqual(0, self.project.projectmessages.count())

        mock_fetch.return_value = "patch failed"
        nix.fetch_codebase_source(self.project, "hello", COMMIT)
        message = self.project.projectmessages.get()
        self.assertEqual(
            "The source with the nixpkgs patches cannot be built, the upstream "
            "source is used instead.",
            message.description,
        )
        self.assertEqual({"error": "patch failed"}, message.details)
        message.delete()

        mock_fetch.side_effect = nix.NixCommandError("attribute 'src' missing")
        nix.fetch_codebase_source(self.project, "papertrail", COMMIT)
        message = self.project.projectmessages.get()
        self.assertEqual(
            "The source cannot be fetched, the binary is analyzed alone and the "
            "license check is skipped.",
            message.description,
        )
        self.assertEqual("fetch_codebase_source", message.model)
        self.assertEqual({"error": "attribute 'src' missing"}, message.details)

    @mock.patch("scanpipe.pipes.nix.run_nix_command")
    def test_scanpipe_nix_build_source(self, mock_run):
        mock_run.return_value = "warning: unknown setting\n/nix/store/abc-source\n"
        store_path = nix.build_source(nix.PATCHED_SOURCE_EXPRESSION, "hello", COMMIT)
        self.assertEqual("/nix/store/abc-source", store_path)
        self.assertEqual(["nix-build", "--no-out-link"], mock_run.call_args.args[0][:2])

    @mock.patch("scanpipe.pipes.nix.copy_store_path")
    @mock.patch("scanpipe.pipes.nix.build_source")
    def test_scanpipe_nix_fetch_source(self, mock_build, mock_copy):
        destination = Path("/codebase/from")
        mock_build.return_value = "/nix/store/abc-source"
        self.assertEqual("", nix.fetch_source("hello", COMMIT, destination))
        mock_copy.assert_called_once_with("/nix/store/abc-source", destination)

        mock_build.side_effect = [nix.NixCommandError("patch failed"), "/nix/store/src"]
        cache_directory = Path("/project/tmp")
        self.assertEqual(
            "patch failed",
            nix.fetch_source("hello", COMMIT, destination, cache_directory),
        )
        mock_build.assert_called_with(
            nix.UPSTREAM_SOURCE_EXPRESSION, "hello", COMMIT, cache_directory
        )
        mock_copy.assert_called_with("/nix/store/src", destination)

    def test_scanpipe_nix_copy_store_path(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            store_directory = Path(temp_directory) / "abc-source"
            (store_directory / "src").mkdir(parents=True)
            source_file = store_directory / "src" / "hello.c"
            source_file.write_text("int main(void);")
            source_file.chmod(0o444)
            (store_directory / "src").chmod(0o555)

            destination = Path(temp_directory) / "codebase" / "from"
            nix.copy_store_path(store_directory, destination)
            copied_file = destination / "src" / "hello.c"
            self.assertEqual("int main(void);", copied_file.read_text())
            self.assertTrue(os.access(copied_file, os.W_OK))
            self.assertTrue(os.access(destination / "src", os.W_OK))
            (store_directory / "src").chmod(0o755)

            store_archive = Path(temp_directory) / "abc123-hello-2.12.3.tar.gz"
            store_archive.write_bytes(b"archive")
            nix.copy_store_path(store_archive, destination)
            self.assertEqual(
                b"archive", (destination / "hello-2.12.3.tar.gz").read_bytes()
            )

    def test_scanpipe_nix_make_writable(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            directory = Path(temp_directory)
            read_only_file = directory / "file"
            read_only_file.write_text("content")
            read_only_file.chmod(0o444)
            (directory / "link").symlink_to("/does/not/exist")

            nix.make_writable(directory)
            self.assertTrue(os.access(read_only_file, os.W_OK))

    @mock.patch("scanpipe.pipes.nix.fetch.get_request_session")
    def test_scanpipe_nix_get_narinfo(self, mock_session):
        narinfo_text = (self.data / "hello.narinfo").read_text()
        mock_session.return_value.get.return_value = make_response(text=narinfo_text)

        store_path = "/nix/store/5z2yp3ysx8476c8g5w25b0smlgkjvaq3-hello-2.12.3"
        narinfo = nix.get_narinfo(store_path)
        self.assertEqual(
            "nar/1k684wya73qd387kbf1pdpzb986qalk7c7jbnh6ib5846i6q18yc.nar.zst",
            narinfo["URL"],
        )
        self.assertEqual("zstd", narinfo["Compression"])
        requested_url = mock_session.return_value.get.call_args.args[0]
        self.assertEqual(
            "https://cache.nixos.org/5z2yp3ysx8476c8g5w25b0smlgkjvaq3.narinfo",
            requested_url,
        )

        mock_session.return_value.get.return_value = make_response(status_code=404)
        self.assertEqual({}, nix.get_narinfo(store_path))

    @mock.patch("scanpipe.pipes.nix.restore_nar")
    @mock.patch("scanpipe.pipes.nix.download_file")
    @mock.patch("scanpipe.pipes.nix.get_narinfo")
    def test_scanpipe_nix_fetch_binary(self, mock_narinfo, mock_fetch, mock_restore):
        store_path = "/nix/store/5z2yp3ysx8476c8g5w25b0smlgkjvaq3-hello-2.12.3"
        destination = Path("/codebase/to/out")

        mock_narinfo.return_value = {}
        self.assertFalse(nix.fetch_binary(store_path, destination, "/downloads"))
        mock_fetch.assert_not_called()

        with tempfile.TemporaryDirectory() as temp_directory:
            nar_location = (
                Path(temp_directory)
                / "5z2yp3ysx8476c8g5w25b0smlgkjvaq3-hello-2.12.3.nar"
            )

            def download_file(url, file_location):
                file_location.write_bytes(b"nar")

            mock_fetch.side_effect = download_file
            mock_narinfo.return_value = {
                "URL": "nar/abc.nar.zst",
                "Compression": "zstd",
            }

            self.assertTrue(nix.fetch_binary(store_path, destination, temp_directory))
            mock_fetch.assert_called_once_with(
                "https://cache.nixos.org/nar/abc.nar.zst", nar_location
            )
            mock_restore.assert_called_once_with(nar_location, "zstd", destination)
            self.assertFalse(nar_location.exists())

    @mock.patch("scanpipe.pipes.nix.fetch_binary")
    def test_scanpipe_nix_fetch_codebase_binaries(self, mock_fetch):
        selected_outputs = {
            "out": "/nix/store/aaa-hello",
            "debug": "/nix/store/bbb-debug",
        }

        def fetch_binary(store_path, destination, download_directory):
            return store_path.endswith("-hello")

        mock_fetch.side_effect = fetch_binary

        nix.fetch_codebase_binaries(self.project, selected_outputs)
        expected_calls = [
            mock.call(
                store_path=store_path,
                destination=self.project.codebase_path / "to" / output,
                download_directory=self.project.tmp_path,
            )
            for output, store_path in selected_outputs.items()
        ]
        self.assertEqual(expected_calls, mock_fetch.call_args_list)
        message = self.project.projectmessages.get()
        self.assertEqual(
            "Outputs not available in the Nix binary cache: debug",
            message.description,
        )
        self.assertEqual("fetch_codebase_binaries", message.model)

    @mock.patch("scanpipe.pipes.nix.fetch.get_request_session")
    def test_scanpipe_nix_download_file(self, mock_session):
        response = mock.MagicMock()
        response.iter_content.return_value = [b"first ", b"second"]
        mock_session.return_value.get.return_value.__enter__.return_value = response

        with tempfile.TemporaryDirectory() as temp_directory:
            file_location = Path(temp_directory) / "hello.nar"
            nix.download_file("https://cache.nixos.org/nar/abc.nar", file_location)
            self.assertEqual(b"first second", file_location.read_bytes())

        self.assertTrue(mock_session.return_value.get.call_args.kwargs["stream"])
        response.iter_content.assert_called_once_with(
            chunk_size=nix.DOWNLOAD_CHUNK_SIZE
        )

    @mock.patch("scanpipe.pipes.nix.make_writable")
    @mock.patch("scanpipe.pipes.nix.subprocess.run")
    @mock.patch("scanpipe.pipes.nix.subprocess.Popen")
    def test_scanpipe_nix_restore_nar(self, mock_popen, mock_run, mock_writable):
        with tempfile.TemporaryDirectory() as temp_directory:
            nar_location = Path(temp_directory) / "hello.nar.xz"
            nar_location.write_bytes(b"nar")
            destination = Path(temp_directory) / "to" / "out"

            with self.assertRaisesMessage(ValueError, "Unsupported NAR compression"):
                nix.restore_nar(nar_location, "lzip", destination)

            decompress_process = mock_popen.return_value.__enter__.return_value
            decompress_process.returncode = 0
            decompress_process.stderr.read.return_value = b""
            mock_run.return_value = mock.Mock(returncode=0, stderr="")
            nix.restore_nar(nar_location, "xz", destination)
            self.assertEqual(
                ["xz", "--decompress", "--stdout"], mock_popen.call_args.args[0]
            )
            self.assertEqual(
                ["nix-store", "--restore", str(destination)],
                mock_run.call_args.args[0],
            )
            mock_writable.assert_called_once_with(destination)

            mock_run.return_value = mock.Mock(returncode=1, stderr="bad archive")
            with self.assertRaisesMessage(nix.NixCommandError, "bad archive"):
                nix.restore_nar(nar_location, "xz", destination)

            decompress_process.returncode = 1
            decompress_process.stderr.read.return_value = b"xz: Unexpected end"
            mock_run.return_value = mock.Mock(returncode=0, stderr="")
            with self.assertRaisesMessage(nix.NixCommandError, "xz: Unexpected end"):
                nix.restore_nar(nar_location, "xz", destination)

            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="nix-store", timeout=nix.NIX_BUILD_TIMEOUT
            )
            with self.assertRaisesMessage(nix.NixCommandError, "timed out"):
                nix.restore_nar(nar_location, "xz", destination)
            decompress_process.kill.assert_called_once()

    @mock.patch("scanpipe.pipes.nix.run_nix_command")
    def test_scanpipe_nix_collect_garbage(self, mock_run):
        nix.collect_garbage(self.project)
        mock_run.assert_called_once_with(
            ["nix-store", "--gc"], timeout=nix.NIX_BUILD_TIMEOUT
        )
        self.assertEqual(0, self.project.projectmessages.count())

        mock_run.side_effect = nix.NixCommandError("store is locked")
        nix.collect_garbage(self.project)
        message = self.project.projectmessages.get()
        self.assertEqual(
            "The Nix store garbage collection failed.", message.description
        )
        self.assertEqual("collect_garbage", message.model)
        self.assertEqual({"error": "store is locked"}, message.details)

    def test_scanpipe_nix_combine_license_expressions(self):
        cases = [
            ([], ""),
            (["Unlicense OR MIT"], "Unlicense OR MIT"),
            (["Apache-2.0", "MIT"], "Apache-2.0 AND MIT"),
            (
                ["Unlicense OR MIT", "GPL-3.0-or-later"],
                "(Unlicense OR MIT) AND GPL-3.0-or-later",
            ),
        ]
        for license_expressions, expected in cases:
            with self.subTest(license_expressions=license_expressions):
                self.assertEqual(
                    expected, nix.combine_license_expressions(license_expressions)
                )

    def test_scanpipe_nix_convert_nixpkgs_license_expression(self):
        cases = [
            ("Unlicense OR MIT", "unlicense OR mit"),
            (
                "LicenseRef-nixos-unfreeRedistributable",
                "unknown-license-reference",
            ),
            ("MIT AND LicenseRef-nixos-free", "mit AND unknown-license-reference"),
        ]
        for license_expression_spdx, expected in cases:
            with self.subTest(license_expression_spdx=license_expression_spdx):
                self.assertEqual(
                    expected,
                    nix.convert_nixpkgs_license_expression(license_expression_spdx),
                )

    def test_scanpipe_nix_get_vcs_url(self):
        cases = [
            ("", "", ""),
            (
                "https://github.com/psf/requests.git",
                "",
                "git+https://github.com/psf/requests.git",
            ),
            (
                "https://github.com/psf/requests.git",
                "refs/tags/v2.34.2",
                "git+https://github.com/psf/requests.git@v2.34.2",
            ),
            (
                "https://github.com/psf/requests.git",
                COMMIT,
                f"git+https://github.com/psf/requests.git@{COMMIT}",
            ),
        ]
        for git_repository, git_revision, expected in cases:
            with self.subTest(git_revision=git_revision):
                self.assertEqual(
                    expected, nix.get_vcs_url(git_repository, git_revision)
                )

    def test_scanpipe_nix_get_recipe_url(self):
        self.assertEqual("", nix.get_recipe_url("", COMMIT))
        self.assertEqual(
            f"https://github.com/NixOS/nixpkgs/blob/{COMMIT}/"
            "pkgs/by-name/he/hello/package.nix#L58",
            nix.get_recipe_url("pkgs/by-name/he/hello/package.nix:58", COMMIT),
        )

    def test_scanpipe_nix_get_binary_provenances(self):
        self.assertEqual([], nix.get_binary_provenances([]))
        self.assertEqual([], nix.get_binary_provenances(["fromSource"]))
        self.assertEqual(
            ["binaryNativeCode", "binaryFirmware"],
            nix.get_binary_provenances(
                ["fromSource", "binaryNativeCode", "binaryFirmware"]
            ),
        )

    def test_scanpipe_nix_create_nix_package(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux"
        )
        metadata = {
            "version": "2.12.3",
            "description": "Program that produces a familiar, friendly greeting",
            "homepage": ["https://www.gnu.org/software/hello/", "https://other"],
            "licenses": ["GPL-3.0-or-later", "Unlicense OR MIT"],
            "outputs": {},
            "source_urls": [
                "https://github.com/BurntSushi/ripgrep/archive/refs/tags/15.2.0.tar.gz"
            ],
            "git_repository": "https://github.com/BurntSushi/ripgrep.git",
            "git_revision": "refs/tags/15.2.0",
            "recipe_position": "pkgs/by-name/ri/ripgrep/package.nix:66",
            "source_provenance": [],
        }
        package = nix.create_nix_package(self.project, purl, metadata, COMMIT)
        self.assertEqual("pkg:nix/nixpkgs/hello@2.12.3", package.purl)
        self.assertEqual(
            "gpl-3.0-plus AND (unlicense OR mit)", package.declared_license_expression
        )
        self.assertEqual(
            "GPL-3.0-or-later AND (Unlicense OR MIT)",
            package.declared_license_expression_spdx,
        )
        self.assertEqual("https://www.gnu.org/software/hello/", package.homepage_url)
        self.assertEqual(metadata["description"], package.description)
        self.assertEqual(["nixpkgs_meta"], package.datasource_ids)
        self.assertEqual(metadata["source_urls"][0], package.download_url)
        self.assertEqual(
            "git+https://github.com/BurntSushi/ripgrep.git@15.2.0", package.vcs_url
        )
        expected_extra_data = {
            "nixpkgs_commit": COMMIT,
            "nixpkgs_recipe_url": (
                f"https://github.com/NixOS/nixpkgs/blob/{COMMIT}/"
                "pkgs/by-name/ri/ripgrep/package.nix#L66"
            ),
            "system": "x86_64-linux",
        }
        self.assertEqual(expected_extra_data, package.extra_data)

        purl = PackageURL.from_string(
            f"pkg:nix/nixpkgs/zlib?system=x86_64-linux&commit={COMMIT}"
        )
        metadata.update(
            version="1.3.1",
            licenses=[],
            homepage="",
            source_urls=[],
            git_repository="",
            git_revision="",
            recipe_position="",
        )
        package = nix.create_nix_package(self.project, purl, metadata, COMMIT)
        self.assertEqual("1.3.1", package.version)
        self.assertEqual("", package.declared_license_expression)
        self.assertEqual("", package.download_url)
        self.assertEqual("", package.vcs_url)
        self.assertEqual("", package.extra_data["nixpkgs_recipe_url"])

        # The nixpkgs version is the one of the scanned code.
        purl = PackageURL.from_string("pkg:nix/nixpkgs/curl@8.0?system=x86_64-linux")
        metadata.update(version="8.16.0")
        package = nix.create_nix_package(self.project, purl, metadata, COMMIT)
        self.assertEqual("pkg:nix/nixpkgs/curl@8.16.0", package.purl)

    def test_scanpipe_nix_add_resources_to_package(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux"
        )
        metadata = {
            "version": "",
            "description": "",
            "homepage": "",
            "licenses": [],
            "source_urls": [],
            "git_repository": "",
            "git_revision": "",
            "recipe_position": "",
        }
        package = nix.create_nix_package(self.project, purl, metadata, COMMIT)
        make_resource_file(self.project, "from/hello.c")
        make_resource_file(self.project, "to/bin/hello")
        resource_qs = self.project.codebaseresources.files()

        nix.add_resources_to_package(package, resource_qs, batch_size=1)
        self.assertEqual(2, package.codebase_resources.count())

        nix.add_resources_to_package(package, resource_qs)
        self.assertEqual(2, package.codebase_resources.count())

    def test_scanpipe_nix_get_uncovered_license_keys(self):
        resources = [
            ("from/src/hello.c", "gpl-3.0-plus"),
            ("from/lib/helper.c", "mit AND gpl-3.0-plus"),
            ("from/lib/other.c", "mit"),
            ("from/README", "unknown-license-reference"),
            ("to/share/doc/LICENSE", "apache-2.0"),
        ]
        for path, license_expression in resources:
            make_resource_file(
                self.project, path, detected_license_expression=license_expression
            )

        self.assertEqual(
            ["mit"], nix.get_uncovered_license_keys(self.project, "gpl-3.0-plus")
        )
        self.assertEqual(
            [], nix.get_uncovered_license_keys(self.project, "gpl-3.0-plus AND mit")
        )

        # The GPL text of a COPYING file is detected without "or later".
        make_resource_file(
            self.project, "from/COPYING", detected_license_expression="gpl-3.0"
        )
        self.assertEqual(
            ["mit"], nix.get_uncovered_license_keys(self.project, "gpl-3.0-plus")
        )
        self.assertEqual(
            ["mit"], nix.get_uncovered_license_keys(self.project, "gpl-3.0")
        )
        self.assertEqual(
            ["gpl-3.0", "gpl-3.0-plus"],
            nix.get_uncovered_license_keys(self.project, "gpl-2.0-plus AND mit"),
        )

    def test_scanpipe_nix_get_base_license_key(self):
        cases = [
            ("gpl-3.0-plus", "gpl-3.0"),
            ("lgpl-2.1-plus", "lgpl-2.1"),
            ("gpl-3.0", "gpl-3.0"),
            ("m-plus", "m-plus"),
            ("mit", "mit"),
        ]
        for license_key, expected in cases:
            with self.subTest(license_key=license_key):
                self.assertEqual(expected, nix.get_base_license_key(license_key))

    def test_scanpipe_nix_check_package_license(self):
        package = make_package(self.project, "pkg:nix/nixpkgs/hello@2.12.3")
        nix.check_package_license(self.project, package)
        self.assertEqual({}, package.extra_data)
        self.assertEqual(0, self.project.projectmessages.count())

        make_resource_file(
            self.project, "from/src/helper.c", detected_license_expression="mit"
        )
        nix.check_package_license(self.project, package)
        self.assertEqual({}, package.extra_data)
        message = self.project.projectmessages.get()
        self.assertEqual(
            "No declared license in nixpkgs, license check skipped.",
            message.description,
        )
        self.assertEqual("check_package_license", message.model)

        package.update(declared_license_expression="gpl-3.0-plus")
        nix.check_package_license(self.project, package)
        self.assertEqual({"uncovered_licenses": ["mit"]}, package.extra_data)

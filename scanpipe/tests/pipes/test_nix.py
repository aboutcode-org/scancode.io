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

from packageurl import PackageURL

from scanpipe.pipes import flag
from scanpipe.pipes import nix
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_file

COMMIT = "55ba7f49ef2962b42cbd126522b7df5f95037679"


def make_response(status_code=200, json_data=None, text="", links=None):
    response = mock.Mock(status_code=status_code, text=text, links=links or {})
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
    def test_scanpipe_nix_find_release_commit(self, mock_session):
        devbox_data = json.loads((self.data / "devbox-hello.json").read_text())
        mock_session.return_value.get.return_value = make_response(
            json_data=devbox_data
        )

        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux"
        )
        self.assertEqual(COMMIT, nix.find_release_commit(purl))
        requested_url = mock_session.return_value.get.call_args.args[0]
        self.assertEqual("https://search.devbox.sh/v2/pkg?name=hello", requested_url)

        purl = PackageURL.from_string("pkg:nix/nixpkgs/hello@1.0?system=x86_64-linux")
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

        error_lines = [f"line {index}" for index in range(30)]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="\n".join(error_lines)
        )
        with self.assertRaises(nix.NixCommandError) as context:
            nix.run_nix_command(["nix-store", "--gc"], 10)
        self.assertEqual("\n".join(error_lines[-20:]), str(context.exception))

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

        self.assertEqual(
            metadata, nix.get_package_metadata("hello", COMMIT, "x86_64-linux")
        )
        arguments = mock_run.call_args.args[0]
        self.assertEqual(["nix-instantiate", "--eval", "--strict"], arguments[:3])
        self.assertIn("x86_64-linux", arguments)
        self.assertEqual(nix.METADATA_EXPRESSION, arguments[-1])

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
        self.assertEqual("patch failed", nix.fetch_source("hello", COMMIT, destination))
        self.assertEqual(nix.UPSTREAM_SOURCE_EXPRESSION, mock_build.call_args.args[0])
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
    @mock.patch("scanpipe.pipes.nix.fetch.fetch_http")
    @mock.patch("scanpipe.pipes.nix.get_narinfo")
    def test_scanpipe_nix_fetch_binary(self, mock_narinfo, mock_fetch, mock_restore):
        store_path = "/nix/store/5z2yp3ysx8476c8g5w25b0smlgkjvaq3-hello-2.12.3"
        destination = Path("/codebase/to/out")

        mock_narinfo.return_value = {}
        self.assertFalse(nix.fetch_binary(store_path, destination, "/downloads"))
        mock_fetch.assert_not_called()

        with tempfile.TemporaryDirectory() as temp_directory:
            nar_location = Path(temp_directory) / "hello.nar.zst"
            nar_location.write_bytes(b"nar")
            mock_fetch.return_value = mock.Mock(path=nar_location)
            mock_narinfo.return_value = {
                "URL": "nar/abc.nar.zst",
                "Compression": "zstd",
            }

            self.assertTrue(nix.fetch_binary(store_path, destination, temp_directory))
            mock_fetch.assert_called_once_with(
                "https://cache.nixos.org/nar/abc.nar.zst", to=temp_directory
            )
            mock_restore.assert_called_once_with(nar_location, "zstd", destination)
            self.assertFalse(nar_location.exists())

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

            mock_popen.return_value.returncode = 0
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

    def test_scanpipe_nix_get_nix_cache_directory(self):
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "/var/cache"}):
            self.assertEqual(Path("/var/cache/nix"), nix.get_nix_cache_directory())

        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": ""}):
            expected = Path.home() / ".cache" / "nix"
            self.assertEqual(expected, nix.get_nix_cache_directory())

    @mock.patch("scanpipe.pipes.nix.run_nix_command")
    def test_scanpipe_nix_collect_garbage(self, mock_run):
        with tempfile.TemporaryDirectory() as temp_directory:
            tarball_cache = Path(temp_directory) / "nix" / "tarball-cache"
            tarball_cache.mkdir(parents=True)

            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": temp_directory}):
                nix.collect_garbage()

            mock_run.assert_called_once_with(
                ["nix-store", "--gc"], timeout=nix.NIX_BUILD_TIMEOUT
            )
            self.assertFalse((Path(temp_directory) / "nix").exists())

    def test_scanpipe_nix_create_nix_package(self):
        purl = PackageURL.from_string(
            "pkg:nix/nixpkgs/hello@2.12.3?system=x86_64-linux"
        )
        metadata = {
            "version": "2.12.3",
            "description": "Program that produces a familiar, friendly greeting",
            "homepage": ["https://www.gnu.org/software/hello/", "https://other"],
            "licenses": ["GPL-3.0-or-later", "MIT"],
            "outputs": {},
        }
        package = nix.create_nix_package(self.project, purl, metadata)
        self.assertEqual("pkg:nix/nixpkgs/hello@2.12.3", package.purl)
        self.assertEqual("gpl-3.0-plus AND mit", package.declared_license_expression)
        self.assertEqual(
            "GPL-3.0-or-later AND MIT", package.declared_license_expression_spdx
        )
        self.assertEqual("https://www.gnu.org/software/hello/", package.homepage_url)
        self.assertEqual(metadata["description"], package.description)
        self.assertEqual(["nixpkgs_meta"], package.datasource_ids)

        purl = PackageURL.from_string(f"pkg:nix/nixpkgs/zlib?commit={COMMIT}")
        metadata.update(version="1.3.1", licenses=[], homepage="")
        package = nix.create_nix_package(self.project, purl, metadata)
        self.assertEqual("1.3.1", package.version)
        self.assertEqual("", package.declared_license_expression)

    def test_scanpipe_nix_add_resources_to_package(self):
        purl = PackageURL.from_string("pkg:nix/nixpkgs/hello@2.12.3")
        metadata = {"version": "", "description": "", "homepage": "", "licenses": []}
        package = nix.create_nix_package(self.project, purl, metadata)
        make_resource_file(self.project, "from/hello.c")
        make_resource_file(self.project, "to/bin/hello")
        resource_qs = self.project.codebaseresources.files()

        nix.add_resources_to_package(package, resource_qs, batch_size=1)
        self.assertEqual(2, package.codebase_resources.count())

        nix.add_resources_to_package(package, resource_qs)
        self.assertEqual(2, package.codebase_resources.count())

    def test_scanpipe_nix_save_scan_results_keeping_status(self):
        resource = make_resource_file(
            self.project, "from/COPYING", status=flag.NOT_DEPLOYED
        )
        scan_results = {"detected_license_expression": "gpl-3.0-plus"}
        nix.save_scan_results_keeping_status(resource, scan_results, scan_errors=[])

        resource.refresh_from_db()
        self.assertEqual(flag.NOT_DEPLOYED, resource.status)
        self.assertEqual("gpl-3.0-plus", resource.detected_license_expression)

        nix.save_scan_results_keeping_status(resource, {}, scan_errors=["error"])
        self.assertEqual(1, self.project.projectmessages.count())

    @mock.patch("scanpipe.pipes.nix.scancode.scan_resources")
    def test_scanpipe_nix_scan_undeployed_from_files(self, mock_scan):
        make_resource_file(self.project, "from/COPYING", status=flag.NOT_DEPLOYED)
        make_resource_file(self.project, "from/hello.c", status=flag.SCANNED)
        make_resource_file(self.project, "to/COPYING", status=flag.NOT_DEPLOYED)

        nix.scan_undeployed_from_files(self.project)
        scan_kwargs = mock_scan.call_args.kwargs
        scanned_paths = [resource.path for resource in scan_kwargs["resource_qs"]]
        self.assertEqual(["from/COPYING"], scanned_paths)
        self.assertEqual(nix.save_scan_results_keeping_status, scan_kwargs["save_func"])

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

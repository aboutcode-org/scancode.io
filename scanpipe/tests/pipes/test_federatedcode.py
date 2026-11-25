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

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

import git
import saneyaml

from scanpipe import models
from scanpipe.pipes import federatedcode
from scanpipe.tests import make_package


class ScanPipeFederatedCodeTest(TestCase):
    def setUp(self):
        self.project1 = models.Project.objects.create(name="Analysis")

    @patch(
        "scanpipe.pipes.federatedcode.FEDERATEDCODE_GIT_ACCOUNT_URL",
        "https://github.com/test/",
    )
    def test_scanpipe_pipes_federatedcode_get_package_repository(self):
        make_package(
            project=self.project1,
            package_url="pkg:npm/foobar@v1.2.3",
            version="v.1.2.3",
        )
        project_purl = "pkg:npm/foobar@v1.2.3"
        expected_repo_name = "aboutcode-packages-npm-3f1"
        expected_git_repo = "https://github.com/test/aboutcode-packages-npm-3f1.git"
        expected_scan_path = (
            "aboutcode-packages-npm-3f1/npm/foobar/v1.2.3/scancodeio.json"
        )
        repo_name, git_repo, scan_path = federatedcode.get_package_repository(
            project_purl=project_purl
        )

        self.assertEqual(expected_repo_name, repo_name)
        self.assertEqual(expected_git_repo, git_repo)
        self.assertEqual(expected_scan_path, str(scan_path))

    def test_scanpipe_pipes_federatedcode_add_scan_result(self):
        local_dir = tempfile.mkdtemp()
        repo = git.Repo.init(local_dir)

        federatedcode.add_scan_result(
            self.project1, repo, Path("repo/npm/foobar/v1.2.3/scancodeio.json")
        )

        self.assertIn("npm/foobar/v1.2.3/scancodeio.json", repo.untracked_files)
        shutil.rmtree(repo.working_dir)

    def test_scanpipe_pipes_federatedcode_delete_local_clone(self):
        local_dir = tempfile.mkdtemp()
        repo = git.Repo.init(local_dir)
        federatedcode.delete_local_clone(repo)

        self.assertEqual(False, Path(local_dir).exists())

    def test_scanpipe_pipes_federatedcode_write_data_as_yaml(self):
        # create local repo
        local_dir = tempfile.mkdtemp()
        repo = git.Repo.init(local_dir)

        # write data
        data = ["123", "abc", 3]
        federatedcode.write_data_as_yaml(
            base_path=repo.working_dir,
            file_path="test.yml",
            data=data,
        )

        # Check if file was written
        test_file_path = Path(repo.working_dir) / "test.yml"
        self.assertEqual(True, test_file_path.exists())
        with open(test_file_path) as f:
            contents = f.read()
        yml = saneyaml.load(contents)
        expected_results = ["123", "abc", "3"]
        self.assertEqual(expected_results, yml)

        # clean up
        shutil.rmtree(repo.working_dir)

    def test_scanpipe_pipes_federatedcode_is_single_path_segment(self):
        self.assertTrue(federatedcode.is_single_path_segment("v1.2.3"))
        self.assertTrue(federatedcode.is_single_path_segment("1.0..2"))
        self.assertFalse(federatedcode.is_single_path_segment(".."))
        self.assertFalse(federatedcode.is_single_path_segment("."))
        self.assertFalse(federatedcode.is_single_path_segment("../v1.2.3"))
        self.assertFalse(federatedcode.is_single_path_segment("v1.2.3/.."))
        self.assertFalse(federatedcode.is_single_path_segment("/v1.2.3"))

    def test_scanpipe_pipes_federatedcode_get_package_repository_path_traversal(self):
        project_purls = [
            "pkg:npm/foobar@..%2F..%2Fbaz%2Fv1.2.3",
            "pkg:npm/foobar@%2E%2E",
            "pkg:npm/foobar@v1.2.3%2Fextra",
            "pkg:generic/%2E%2E/%2E%2E/foobar@v1.2.3",
            "pkg:generic/foo%2F..%2F..%2Fbar@v1.2.3",
        ]
        for project_purl in project_purls:
            with self.assertRaisesMessage(ValueError, "cannot be used as a scan path"):
                federatedcode.get_package_repository(project_purl=project_purl)

    @patch("scanpipe.pipes.federatedcode.is_available")
    @patch("scanpipe.pipes.federatedcode.is_configured")
    def test_scanpipe_pipes_federatedcode_check_eligibility_version_path(
        self, mock_is_configured, mock_is_available
    ):
        mock_is_configured.return_value = True
        mock_is_available.return_value = True
        self.project1.add_input_source(download_url="https://example.com/foobar.zip")

        self.project1.update(purl="pkg:npm/foobar@v1.2.3")
        federatedcode.check_federatedcode_eligibility(self.project1)

        self.project1.update(purl="pkg:npm/foobar@..%2F..%2Fbaz")
        expected = "Invalid version in Project PURL: it must not be a path."
        with self.assertRaisesMessage(Exception, expected):
            federatedcode.check_federatedcode_eligibility(self.project1)

    def test_scanpipe_pipes_federatedcode_add_scan_result_outside_repository(self):
        local_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, local_dir)
        repo = git.Repo.init(local_dir / "repo")
        outside_dir = local_dir / "outside"

        package_scan_file = Path("repo/../outside/scancodeio.json")
        with self.assertRaisesMessage(ValueError, "outside the repository"):
            federatedcode.add_scan_result(self.project1, repo, package_scan_file)
        self.assertFalse(outside_dir.exists())

        outside_dir.mkdir()
        (local_dir / "repo" / "npm").symlink_to(outside_dir)
        package_scan_file = Path("repo/npm/foobar/v1.2.3/scancodeio.json")
        with self.assertRaisesMessage(ValueError, "outside the repository"):
            federatedcode.add_scan_result(self.project1, repo, package_scan_file)
        self.assertEqual([], list(outside_dir.iterdir()))

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

import json
import tempfile
from pathlib import Path

from django.apps import apps
from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import docker
from scanpipe.pipes.input import copy_inputs
from scanpipe.tests import FIXTURES_REGEN

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipeDockerPipesTest(TestCase):
    data_path = Path(__file__).parent / "data"
    maxDiff = None

    def assertResultsEqual(self, expected_file, results, regen=FIXTURES_REGEN):
        """
        Set `regen` to True to regenerate the expected results.
        """
        if regen:
            expected_file.write_text(results)

        expected_data = expected_file.read_text()
        self.assertEqual(expected_data, results)

    def test_pipes_docker_get_image_data_contains_layers_with_relative_paths(self):
        extract_target = str(Path(tempfile.mkdtemp()) / "tempdir")
        input_tarball = str(self.data_path / "docker-images.tar.gz")

        # Extract the image first
        images, errors = docker.extract_image_from_tarball(
            input_tarball,
            extract_target,
            verify=False,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = self.data_path / "docker-images.tar.gz-expected-data-1.json"
        self.assertResultsEqual(expected_location, results)

        # Extract the layers second
        errors = docker.extract_layers_from_images_to_base_path(
            base_path=extract_target,
            images=images,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = self.data_path / "docker-images.tar.gz-expected-data-2.json"
        self.assertResultsEqual(expected_location, results)

    def test_pipes_docker_tag_whiteout_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(project=p1, name=".wh.filename2")

        docker.tag_whiteout_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("ignored-whiteout", resource2.status)

    def test_pipes_docker_extract_image_from_tarball_with_broken_symlinks(
        self,
    ):
        extract_target = str(Path(tempfile.mkdtemp()) / "tempdir")
        input_tarball = str(self.data_path / "image-with-symlinks/minitag.tar")

        # Extract the image first
        images, errors = docker.extract_image_from_tarball(
            input_tarball,
            extract_target,
            verify=False,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = (
            self.data_path / "image-with-symlinks/minitag.tar-expected-data-1.json"
        )
        self.assertResultsEqual(expected_location, results)

        # Extract the layers second
        errors = docker.extract_layers_from_images_to_base_path(
            base_path=extract_target,
            images=images,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = (
            self.data_path / "image-with-symlinks/minitag.tar-expected-data-2.json"
        )
        self.assertResultsEqual(expected_location, results)

    def test_pipes_docker_get_tarballs_from_inputs(self):
        p1 = Project.objects.create(name="Analysis")
        _, tar = tempfile.mkstemp(suffix=".tar")
        _, tar_gz = tempfile.mkstemp(suffix=".tar.gz")
        _, tgz = tempfile.mkstemp(suffix=".tgz")
        _, zip = tempfile.mkstemp(suffix=".zip")
        _, rar = tempfile.mkstemp(suffix=".rar")
        copy_inputs([tar, tar_gz, tgz, zip, rar], p1.input_path)

        expected_extensions = ("tar", "tar.gz", "tgz")
        tarballs = docker.get_tarballs_from_inputs(project=p1)
        self.assertEqual(3, len(tarballs))
        for path in tarballs:
            self.assertTrue(path.name.endswith(expected_extensions))

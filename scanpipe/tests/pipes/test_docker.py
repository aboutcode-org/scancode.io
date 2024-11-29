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
    data = Path(__file__).parent.parent / "data"
    maxDiff = None

    def assertResultsEqual(self, expected_file, results, regen=FIXTURES_REGEN):
        """Set `regen` to True to regenerate the expected results."""
        if regen:
            expected_file.write_text(results)

        expected_data = expected_file.read_text()
        self.assertEqual(expected_data, results)

    def test_pipes_docker_get_image_data_contains_layers_with_relative_paths(self):
        extract_target = str(Path(tempfile.mkdtemp()) / "tempdir")
        input_tarball = str(self.data / "docker" / "docker-images.tar.gz")

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
            self.data / "docker" / "docker-images.tar.gz-expected-data-1.json"
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
            self.data / "docker" / "docker-images.tar.gz-expected-data-2.json"
        )
        self.assertResultsEqual(expected_location, results)

    def test_pipes_docker_flag_whiteout_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(project=p1, name=".wh.filename2")

        docker.flag_whiteout_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("ignored-whiteout", resource2.status)

    def test_pipes_docker_extract_image_from_tarball_with_broken_symlinks(
        self,
    ):
        extract_target = str(Path(tempfile.mkdtemp()) / "tempdir")
        input_tarball = str(self.data / "image-with-symlinks" / "minitag.tar")

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
            self.data / "image-with-symlinks" / "minitag.tar-expected-data-1.json"
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
            self.data / "image-with-symlinks" / "minitag.tar-expected-data-2.json"
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

    def test_pipes_docker_get_layers_data(self):
        p1 = Project.objects.create(name="Analysis")
        self.assertEqual([], docker.get_layers_data(p1))

        layers = [
            {
                "size": 5855232,
                "author": "Author",
                "comment": "Comment",
                "created": "2022-04-05T00:19:59.790636867Z",
                "layer_id": "4fc242d58285699eca05db3cc7c7122a2b8e014d9481",
                "created_by": "/bin/sh -c #(nop) ADD file:3efb3fd9ff852b5b56e4 in / ",
                "archive_location": "4fc242d58285699eca05db3cc7c712/layer.tar",
            },
            {
                "size": 2876928,
                "author": None,
                "comment": None,
                "created": "2022-04-05T07:50:46.219557029Z",
                "layer_id": "fbd7d5451c694bccb661c80cb52dd44824a8d0947b",
                "created_by": "/bin/sh -c set -eux;",
                "archive_location": "fbd7d5451c694bccb661c80/layer.tar",
            },
        ]
        p1.update_extra_data(
            {
                "images": [
                    {
                        "image_id": "06a4df09d5a34628e72a77999e5daee6cd3",
                        "layers": layers,
                    }
                ]
            }
        )

        layers_data = docker.get_layers_data(p1)
        self.assertEqual(2, len(layers_data))
        self.assertEqual("img-06a4df-layer-01-4fc242", layers_data[0].layer_tag)
        self.assertEqual(5855232, layers_data[0].size)
        self.assertEqual("Author", layers_data[0].author)
        self.assertEqual("Comment", layers_data[0].comment)
        self.assertEqual(layers[0]["archive_location"], layers_data[0].archive_location)

        self.assertEqual("img-06a4df-layer-02-fbd7d5", layers_data[1].layer_tag)
        self.assertEqual(layers[1]["archive_location"], layers_data[1].archive_location)

        from_old_rootfs = {
            "images": {"name": "packageurl-python-main.zip-extract", "distro": {}}
        }
        p1.update_extra_data(from_old_rootfs)
        self.assertEqual([], docker.get_layers_data(p1))

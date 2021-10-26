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

from scanpipe.pipes import docker

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipeDcokerPipesTest(TestCase):
    data_location = Path(__file__).parent / "data"

    def test_docker__get_image_data_contains_layers__with_relative_paths(
        self, regen=False
    ):
        extract_target = str(Path(tempfile.mkdtemp()) / "tempdir")

        input_tarball = str(self.data_location / "docker-images.tar.gz")

        # extract the image first
        images, errors = docker.extract_image_from_tarball(
            input_tarball,
            extract_target,
            verify=False,
        )
        assert not errors

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)

        expected_location = str(
            self.data_location / "docker-images.tar.gz-expected-data-1.json"
        )

        if regen:
            expected = results

            with open(expected_location, "w") as out:
                out.write(expected)
        else:
            with open(expected_location) as inp:
                expected = inp.read()

        self.assertEqual(results, expected)

        # extract the layers second
        errors = docker.extract_layers_from_images_to_base_path(
            base_path=extract_target,
            images=images,
        )
        assert not errors

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)

        expected_location = str(
            self.data_location / "docker-images.tar.gz-expected-data-2.json"
        )
        if regen:
            expected = results

            with open(expected_location, "w") as out:
                out.write(expected)
        else:
            with open(expected_location) as inp:
                expected = inp.read()

        self.assertEqual(results, expected)

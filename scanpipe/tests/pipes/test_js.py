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

from pathlib import Path

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import d2d
from scanpipe.pipes import js
from scanpipe.pipes.input import copy_input
from scanpipe.pipes.input import copy_inputs


class ScanPipeJsTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_pipes_js_sha1(self):
        source_file = self.data_location / "d2d-javascript/from/main.js"
        with open(source_file) as f:
            source_text = f.read()
        result = js.sha1(source_text)
        self.assertEqual("d6bfcf7d1f8a00cc639b3a186a52453d37c52f61", result)

    def test_scanpipe_pipes_js_is_source_mapping_in_minified(self):
        to_input_location = self.data_location / "d2d-javascript" / "to" / "main.js"
        to_dir = (
            self.project1.codebase_path / "to/project.tar.zst-extract/osgi/marketplace/"
            "intelligent robotics platform.lpkg-extract/"
            "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
            "resources/adaptive_media/js"
        )
        to_dir.mkdir(parents=True)
        copy_input(to_input_location, to_dir)
        d2d.collect_and_create_codebase_resources(self.project1)
        to_resource = self.project1.codebaseresources.get(
            path=(
                "to/project.tar.zst-extract/osgi/marketplace/"
                "intelligent robotics platform.lpkg-extract/"
                "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
                "resources/adaptive_media/js/main.js"
            )
        )
        result = js.is_source_mapping_in_minified(to_resource, "main.js.map")
        self.assertEqual(True, result)

    def test_scanpipe_pipes_js_source_content_sha1_list(self):
        to_input_location = self.data_location / "d2d-javascript" / "to" / "main.js.map"
        to_dir = (
            self.project1.codebase_path / "to/project.tar.zst-extract/osgi/marketplace/"
            "intelligent robotics platform.lpkg-extract/"
            "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
            "resources/adaptive_media/js"
        )
        to_dir.mkdir(parents=True)
        copy_input(to_input_location, to_dir)
        d2d.collect_and_create_codebase_resources(self.project1)
        to_resource = self.project1.codebaseresources.get(
            path=(
                "to/project.tar.zst-extract/osgi/marketplace/"
                "intelligent robotics platform.lpkg-extract/"
                "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
                "resources/adaptive_media/js/main.js.map"
            )
        )
        result = js.source_content_sha1_list(to_resource)
        self.assertEqual(["d6bfcf7d1f8a00cc639b3a186a52453d37c52f61"], result)

    def test_scanpipe_pipes_js_get_map_sources(self):
        to_input_location = self.data_location / "d2d-javascript" / "to" / "main.js.map"
        to_dir = (
            self.project1.codebase_path / "to/project.tar.zst-extract/osgi/marketplace/"
            "intelligent robotics platform.lpkg-extract/"
            "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
            "resources/adaptive_media/js"
        )
        to_dir.mkdir(parents=True)
        copy_input(to_input_location, to_dir)
        d2d.collect_and_create_codebase_resources(self.project1)
        to_resource = self.project1.codebaseresources.get(
            path=(
                "to/project.tar.zst-extract/osgi/marketplace/"
                "intelligent robotics platform.lpkg-extract/"
                "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
                "resources/adaptive_media/js/main.js.map"
            )
        )
        result = js.get_map_sources(to_resource)
        self.assertEqual(
            ["src/main/resources/META-INF/adaptive_media/js/main.js"], result
        )

    def test_scanpipe_pipes_js_get_map_sources_content(self):
        to_input_location = self.data_location / "d2d-javascript" / "to" / "main.js.map"
        expected_location = self.data_location / "d2d-javascript" / "from" / "main.js"
        to_dir = (
            self.project1.codebase_path / "to/project.tar.zst-extract/osgi/marketplace/"
            "intelligent robotics platform.lpkg-extract/"
            "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
            "resources/adaptive_media/js"
        )
        to_dir.mkdir(parents=True)
        copy_input(to_input_location, to_dir)
        d2d.collect_and_create_codebase_resources(self.project1)
        to_resource = self.project1.codebaseresources.get(
            path=(
                "to/project.tar.zst-extract/osgi/marketplace/"
                "intelligent robotics platform.lpkg-extract/"
                "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
                "resources/adaptive_media/js/main.js.map"
            )
        )
        expected = open(expected_location, "r").read()
        result = js.get_map_sources_content(to_resource)

        self.assertEqual([expected], result)

    def test_scanpipe_pipes_js_get_minified_resource(self):
        to_dir = (
            self.project1.codebase_path / "to/project.tar.zst-extract/osgi/marketplace/"
            "intelligent robotics platform.lpkg-extract/"
            "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
            "resources/adaptive_media/js"
        )
        to_dir.mkdir(parents=True)
        resource_files = [
            self.data_location / "d2d-javascript" / "to" / "main.js.map",
            self.data_location / "d2d-javascript" / "to" / "main.js",
        ]
        copy_inputs(resource_files, to_dir)

        d2d.collect_and_create_codebase_resources(self.project1)

        map_file = self.project1.codebaseresources.get(
            path=(
                "to/project.tar.zst-extract/osgi/marketplace/"
                "intelligent robotics platform.lpkg-extract/"
                "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
                "resources/adaptive_media/js/main.js.map"
            )
        )

        expected = self.project1.codebaseresources.get(
            path=(
                "to/project.tar.zst-extract/osgi/marketplace/"
                "intelligent robotics platform.lpkg-extract/"
                "com.example.adaptive.media.web-0.0.5.jar-extract/META-INF/"
                "resources/adaptive_media/js/main.js"
            )
        )

        project_files = self.project1.codebaseresources.files().no_status()
        minified_resources = project_files.to_codebase()

        result = js.get_minified_resource(map_file, minified_resources)

        self.assertEqual(expected, result)

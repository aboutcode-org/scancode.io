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

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import get_pipeline_class
from scanpipe.pipelines import get_pipeline_doc
from scanpipe.pipelines import get_pipeline_graph
from scanpipe.pipelines import is_pipeline_subclass
from scanpipe.pipelines.docker import Docker
from scanpipe.pipelines.load_inventory import LoadInventory
from scanpipe.pipelines.root_filesystems import RootFS


class ScanPipePipelinesTest(TestCase):
    docker_pipeline_location = "scanpipe/pipelines/docker.py"
    rootfs_pipeline_location = "scanpipe/pipelines/root_filesystems.py"
    scan_pipeline_location = "scanpipe/pipelines/load_inventory.py"

    def test_scanpipe_pipeline_class_get_project(self):
        project1 = Project.objects.create(name="Analysis")
        project_instance = Pipeline.get_project(project1.name)
        self.assertEqual(project1, project_instance)

    def test_scanpipe_pipeline_class_save_errors_context_manager(self):
        project1 = Project.objects.create(name="Analysis")
        pipeline = Docker(project_name=project1.name)
        self.assertEqual(project1, pipeline.project)

        with pipeline.save_errors(Exception):
            raise Exception("Error message")

        error = project1.projecterrors.get()
        self.assertEqual("Docker", error.model)
        self.assertEqual({}, error.details)
        self.assertEqual("Error message", error.message)
        self.assertIn('raise Exception("Error message")', error.traceback)

    def test_scanpipe_pipelines_is_pipeline_subclass(self):
        self.assertFalse(is_pipeline_subclass(None))
        self.assertFalse(is_pipeline_subclass(Pipeline))
        self.assertTrue(is_pipeline_subclass(Docker))
        self.assertTrue(is_pipeline_subclass(RootFS))
        self.assertTrue(is_pipeline_subclass(LoadInventory))

    def test_scanpipe_pipelines_get_pipeline_class(self):
        pipeline_class = get_pipeline_class(self.docker_pipeline_location)
        self.assertEqual(Docker, pipeline_class)
        pipeline_class = get_pipeline_class(self.rootfs_pipeline_location)
        self.assertEqual(RootFS, pipeline_class)
        pipeline_class = get_pipeline_class(self.scan_pipeline_location)
        self.assertEqual(LoadInventory, pipeline_class)

    def test_scanpipe_pipelines_get_pipeline_doc(self):
        doc = get_pipeline_doc(self.docker_pipeline_location)
        self.assertEqual("A pipeline to analyze a Docker image.", doc)

    def test_scanpipe_pipelines_get_pipeline_graph(self):
        graph = get_pipeline_graph(self.docker_pipeline_location)
        expected = [
            {"name": "extract_images", "doc": "Extract the images from tarballs."},
            {"name": "extract_layers", "doc": "Extract layers from images."},
        ]
        self.assertEqual(expected, graph[0:2])

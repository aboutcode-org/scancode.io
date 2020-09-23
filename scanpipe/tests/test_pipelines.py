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
from scanpipe.pipelines import PipelineGraph
from scanpipe.pipelines import get_pipeline_class
from scanpipe.pipelines import get_pipeline_description
from scanpipe.pipelines import get_pipeline_doc
from scanpipe.pipelines import is_pipeline_subclass
from scanpipe.pipelines.docker import DockerPipeline
from scanpipe.pipelines.root_filesystems import RootfsPipeline
from scanpipe.pipelines.scan_inventory import CollectInventoryFromScanCodeScan


class ScanPipeModelsTest(TestCase):
    docker_pipeline_location = "scanpipe/pipelines/docker.py"
    rootfs_pipeline_location = "scanpipe/pipelines/root_filesystems.py"
    scan_pipeline_location = "scanpipe/pipelines/scan_inventory.py"

    def test_scanpipe_pipeline_class_get_project(self):
        project1 = Project.objects.create(name="Analysis")
        project_instance = Pipeline.get_project(project1.name)
        self.assertEqual(project1, project_instance)

    def test_scanpipe_pipelines_is_pipeline_subclass(self):
        self.assertFalse(is_pipeline_subclass(None))
        self.assertFalse(is_pipeline_subclass(Pipeline))
        self.assertTrue(is_pipeline_subclass(DockerPipeline))
        self.assertTrue(is_pipeline_subclass(RootfsPipeline))
        self.assertTrue(is_pipeline_subclass(CollectInventoryFromScanCodeScan))

    def test_scanpipe_pipelines_get_pipeline_class(self):
        pipeline_class = get_pipeline_class(self.docker_pipeline_location)
        self.assertEqual(DockerPipeline, pipeline_class)
        pipeline_class = get_pipeline_class(self.rootfs_pipeline_location)
        self.assertEqual(RootfsPipeline, pipeline_class)
        pipeline_class = get_pipeline_class(self.scan_pipeline_location)
        self.assertEqual(CollectInventoryFromScanCodeScan, pipeline_class)

    def test_scanpipe_pipelines_get_pipeline_doc(self):
        doc = get_pipeline_doc(self.docker_pipeline_location)
        self.assertEqual("A pipeline to analyze a Docker image.", doc)

    def test_scanpipe_pipelines_get_pipeline_description(self):
        description = get_pipeline_description(self.docker_pipeline_location)
        self.assertIn("executing DockerPipeline for user:", description)
        self.assertIn("A pipeline to analyze a Docker image.", description)
        self.assertIn("Step start", description)
        self.assertIn("Step start", description)
        self.assertIn("Step end", description)
        self.assertIn("Analysis completed.", description)

    def test_scanpipe_pipelines_pipeline_graph_output_dot(self):
        pipeline_class = get_pipeline_class(self.docker_pipeline_location)
        pipeline_graph = PipelineGraph(pipeline_class)
        output_dot = pipeline_graph.output_dot()
        self.assertIn("rankdir=TB;", output_dot)
        self.assertIn("start -> extract_images;", output_dot)
        self.assertIn("tag_not_analyzed_codebase_resources -> end;", output_dot)

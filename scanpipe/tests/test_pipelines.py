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
from scanpipe.pipelines import is_pipeline_subclass
from scanpipe.tests.pipelines.do_nothing import DoNothing
from scanpipe.tests.pipelines.pretty_name import PrettyPipeline


class ScanPipePipelinesTest(TestCase):
    def test_scanpipe_pipeline_class_get_name(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("do_nothing")

        pipeline_class = DoNothing
        pipeline_instance = DoNothing(run)
        self.assertIsNone(pipeline_class.name)
        self.assertIsNone(pipeline_instance.name)
        self.assertEqual("DoNothing", pipeline_class.get_name())
        self.assertEqual("DoNothing", pipeline_instance.get_name())

        pipeline_class = PrettyPipeline
        pipeline_instance = PrettyPipeline(run)
        self.assertEqual("Pretty name", pipeline_class.name)
        self.assertEqual("Pretty name", pipeline_instance.name)
        self.assertEqual("Pretty name", pipeline_class.get_name())
        self.assertEqual("Pretty name", pipeline_instance.get_name())

    def test_scanpipe_pipelines_class_get_doc(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("do_nothing")
        pipeline_class = DoNothing
        pipeline_instance = DoNothing(run)

        expected = "A pipeline that does nothing, in 2 steps."
        self.assertIsNone(pipeline_class.doc)
        self.assertIsNone(pipeline_instance.doc)
        self.assertEqual(expected, pipeline_class.get_doc())
        self.assertEqual(expected, pipeline_instance.get_doc())

        pipeline_class = PrettyPipeline
        pipeline_instance = PrettyPipeline(run)
        expected = "Doc from attribute"
        self.assertEqual(expected, pipeline_class.doc)
        self.assertEqual(expected, pipeline_instance.doc)
        self.assertEqual(expected, pipeline_class.get_doc())
        self.assertEqual(expected, pipeline_instance.get_doc())

    def test_scanpipe_pipelines_class_get_info(self):
        expected = {
            "name": "DoNothing",
            "description": "A pipeline that does nothing, in 2 steps.",
            "steps": [
                {"name": "step1", "doc": "Step1 doc."},
                {"name": "step2", "doc": "Step2 doc."},
            ],
        }
        self.assertEqual(expected, DoNothing.get_info())

    def test_scanpipe_pipeline_class_log(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("do_nothing")
        pipeline = run.make_pipeline_instance()
        pipeline.log("Event1")
        pipeline.log("Event2")

        run.refresh_from_db()
        self.assertIn("Event1", run.log)
        self.assertIn("Event2", run.log)

    def test_scanpipe_pipeline_class_execute(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("do_nothing")
        pipeline = run.make_pipeline_instance()

        exitcode, output = pipeline.execute()
        self.assertEqual(0, exitcode)
        self.assertEqual("", output)

        run.refresh_from_db()
        self.assertIn("Pipeline [DoNothing] starting", run.log)
        self.assertIn("Step [step1] starting", run.log)
        self.assertIn("Step [step1] completed", run.log)
        self.assertIn("Step [step2] starting", run.log)
        self.assertIn("Step [step2] completed", run.log)
        self.assertIn("Pipeline completed", run.log)

    def test_scanpipe_pipeline_class_execute_with_exception(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("raise_exception")
        pipeline = run.make_pipeline_instance()

        exitcode, output = pipeline.execute()
        self.assertEqual(1, exitcode)
        self.assertTrue(output.startswith("Error message"))
        self.assertIn("Traceback:", output)
        self.assertIn("in execute", output)
        self.assertIn("step(self)", output)
        self.assertIn("in raise_exception", output)
        self.assertIn("raise ValueError", output)

        run.refresh_from_db()
        self.assertIn("Pipeline [RaiseException] starting", run.log)
        self.assertIn("Step [raise_exception] starting", run.log)
        self.assertIn("Pipeline failed", run.log)

    def test_scanpipe_pipeline_class_save_errors_context_manager(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("do_nothing")
        pipeline = run.make_pipeline_instance()
        self.assertEqual(project1, pipeline.project)

        with pipeline.save_errors(Exception):
            raise Exception("Error message")

        error = project1.projecterrors.get()
        self.assertEqual("DoNothing", error.model)
        self.assertEqual({}, error.details)
        self.assertEqual("Error message", error.message)
        self.assertIn('raise Exception("Error message")', error.traceback)

    def test_scanpipe_pipelines_is_pipeline_subclass(self):
        self.assertFalse(is_pipeline_subclass(None))
        self.assertFalse(is_pipeline_subclass(Pipeline))
        self.assertTrue(is_pipeline_subclass(DoNothing))
        self.assertTrue(is_pipeline_subclass(PrettyPipeline))

    def test_scanpipe_pipelines_class_get_graph(self):
        expected = [
            {"doc": "Step1 doc.", "name": "step1"},
            {"doc": "Step2 doc.", "name": "step2"},
        ]
        self.assertEqual(expected, DoNothing.get_graph())

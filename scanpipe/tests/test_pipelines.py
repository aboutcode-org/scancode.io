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
import warnings
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.test import tag

from scanpipe.models import Project
from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import is_pipeline
from scanpipe.pipelines import root_filesystems
from scanpipe.pipes import output
from scanpipe.tests.pipelines.do_nothing import DoNothing
from scanpipe.tests.pipelines.steps_as_attribute import StepsAsAttribute


class ScanPipePipelinesTest(TestCase):
    def test_scanpipe_pipeline_class_pipeline_name_attribute(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("do_nothing")
        pipeline_instance = DoNothing(run)
        self.assertEqual("do_nothing", pipeline_instance.pipeline_name)

    def test_scanpipe_pipelines_class_get_info(self):
        expected = {
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
        self.assertIn("Pipeline [do_nothing] starting", run.log)
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
        self.assertIn("Pipeline [raise_exception] starting", run.log)
        self.assertIn("Step [raise_exception_step] starting", run.log)
        self.assertIn("Pipeline failed", run.log)

    def test_scanpipe_pipeline_class_save_errors_context_manager(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("do_nothing")
        pipeline = run.make_pipeline_instance()
        self.assertEqual(project1, pipeline.project)

        with pipeline.save_errors(Exception):
            raise Exception("Error message")

        error = project1.projecterrors.get()
        self.assertEqual("do_nothing", error.model)
        self.assertEqual({}, error.details)
        self.assertEqual("Error message", error.message)
        self.assertIn('raise Exception("Error message")', error.traceback)

    def test_scanpipe_pipelines_is_pipeline(self):
        self.assertFalse(is_pipeline(None))
        self.assertFalse(is_pipeline(Pipeline))
        self.assertTrue(is_pipeline(DoNothing))

        class SubSubClass(DoNothing):
            pass

        self.assertTrue(is_pipeline(SubSubClass))

    def test_scanpipe_pipelines_class_get_graph(self):
        expected = [
            {"doc": "Step1 doc.", "name": "step1"},
            {"doc": "Step2 doc.", "name": "step2"},
        ]
        self.assertEqual(expected, DoNothing.get_graph())

    def test_scanpipe_pipelines_profile_decorator(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("profile_step")
        pipeline_instance = run.make_pipeline_instance()

        exitcode, output = pipeline_instance.execute()
        self.assertEqual(0, exitcode)

        run.refresh_from_db()
        self.assertIn("Profiling results at", run.log)
        self.assertIn("Pipeline completed", run.log)

        self.assertEqual(1, len(project1.output_root))
        output_file = project1.output_root[0]
        self.assertTrue(output_file.startswith("profile-"))
        self.assertTrue(output_file.endswith(".html"))

    def test_scanpipe_pipelines_class_get_steps(self):
        expected = (
            DoNothing.step1,
            DoNothing.step2,
        )
        self.assertEqual(expected, DoNothing.get_steps())

        expected = (StepsAsAttribute.step1,)
        with warnings.catch_warnings(record=True) as caught_warnings:
            self.assertEqual(expected, StepsAsAttribute.get_steps())
            self.assertEquals(len(caught_warnings), 1)
            caught_warning = caught_warnings[0]

        expected = (
            f"Defining ``steps`` as a tuple is deprecated in {StepsAsAttribute} "
            f"Use a ``steps(cls)`` classmethod instead."
        )
        self.assertEqual(expected, str(caught_warning.message))


class RootFSPipelineTest(TestCase):
    def test_scanpipe_rootfs_pipeline_extract_input_files_errors(self):
        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("root_filesystems")
        pipeline_instance = root_filesystems.RootFS(run)

        # Create 2 files in the input/ directory to generate error twice
        project1.move_input_from(tempfile.mkstemp()[1])
        project1.move_input_from(tempfile.mkstemp()[1])
        self.assertEqual(2, len(project1.input_files))

        with mock.patch("scanpipe.pipes.scancode.extract_archive") as extract_archive:
            extract_archive.return_value = ["Error"]
            pipeline_instance.extract_input_files_to_codebase_directory()

        error = project1.projecterrors.get()
        self.assertEqual("Error\nError", error.message)


@tag("slow")
class PipelinesIntegrationTest(TestCase):
    """
    Set of integration tests to ensure the proper output for each built-in Pipelines.
    """

    maxDiff = None
    data_location = Path(__file__).parent / "data"
    exclude_from_diff = [
        "start_timestamp",
        "end_timestamp",
        "date",
        "duration",
        "input",
        "compliance_alert",
        "policy",
        "tool_version",
        "created_date",
        "log",
        "uuid",
        "size",  # directory sizes are OS dependant
        "--json-pp",
        "--processes",
        "--verbose",
    ]

    def _without_keys(self, data, exclude_keys):
        """
        Returns the `data` excluding the provided `exclude_keys`.
        """
        if type(data) == list:
            return [self._without_keys(entry, exclude_keys) for entry in data]

        if type(data) == dict:
            return {
                key: self._without_keys(value, exclude_keys)
                if type(value) in [list, dict]
                else value
                for key, value in data.items()
                if key not in exclude_keys
            }

        return data

    def assertPipelineResultEqual(self, expected_file, result_file, regen=False):
        """
        Set `regen` to True to regenerate the expected results.
        """
        result_json = json.loads(Path(result_file).read_text())
        result_data = self._without_keys(result_json, self.exclude_from_diff)

        if regen:
            expected_file.write_text(json.dumps(result_data, indent=2))

        expected_json = json.loads(expected_file.read_text())
        expected_data = self._without_keys(expected_json, self.exclude_from_diff)

        self.assertEqual(expected_data, result_data)

    def test_scanpipe_scan_package_pipeline_integration_test(self):
        pipeline_name = "scan_package"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data_location / "is-npm-1.0.0.tgz"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, output = pipeline.execute()
        self.assertEqual(0, exitcode, msg=output)

        self.assertEqual(4, project1.codebaseresources.count())
        self.assertEqual(1, project1.discoveredpackages.count())

        scancode_file = project1.get_latest_output(filename="scancode")
        expected_file = self.data_location / "is-npm-1.0.0_scan_package.json"
        self.assertPipelineResultEqual(expected_file, scancode_file, regen=False)

        summary_file = project1.get_latest_output(filename="summary")
        expected_file = self.data_location / "is-npm-1.0.0_scan_package_summary.json"
        self.assertPipelineResultEqual(expected_file, summary_file, regen=False)

    def test_scanpipe_scan_codebase_pipeline_integration_test(self):
        pipeline_name = "scan_codebase"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data_location / "is-npm-1.0.0.tgz"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, _ = pipeline.execute()
        self.assertEqual(0, exitcode)

        self.assertEqual(6, project1.codebaseresources.count())
        self.assertEqual(1, project1.discoveredpackages.count())

        result_file = output.to_json(project1)
        expected_file = self.data_location / "is-npm-1.0.0_scan_codebase.json"
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

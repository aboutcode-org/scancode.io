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
import os
import sys
import tempfile
import warnings
from pathlib import Path
from unittest import mock
from unittest import skipIf

from django.test import TestCase
from django.test import tag

from scancode.cli_test_utils import purl_with_fake_uuid

from scanpipe.models import Project
from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import is_pipeline
from scanpipe.pipelines import root_filesystems
from scanpipe.pipes import output
from scanpipe.tests.pipelines.do_nothing import DoNothing
from scanpipe.tests.pipelines.steps_as_attribute import StepsAsAttribute

from_docker_image = os.environ.get("FROM_DOCKER_IMAGE")


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

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode)
        self.assertEqual("", out)

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

        exitcode, out = pipeline.execute()
        self.assertEqual(1, exitcode)
        self.assertTrue(out.startswith("Error message"))
        self.assertIn("Traceback:", out)
        self.assertIn("in execute", out)
        self.assertIn("step(self)", out)
        self.assertIn("in raise_exception", out)
        self.assertIn("raise ValueError", out)

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

        exitcode, out = pipeline_instance.execute()
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


def sort_scanned_files_by_path(scan_data):
    """
    Sort the ``scan_data`` files in place. Return ``scan_data``.
    """
    files = scan_data.get("files")
    if files:
        files.sort(key=lambda x: x["path"])
    return scan_data


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
        # system_environment differs between systems
        "system_environment",
        "file_type",
        # mime type is inconsistent across systems
        "mime_type",
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

    def _normalize_package_uids(self, data):
        """
        Returns the `data`, where any `package_uid` value has been normalized
        with `purl_with_fake_uuid()`
        """
        if type(data) == list:
            return [self._normalize_package_uids(entry) for entry in data]

        if type(data) == dict:
            normalized_data = {}
            for key, value in data.items():
                if type(value) in [list, dict]:
                    value = self._normalize_package_uids(value)
                if (
                    key in ("package_uid", "dependency_uid", "for_package_uid")
                    and value
                ):
                    value = purl_with_fake_uuid(value)
                if key == "for_packages":
                    value = [purl_with_fake_uuid(package_uid) for package_uid in value]
                normalized_data[key] = value
            return normalized_data

        return data

    def assertPipelineResultEqual(self, expected_file, result_file, regen=False):
        """
        Set `regen` to True to regenerate the expected results.
        """
        result_json = json.loads(Path(result_file).read_text())
        result_json = self._normalize_package_uids(result_json)
        result_data = self._without_keys(result_json, self.exclude_from_diff)
        result_data = sort_scanned_files_by_path(result_data)

        if regen:
            expected_file.write_text(json.dumps(result_data, indent=2))

        expected_json = json.loads(expected_file.read_text())
        expected_json = self._normalize_package_uids(expected_json)
        expected_data = self._without_keys(expected_json, self.exclude_from_diff)
        expected_data = sort_scanned_files_by_path(expected_data)

        self.assertEqual(expected_data, result_data)

    @skipIf(from_docker_image, "Random failure in the Docker context.")
    def test_scanpipe_scan_package_pipeline_integration_test(self):
        pipeline_name = "scan_package"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data_location / "is-npm-1.0.0.tgz"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(4, project1.codebaseresources.count())
        self.assertEqual(1, project1.discoveredpackages.count())

        scancode_file = project1.get_latest_output(filename="scancode")
        expected_file = self.data_location / "is-npm-1.0.0_scan_package.json"
        self.assertPipelineResultEqual(expected_file, scancode_file, regen=False)

        summary_file = project1.get_latest_output(filename="summary")
        expected_file = self.data_location / "is-npm-1.0.0_scan_package_summary.json"
        self.assertPipelineResultEqual(expected_file, summary_file, regen=False)

        # Ensure that we only have one instance of is-npm in `key_files_packages`
        summary_data = json.loads(Path(summary_file).read_text())
        key_files_packages = summary_data.get("key_files_packages", [])
        self.assertEqual(1, len(key_files_packages))
        key_file_package = key_files_packages[0]
        key_file_package_purl = key_file_package.get("purl", "")
        self.assertEqual("pkg:npm/is-npm@1.0.0", key_file_package_purl)

    @skipIf(from_docker_image, "Random failure in the Docker context.")
    def test_scanpipe_scan_package_pipeline_integration_test_multiple_packages(self):
        pipeline_name = "scan_package"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data_location / "multiple-is-npm-1.0.0.tar.gz"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(9, project1.codebaseresources.count())
        self.assertEqual(2, project1.discoveredpackages.count())

        scancode_file = project1.get_latest_output(filename="scancode")
        expected_file = self.data_location / "multiple-is-npm-1.0.0_scan_package.json"
        self.assertPipelineResultEqual(expected_file, scancode_file, regen=False)

        summary_file = project1.get_latest_output(filename="summary")
        expected_file = (
            self.data_location / "multiple-is-npm-1.0.0_scan_package_summary.json"
        )
        self.assertPipelineResultEqual(expected_file, summary_file, regen=False)

    def test_scanpipe_scan_codebase_pipeline_integration_test(self):
        pipeline_name = "scan_codebase"
        project1 = Project.objects.create(name="Analysis")

        filename = "is-npm-1.0.0.tgz"
        input_location = self.data_location / "is-npm-1.0.0.tgz"
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(6, project1.codebaseresources.count())
        self.assertEqual(1, project1.discoveredpackages.count())

        result_file = output.to_json(project1)
        expected_file = self.data_location / "is-npm-1.0.0_scan_codebase.json"
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_docker_pipeline_alpine_integration_test(self):
        pipeline_name = "docker"
        project1 = Project.objects.create(name="Analysis")

        filename = "alpine_3_15_4.tar.gz"
        input_location = self.data_location / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        result_file = output.to_json(project1)
        expected_file = self.data_location / "alpine_3_15_4_scan_codebase.json"
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_docker_pipeline_does_not_report_errors_for_broken_symlinks(self):
        pipeline_name = "docker"
        project1 = Project.objects.create(name="Analysis")

        filename = "minitag.tar"
        input_location = self.data_location / "image-with-symlinks" / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        project_errors = [pe.message for pe in project1.projecterrors.all()]
        self.assertEqual(1, len(project_errors))
        self.assertEqual("Distro not found.", project_errors[0])

        result_file = output.to_json(project1)
        expected_file = (
            self.data_location
            / "image-with-symlinks"
            / (filename + "-expected-scan.json")
        )
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    @skipIf(sys.platform != "linux", "RPM related features only supported on Linux.")
    def test_scanpipe_docker_pipeline_rpm_integration_test(self):
        pipeline_name = "docker"
        project1 = Project.objects.create(name="Analysis")

        filename = "centos.tar.gz"
        input_location = self.data_location / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(25, project1.codebaseresources.count())
        self.assertEqual(101, project1.discoveredpackages.count())

        result_file = output.to_json(project1)
        expected_file = self.data_location / "centos_scan_codebase.json"
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_docker_pipeline_debian_integration_test(self):
        pipeline_name = "docker"
        project1 = Project.objects.create(name="Analysis")

        filename = "debian.tar.gz"
        input_location = self.data_location / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(6, project1.codebaseresources.count())
        self.assertEqual(2, project1.discoveredpackages.count())

        result_file = output.to_json(project1)
        expected_file = self.data_location / "debian_scan_codebase.json"
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_docker_pipeline_debian_mini_license_integration_test(self):
        pipeline_name = "docker"
        project1 = Project.objects.create(name="Analysis")

        filename = "docker-mini-with-license-debian.tar.xz"
        input_location = self.data_location / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        result_file = output.to_json(project1)
        expected_file = (
            self.data_location
            / "docker-mini-with-license-debian.tar.xz-docker-scan.json"
        )
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_docker_pipeline_alpine_mini_license_integration_test(self):
        pipeline_name = "docker"
        project1 = Project.objects.create(name="Analysis")

        filename = "docker-mini-with-license-alpine.tar.xz"
        input_location = self.data_location / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        result_file = output.to_json(project1)
        expected_file = (
            self.data_location
            / "docker-mini-with-license-alpine.tar.xz-docker-scan.json"
        )
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_docker_pipeline_distroless_debian_integration_test(self):
        pipeline_name = "docker"
        project1 = Project.objects.create(name="Analysis")

        filename = "gcr_io_distroless_base.tar.gz"
        input_location = self.data_location / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename, "https://download.url", save=True)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        result_file = output.to_json(project1)
        expected_file = self.data_location / "gcr_io_distroless_base_scan_codebase.json"
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_rootfs_pipeline_integration_test(self):
        pipeline_name = "root_filesystems"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data_location / "basic-rootfs.tar.gz"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(6, project1.codebaseresources.count())
        self.assertEqual(2, project1.discoveredpackages.count())

        result_file = output.to_json(project1)
        expected_file = self.data_location / "basic-rootfs_root_filesystems.json"
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

    def test_scanpipe_load_inventory_pipeline_integration_test(self):
        pipeline_name = "load_inventory"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data_location / "asgiref-3.3.0_scancode_scan.json"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(18, project1.codebaseresources.count())
        self.assertEqual(2, project1.discoveredpackages.count())

        result_file = output.to_json(project1)
        expected_file = (
            self.data_location / "asgiref-3.3.0_load_inventory_expected.json"
        )
        self.assertPipelineResultEqual(expected_file, result_file, regen=False)

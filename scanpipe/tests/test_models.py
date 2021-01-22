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
import io
import tempfile
import uuid
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import TransactionTestCase
from django.utils import timezone

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.pipelines import get_pipeline_doc
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1

scanpipe_app_config = apps.get_app_config("scanpipe")


class ScanPipeModelsTest(TestCase):
    data_location = Path(__file__).parent / "data"
    fixtures = [data_location / "asgiref-3.3.0_fixtures.json"]

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project_asgiref = Project.objects.get(name="asgiref")

    def create_run(self, **kwargs):
        return Run.objects.create(project=self.project1, pipeline="pipeline", **kwargs)

    def test_scanpipe_project_model_extra_data(self):
        self.assertEqual({}, self.project1.extra_data)
        project1_from_db = Project.objects.get(name=self.project1.name)
        self.assertEqual({}, project1_from_db.extra_data)

    def test_scanpipe_project_model_work_directories(self):
        expected_work_directory = (
            f"projects/{self.project1.name}-{self.project1.short_uuid}"
        )
        self.assertTrue(self.project1.work_directory.endswith(expected_work_directory))
        self.assertTrue(self.project1.work_path.exists())
        self.assertTrue(self.project1.input_path.exists())
        self.assertTrue(self.project1.output_path.exists())
        self.assertTrue(self.project1.codebase_path.exists())
        self.assertTrue(self.project1.tmp_path.exists())

    def test_scanpipe_project_model_clear_tmp_directory(self):
        new_file_path = self.project1.tmp_path / "file.ext"
        new_file_path.touch()
        self.assertEqual([new_file_path], list(self.project1.tmp_path.glob("*")))

        self.project1.clear_tmp_directory()
        self.assertTrue(self.project1.tmp_path.exists())
        self.assertEqual([], list(self.project1.tmp_path.glob("*")))

    def test_scanpipe_project_model_inputs_and_input_files_and_input_root(self):
        self.assertEqual([], list(self.project1.inputs()))
        self.assertEqual([], self.project1.input_files)
        self.assertEqual([], self.project1.input_root)

        new_file_path1 = self.project1.input_path / "file.ext"
        new_file_path1.touch()

        new_dir1 = self.project1.input_path / "dir1"
        new_dir1.mkdir(parents=True, exist_ok=True)
        new_file_path2 = new_dir1 / "file2.ext"
        new_file_path2.touch()

        inputs = list(self.project1.inputs())
        expected = [new_dir1, new_file_path1, new_file_path2]
        self.assertEqual(sorted(expected), sorted(inputs))

        expected = ["file.ext", "dir1/file2.ext"]
        self.assertEqual(sorted(expected), sorted(self.project1.input_files))

        expected = ["dir1", "file.ext"]
        self.assertEqual(sorted(expected), sorted(self.project1.input_root))

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_project_model_get_output_file_path(self):
        filename = self.project1.get_output_file_path("file", "ext")
        self.assertTrue(str(filename).endswith("/output/file-2010-10-10-10-10-10.ext"))

    def test_scanpipe_project_model_add_input_file(self):
        self.assertEqual([], self.project1.input_files)

        uploaded_file = SimpleUploadedFile("file.ext", content=b"content")
        self.project1.add_input_file(uploaded_file)

        self.assertEqual(["file.ext"], self.project1.input_files)

    def test_scanpipe_project_model_copy_input_from(self):
        self.assertEqual([], self.project1.input_files)

        _, input_location = tempfile.mkstemp()
        input_filename = Path(input_location).name

        self.project1.copy_input_from(input_location)
        self.assertEqual([input_filename], self.project1.input_files)
        self.assertTrue(Path(input_location).exists())

    def test_scanpipe_project_model_move_input_from(self):
        self.assertEqual([], self.project1.input_files)

        _, input_location = tempfile.mkstemp()
        input_filename = Path(input_location).name

        self.project1.move_input_from(input_location)
        self.assertEqual([input_filename], self.project1.input_files)
        self.assertFalse(Path(input_location).exists())

    def test_scanpipe_project_model_get_next_run(self):
        self.assertEqual(None, self.project1.get_next_run())

        run1 = self.create_run()
        run2 = self.create_run()
        self.assertEqual(run1, self.project1.get_next_run())

        run1.task_start_date = timezone.now()
        run1.save()
        self.assertEqual(run2, self.project1.get_next_run())

        run2.task_start_date = timezone.now()
        run2.save()
        self.assertEqual(None, self.project1.get_next_run())

    def test_scanpipe_project_model_get_latest_failed_run(self):
        self.assertEqual(None, self.project1.get_latest_failed_run())

        run1 = self.create_run()
        run2 = self.create_run()
        self.assertEqual(None, self.project1.get_latest_failed_run())

        run1.task_exitcode = 0
        run1.save()
        self.assertEqual(None, self.project1.get_latest_failed_run())

        run1.task_exitcode = 1
        run1.save()
        self.assertEqual(run1, self.project1.get_latest_failed_run())

        run2.task_exitcode = 0
        run2.save()
        self.assertEqual(run1, self.project1.get_latest_failed_run())

        run2.task_exitcode = 1
        run2.save()
        self.assertEqual(run2, self.project1.get_latest_failed_run())

        run1.task_exitcode = None
        run1.save()
        self.assertEqual(run2, self.project1.get_latest_failed_run())

    def test_scanpipe_run_model_task_methods(self):
        run1 = self.create_run()
        self.assertFalse(run1.task_succeeded)

        run1.task_exitcode = 0
        run1.save()
        self.assertTrue(run1.task_succeeded)

        run1.task_exitcode = 1
        run1.save()
        self.assertFalse(run1.task_succeeded)

    def test_scanpipe_run_model_task_execution_time_property(self):
        run1 = self.create_run()

        self.assertIsNone(run1.execution_time)

        run1.task_start_date = datetime(1984, 10, 10, 10, 10, 10, tzinfo=timezone.utc)
        run1.save()
        self.assertIsNone(run1.execution_time)

        run1.task_end_date = datetime(1984, 10, 10, 10, 10, 35, tzinfo=timezone.utc)
        run1.save()
        self.assertEqual(25.0, run1.execution_time)

    def test_scanpipe_run_model_reset_task_values_method(self):
        run1 = self.create_run(
            task_id=uuid.uuid4(),
            task_start_date=timezone.now(),
            task_end_date=timezone.now(),
            task_exitcode=0,
            task_output="Output",
        )

        run1.reset_task_values()
        self.assertIsNone(run1.task_id)
        self.assertIsNone(run1.task_start_date)
        self.assertIsNone(run1.task_end_date)
        self.assertIsNone(run1.task_exitcode)
        self.assertEqual("", run1.task_output)

    def test_scanpipe_run_model_set_task_started_method(self):
        run1 = self.create_run()

        task_id = uuid.uuid4()
        run1.set_task_started(task_id)

        run1 = Run.objects.get(pk=run1.pk)
        self.assertEqual(task_id, run1.task_id)
        self.assertTrue(run1.task_start_date)
        self.assertFalse(run1.task_end_date)

    def test_scanpipe_run_model_set_task_ended_method(self):
        run1 = self.create_run()

        run1.set_task_ended(exitcode=0, output="output")

        run1 = Run.objects.get(pk=run1.pk)
        self.assertEqual(0, run1.task_exitcode)
        self.assertEqual("output", run1.task_output)
        self.assertTrue(run1.task_end_date)

    def test_scanpipe_run_model_get_run_id_method(self):
        run1 = self.create_run()

        self.assertIsNone(run1.get_run_id())

        run1.task_output = "Missing run-id"
        run1.save()
        self.assertIsNone(run1.get_run_id())

        run1.task_output = "Workflow starting (run-id 1593181041039832):"
        run1.save()
        self.assertEqual("1593181041039832", run1.get_run_id())

        run1.task_output = "(run-id 123) + (run-id 456)"
        run1.save()
        self.assertEqual("123", run1.get_run_id())

    def test_scanpipe_run_model_queryset_methods(self):
        now = timezone.now()

        started = self.create_run(task_start_date=now)
        not_started = self.create_run()
        executed = self.create_run(task_start_date=now, task_end_date=now)
        succeed = self.create_run(task_start_date=now, task_exitcode=0)
        failed = self.create_run(task_start_date=now, task_exitcode=1)

        qs = self.project1.runs.started()
        self.assertEqual(4, len(qs))
        self.assertIn(started, qs)
        self.assertIn(executed, qs)
        self.assertIn(succeed, qs)
        self.assertIn(failed, qs)

        qs = self.project1.runs.not_started()
        self.assertEqual([not_started], list(qs))

        qs = self.project1.runs.executed()
        self.assertEqual([executed], list(qs))

        qs = self.project1.runs.succeed()
        self.assertEqual([succeed], list(qs))

        qs = self.project1.runs.failed()
        self.assertEqual([failed], list(qs))

    def test_scanpipe_run_model_profile_method(self):
        run1 = self.create_run()

        self.assertIsNone(run1.profile())

        run1.task_output = (
            "Validating your flow...\n"
            "    The graph looks good!\n"
            "Running pylint...\n"
            "    Pylint is happy!\n"
            "2021-01-08 15:44:19.380 Workflow starting (run-id 1):\n"
            "2021-01-08 15:44:19.385 [1/start/1 (pid 1)] Task is starting.\n"
            "2021-01-08 15:44:20.720 [1/start/1 (pid 1)] Task finished successfully.\n"
            "2021-01-08 15:44:20.727 [1/step1/2 (pid 1)] Task is starting.\n"
            "2021-01-08 15:44:26.722 [1/step1/2 (pid 1)] Task finished successfully.\n"
            "2021-01-08 15:44:26.729 [1/step2/3 (pid 1)] Task is starting.\n"
            "2021-01-08 15:44:31.619 [1/step2/3 (pid 1)] Task finished successfully.\n"
            "2021-01-08 15:44:31.626 [1/step3/4 (pid 1)] Task is starting.\n"
            "2021-01-08 15:44:33.119 [1/step3/4 (pid 1)] Task finished successfully.\n"
            "2021-01-08 15:44:38.481 [1/step4/5 (pid 1)] Task is starting.\n"
            "2021-01-08 15:54:40.042 [1/step4/5 (pid 1)] Task finished successfully.\n"
            "2021-01-08 15:55:04.345 [1/end/13 (pid 1)] Task is starting.\n"
            "2021-01-08 15:55:05.651 [1/end/13 (pid 1)] Task finished successfully.\n"
            "2021-01-08 15:55:05.652 Done!'"
        )
        run1.save()
        self.assertIsNone(run1.profile())

        run1.task_exitcode = 0
        run1.save()

        expected = {
            "start": 1,
            "step1": 5,
            "step2": 4,
            "step3": 1,
            "step4": 601,
            "end": 1,
        }
        self.assertEqual(expected, run1.profile())

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertIsNone(run1.profile(print_results=True))

        expected = (
            "start    1 seconds 0.2%\n"
            "step1    5 seconds 0.8%\n"
            "step2    4 seconds 0.7%\n"
            "step3    1 seconds 0.2%\n"
            "\x1b[41;37mstep4  601 seconds 98.0%\x1b[m\n"
            "end      1 seconds 0.2%\n"
        )
        self.assertEqual(expected, output.getvalue())

    def test_scanpipe_codebase_resource_model_methods(self):
        resource = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )

        self.assertEqual(
            self.project1.codebase_path / resource.path, resource.location_path
        )
        self.assertEqual(
            f"{self.project1.codebase_path}/{resource.path}", resource.location
        )

        with open(resource.location, "w") as f:
            f.write("content")
        self.assertEqual("content", resource.file_content)

        package = DiscoveredPackage.objects.create(project=self.project1)
        resource.discovered_packages.add(package)
        self.assertEqual([str(package.uuid)], resource.for_packages)

        scan_results = {
            "name": "name",
            "extension": "ext",
            "non_resource_field": "value",
        }
        resource.set_scan_results(scan_results, save=True)
        self.assertEqual(scan_results["name"], resource.name)
        self.assertEqual(scan_results["extension"], resource.extension)

    def test_scanpipe_codebase_resource_type_methods(self):
        CodebaseResource.objects.all().delete()

        file = CodebaseResource.objects.create(
            project=self.project1, type=CodebaseResource.Type.FILE, path="file"
        )
        directory = CodebaseResource.objects.create(
            project=self.project1,
            type=CodebaseResource.Type.DIRECTORY,
            path="directory",
        )
        symlink = CodebaseResource.objects.create(
            project=self.project1, type=CodebaseResource.Type.SYMLINK, path="symlink"
        )

        self.assertTrue(file.is_file)
        self.assertFalse(file.is_dir)
        self.assertFalse(file.is_symlink)

        self.assertFalse(directory.is_file)
        self.assertTrue(directory.is_dir)
        self.assertFalse(directory.is_symlink)

        self.assertFalse(symlink.is_file)
        self.assertFalse(symlink.is_dir)
        self.assertTrue(symlink.is_symlink)

        qs = CodebaseResource.objects.files()
        self.assertEqual(1, len(qs))
        self.assertIn(file, qs)

        qs = CodebaseResource.objects.directories()
        self.assertEqual(1, len(qs))
        self.assertIn(directory, qs)

        qs = CodebaseResource.objects.symlinks()
        self.assertEqual(1, len(qs))
        self.assertIn(symlink, qs)

        qs = CodebaseResource.objects.without_symlinks()
        self.assertEqual(2, len(qs))
        self.assertIn(file, qs)
        self.assertIn(directory, qs)
        self.assertNotIn(symlink, qs)

    def test_scanpipe_codebase_resource_descendants(self):
        path = "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref"
        resource = self.project_asgiref.codebaseresources.get(path=path)
        descendants = list(resource.descendants())
        self.assertEqual(9, len(descendants))
        self.assertNotIn(resource.path, descendants)
        expected = [
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/__init__.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/compatibility.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/"
            "current_thread_executor.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/local.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/server.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/sync.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/testing.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/timeout.py",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/wsgi.py",
        ]
        self.assertEqual(expected, sorted([resource.path for resource in descendants]))

    def test_scanpipe_codebase_resource_children(self):
        resource = self.project_asgiref.codebaseresources.get(path="codebase")
        children = list(resource.children())
        self.assertEqual(2, len(children))
        self.assertNotIn(resource.path, children)
        expected = [
            "codebase/asgiref-3.3.0-py3-none-any.whl",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract",
        ]
        self.assertEqual(expected, [resource.path for resource in children])

        path = "codebase/asgiref-3.3.0-py3-none-any.whl-extract"
        resource = self.project_asgiref.codebaseresources.get(path=path)
        children = list(resource.children())
        self.assertEqual(2, len(children))
        self.assertNotIn(resource.path, children)
        expected = [
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref",
            "codebase/asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info",
        ]
        self.assertEqual(expected, [resource.path for resource in children])

    def test_scanpipe_discovered_package_model_create_from_data(self):
        package = DiscoveredPackage.create_from_data(self.project1, package_data1)
        self.assertEqual(self.project1, package.project)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", str(package))
        self.assertEqual("deb", package.type)
        self.assertEqual("debian", package.namespace)
        self.assertEqual("adduser", package.name)
        self.assertEqual("3.118", package.version)
        self.assertEqual("arch=all", package.qualifiers)
        self.assertEqual("add and remove users and groups", package.description)
        self.assertEqual("849", package.size)
        self.assertEqual(
            "gpl-2.0 AND gpl-2.0-plus AND unknown", package.license_expression
        )

    def test_scanpipe_discovered_package_model_create_for_resource(self):
        codebase_resource = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )
        package = DiscoveredPackage.create_for_resource(
            package_data1, codebase_resource
        )
        self.assertEqual(self.project1, package.project)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", str(package))
        self.assertEqual(1, codebase_resource.discovered_packages.count())
        self.assertEqual(package, codebase_resource.discovered_packages.get())


class ScanPipeModelsTransactionTest(TransactionTestCase):
    """
    Since we are testing some Database errors, we need to use a
    TransactionTestCase to avoid any TransactionManagementError while running
    the tests.
    """

    @mock.patch("scanpipe.models.Run.run_pipeline_task_async")
    def test_scanpipe_project_model_add_pipeline(self, run_task):
        project1 = Project.objects.create(name="Analysis")

        self.assertEqual(0, project1.runs.count())

        pipeline, _name = scanpipe_app_config.pipelines[0]
        project1.add_pipeline(pipeline)

        self.assertEqual(1, project1.runs.count())
        run = project1.runs.get()
        self.assertEqual(pipeline, run.pipeline)
        self.assertEqual(get_pipeline_doc(pipeline), run.description)
        run_task.assert_not_called()

        project1.add_pipeline(pipeline, start_run=True)
        run_task.assert_called_once()

    def test_scanpipe_project_model_add_error(self):
        project1 = Project.objects.create(name="Analysis")
        error = project1.add_error(Exception("Error message"), model="Package")
        self.assertEqual(error, ProjectError.objects.get())
        self.assertEqual("Package", error.model)
        self.assertEqual({}, error.details)
        self.assertEqual("Error message", error.message)
        self.assertEqual("", error.traceback)

    def test_scanpipe_project_error_model_save_non_valid_related_object(self):
        project1 = Project.objects.create(name="Analysis")
        long_value = "value" * 1000

        package = DiscoveredPackage.objects.create(
            project=project1, filename=long_value
        )
        # The DiscoveredPackage was not created
        self.assertIsNone(package.id)
        self.assertEqual(0, DiscoveredPackage.objects.count())
        # A ProjectError was saved instead
        self.assertEqual(1, project1.projecterrors.count())

        error = project1.projecterrors.get()
        self.assertEqual("DiscoveredPackage", error.model)
        self.assertEqual(long_value, error.details["filename"])
        self.assertEqual(
            "value too long for type character varying(255)\n", error.message
        )

        codebase_resource = CodebaseResource.objects.create(
            project=project1, type=long_value
        )
        self.assertIsNone(codebase_resource.id)
        self.assertEqual(0, CodebaseResource.objects.count())
        self.assertEqual(2, project1.projecterrors.count())

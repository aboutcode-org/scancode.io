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
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1
from scanpipe.tests.pipelines.do_nothing import DoNothing

scanpipe_app_config = apps.get_app_config("scanpipe")


class ScanPipeModelsTest(TestCase):
    data_location = Path(__file__).parent / "data"
    fixtures = [data_location / "asgiref-3.3.0_fixtures.json"]

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project_asgiref = Project.objects.get(name="asgiref")

    def create_run(self, **kwargs):
        return Run.objects.create(
            project=self.project1,
            pipeline_name="pipeline",
            **kwargs,
        )

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

    def test_scanpipe_project_model_delete(self):
        work_path = self.project1.work_path
        self.assertTrue(work_path.exists())

        self.project1.add_input_file(SimpleUploadedFile("file.ext", content=b"content"))
        self.project1.add_pipeline("docker")
        resource = CodebaseResource.objects.create(project=self.project1, path="path")
        package = DiscoveredPackage.objects.create(project=self.project1)
        resource.discovered_packages.add(package)

        delete_log = self.project1.delete()
        expected = {
            "scanpipe.CodebaseResource": 1,
            "scanpipe.DiscoveredPackage": 1,
            "scanpipe.DiscoveredPackage_codebase_resources": 1,
            "scanpipe.Project": 1,
            "scanpipe.Run": 1,
        }
        self.assertEqual(expected, delete_log[1])

        self.assertFalse(Project.objects.filter(name="my_project").exists())
        self.assertFalse(work_path.exists())

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

    def test_scanpipe_run_model_pipeline_class_property(self):
        run1 = Run.objects.create(project=self.project1, pipeline_name="do_nothing")
        self.assertEqual(DoNothing, run1.pipeline_class)

    def test_scanpipe_run_model_make_pipeline_instance(self):
        run1 = Run.objects.create(project=self.project1, pipeline_name="do_nothing")
        pipeline_instance = run1.make_pipeline_instance()
        self.assertTrue(isinstance(pipeline_instance, DoNothing))

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

    def test_scanpipe_run_model_append_to_log(self):
        run1 = self.create_run()

        with self.assertRaises(ValueError):
            run1.append_to_log("multiline\nmessage")

        run1.append_to_log("line1")
        run1.append_to_log("line2", save=True)

        run1.refresh_from_db()
        self.assertEqual("line1\nline2\n", run1.log)

    def test_scanpipe_run_model_profile_method(self):
        run1 = self.create_run()
        self.assertIsNone(run1.profile())

        run1.log = (
            "2021-02-05 12:46:47.63 Pipeline [ScanCodebase] starting\n"
            "2021-02-05 12:46:47.63 Step [copy_inputs_to_codebase_directory] starting\n"
            "2021-02-05 12:46:47.63 Step [copy_inputs_to_codebase_directory]"
            " completed in 0.00 seconds\n"
            "2021-02-05 12:46:47.63 Step [run_extractcode] starting\n"
            "2021-02-05 12:46:48.13 Step [run_extractcode] completed in 0.50 seconds\n"
            "2021-02-05 12:46:48.14 Step [run_scancode] starting\n"
            "2021-02-05 12:46:52.59 Step [run_scancode] completed in 4.45 seconds\n"
            "2021-02-05 12:46:52.59 Step [build_inventory_from_scan] starting\n"
            "2021-02-05 12:46:52.75 Step [build_inventory_from_scan]"
            " completed in 0.16 seconds\n"
            "2021-02-05 12:46:52.75 Step [csv_output] starting\n"
            "2021-02-05 12:46:52.82 Step [csv_output] completed in 0.06 seconds\n"
            "2021-02-05 12:46:52.82 Pipeline completed\n"
        )
        run1.save()
        self.assertIsNone(run1.profile())

        run1.task_exitcode = 0
        run1.save()

        expected = {
            "build_inventory_from_scan": 0.16,
            "copy_inputs_to_codebase_directory": 0.0,
            "csv_output": 0.06,
            "run_extractcode": 0.5,
            "run_scancode": 4.45,
        }
        self.assertEqual(expected, run1.profile())

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertIsNone(run1.profile(print_results=True))

        expected = (
            "copy_inputs_to_codebase_directory  0.0 seconds 0.0%\n"
            "run_extractcode                    0.5 seconds 9.7%\n"
            "\x1b[41;37mrun_scancode                       4.45 seconds 86.1%\x1b[m\n"
            "build_inventory_from_scan          0.16 seconds 3.1%\n"
            "csv_output                         0.06 seconds 1.2%\n"
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

    def test_scanpipe_scan_fields_model_mixin_methods(self):
        expected = [
            "copyrights",
            "holders",
            "authors",
            "licenses",
            "license_expressions",
            "emails",
            "urls",
        ]
        self.assertEqual(expected, CodebaseResource.scan_fields())

        resource = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )

        scan_results = {
            "license_expressions": ["mit"],
            "name": "name",
            "non_resource_field": "value",
        }
        resource.set_scan_results(scan_results, save=True)
        resource.refresh_from_db()
        self.assertEqual("", resource.name)
        self.assertEqual(["mit"], resource.license_expressions)

        resource2 = CodebaseResource.objects.create(project=self.project1, path="file2")
        resource2.copy_scan_results(from_instance=resource, save=True)
        resource.refresh_from_db()
        self.assertEqual(["mit"], resource2.license_expressions)

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

        file.licenses = [{"key": "bsd-new", "name": "BSD-3-Clause"}]
        file.save()
        qs = CodebaseResource.objects.has_licenses()
        self.assertEqual(1, len(qs))
        self.assertIn(file, qs)
        self.assertNotIn(directory, qs)
        self.assertNotIn(symlink, qs)

        qs = CodebaseResource.objects.has_no_licenses()
        self.assertEqual(2, len(qs))
        self.assertNotIn(file, qs)
        self.assertIn(directory, qs)
        self.assertIn(symlink, qs)

        self.assertEqual(0, CodebaseResource.objects.in_package().count())
        self.assertEqual(3, CodebaseResource.objects.not_in_package().count())

        DiscoveredPackage.create_for_resource(package_data1, file)
        self.assertEqual(1, CodebaseResource.objects.in_package().count())
        self.assertEqual(2, CodebaseResource.objects.not_in_package().count())

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

    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_project_model_add_pipeline(self, mock_execute_task):
        project1 = Project.objects.create(name="Analysis")

        self.assertEqual(0, project1.runs.count())

        pipeline_name = "docker"
        pipeline_class = scanpipe_app_config.pipelines.get(pipeline_name)
        project1.add_pipeline(pipeline_name)

        self.assertEqual(1, project1.runs.count())
        run = project1.runs.get()
        self.assertEqual(pipeline_name, run.pipeline_name)
        self.assertEqual(pipeline_class.get_doc(), run.description)
        mock_execute_task.assert_not_called()

        project1.add_pipeline(pipeline_name, execute_now=True)
        mock_execute_task.assert_called_once()

    def test_scanpipe_project_model_add_error(self):
        project1 = Project.objects.create(name="Analysis")
        error = project1.add_error(Exception("Error message"), model="Package")
        self.assertEqual(error, ProjectError.objects.get())
        self.assertEqual("Package", error.model)
        self.assertEqual({}, error.details)
        self.assertEqual("Error message", error.message)
        self.assertEqual("", error.traceback)

    def test_scanpipe_codebase_resource_model_add_error(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(project=project1)
        error = codebase_resource.add_error(Exception("Error message"))

        self.assertEqual(error, ProjectError.objects.get())
        self.assertEqual("CodebaseResource", error.model)
        self.assertTrue(error.details)
        self.assertEqual("Error message", error.message)
        self.assertEqual("", error.traceback)

    def test_scanpipe_codebase_resource_model_add_errors(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(project=project1)
        codebase_resource.add_error(Exception("Error1"))
        codebase_resource.add_error(Exception("Error2"))
        self.assertEqual(2, ProjectError.objects.count())

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

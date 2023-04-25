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
import shutil
import sys
import tempfile
import uuid
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock
from unittest import skipIf

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import DataError
from django.db import IntegrityError
from django.db import connection
from django.test import TestCase
from django.test import TransactionTestCase
from django.test import override_settings
from django.utils import timezone

from packagedcode.models import PackageData
from requests.exceptions import RequestException
from rq.job import JobStatus

from scancodeio import __version__ as scancodeio_version
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.models import RunInProgressError
from scanpipe.models import get_project_work_directory
from scanpipe.pipes.fetch import Download
from scanpipe.pipes.input import copy_input
from scanpipe.pipes.input import copy_inputs
from scanpipe.tests import dependency_data1
from scanpipe.tests import dependency_data2
from scanpipe.tests import license_policies_index
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1
from scanpipe.tests.pipelines.do_nothing import DoNothing

scanpipe_app = apps.get_app_config("scanpipe")
User = get_user_model()


class ScanPipeModelsTest(TestCase):
    data_location = Path(__file__).parent / "data"
    fixtures = [data_location / "asgiref-3.3.0_fixtures.json"]

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.project_asgiref = Project.objects.get(name="asgiref")

    def create_run(self, pipeline="pipeline", **kwargs):
        return Run.objects.create(
            project=self.project1,
            pipeline_name=pipeline,
            **kwargs,
        )

    def test_scanpipe_project_model_extra_data(self):
        self.assertEqual({}, self.project1.extra_data)
        project1_from_db = Project.objects.get(name=self.project1.name)
        self.assertEqual({}, project1_from_db.extra_data)

    def test_scanpipe_project_model_work_directories(self):
        expected_work_directory = f"projects/analysis-{self.project1.short_uuid}"
        self.assertTrue(self.project1.work_directory.endswith(expected_work_directory))
        self.assertTrue(self.project1.work_path.exists())
        self.assertTrue(self.project1.input_path.exists())
        self.assertTrue(self.project1.output_path.exists())
        self.assertTrue(self.project1.codebase_path.exists())
        self.assertTrue(self.project1.tmp_path.exists())

    def test_scanpipe_get_project_work_directory(self):
        project = Project.objects.create(name="Name with spaces and @£$éæ")
        expected = f"/projects/name-with-spaces-and-e-{project.short_uuid}"
        self.assertTrue(get_project_work_directory(project).endswith(expected))
        self.assertTrue(project.work_directory.endswith(expected))

    def test_scanpipe_project_model_clear_tmp_directory(self):
        new_file_path = self.project1.tmp_path / "file.ext"
        new_file_path.touch()
        self.assertEqual([new_file_path], list(self.project1.tmp_path.glob("*")))

        self.project1.clear_tmp_directory()
        self.assertTrue(self.project1.tmp_path.exists())
        self.assertEqual([], list(self.project1.tmp_path.glob("*")))

        self.assertTrue(self.project1.tmp_path.exists())
        shutil.rmtree(self.project1.work_path, ignore_errors=True)
        self.assertFalse(self.project1.tmp_path.exists())
        self.project1.clear_tmp_directory()
        self.assertTrue(self.project1.tmp_path.exists())

    def test_scanpipe_project_model_archive(self):
        (self.project1.input_path / "input_file").touch()
        (self.project1.codebase_path / "codebase_file").touch()
        (self.project1.output_path / "output_file").touch()
        self.assertEqual(1, len(Project.get_root_content(self.project1.input_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.codebase_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.output_path)))

        self.project1.archive()
        self.project1.refresh_from_db()
        self.assertTrue(self.project1.is_archived)
        self.assertEqual(1, len(Project.get_root_content(self.project1.input_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.codebase_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.output_path)))

        self.project1.archive(remove_input=True, remove_codebase=True)
        self.assertEqual(0, len(Project.get_root_content(self.project1.input_path)))
        self.assertEqual(0, len(Project.get_root_content(self.project1.codebase_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.output_path)))

    def test_scanpipe_project_model_delete(self):
        work_path = self.project1.work_path
        self.assertTrue(work_path.exists())

        uploaded_file = SimpleUploadedFile("file.ext", content=b"content")
        self.project1.write_input_file(uploaded_file)
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

        self.assertFalse(Project.objects.filter(name=self.project1.name).exists())
        self.assertFalse(work_path.exists())

    def test_scanpipe_project_model_reset(self):
        work_path = self.project1.work_path
        self.assertTrue(work_path.exists())

        uploaded_file = SimpleUploadedFile("file.ext", content=b"content")
        self.project1.write_input_file(uploaded_file)
        self.project1.add_pipeline("docker")
        CodebaseResource.objects.create(project=self.project1, path="path")
        DiscoveredPackage.objects.create(project=self.project1)

        self.project1.reset()

        self.assertTrue(Project.objects.filter(name=self.project1.name).exists())
        self.assertEqual(0, self.project1.projecterrors.count())
        self.assertEqual(0, self.project1.runs.count())
        self.assertEqual(0, self.project1.discoveredpackages.count())
        self.assertEqual(0, self.project1.codebaseresources.count())

        self.assertTrue(work_path.exists())
        self.assertTrue(self.project1.input_path.exists())
        self.assertEqual(["file.ext"], self.project1.input_root)
        self.assertTrue(self.project1.output_path.exists())
        self.assertTrue(self.project1.codebase_path.exists())
        self.assertTrue(self.project1.tmp_path.exists())

    def test_scanpipe_project_model_input_sources_list_property(self):
        self.project1.add_input_source(filename="file1", source="uploaded")
        self.project1.add_input_source(filename="file2", source="https://download.url")

        expected = [
            {"filename": "file1", "source": "uploaded"},
            {"filename": "file2", "source": "https://download.url"},
        ]
        self.assertEqual(expected, self.project1.input_sources_list)

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

        # get_output_file_path always ensure the work_directory is setup
        shutil.rmtree(self.project1.work_directory)
        self.assertFalse(self.project1.work_path.exists())
        self.project1.get_output_file_path("file", "ext")
        self.assertTrue(self.project1.work_path.exists())

    def test_scanpipe_project_model_get_latest_output(self):
        scan1 = self.project1.get_output_file_path("scancode", "json")
        scan1.write_text("")
        scan2 = self.project1.get_output_file_path("scancode", "json")
        scan2.write_text("")
        summary1 = self.project1.get_output_file_path("summary", "json")
        summary1.write_text("")
        scan3 = self.project1.get_output_file_path("scancode", "json")
        scan3.write_text("")
        summary2 = self.project1.get_output_file_path("summary", "json")
        summary2.write_text("")

        self.assertIsNone(self.project1.get_latest_output("none"))
        self.assertEqual(scan3, self.project1.get_latest_output("scancode"))
        self.assertEqual(summary2, self.project1.get_latest_output("summary"))

    def test_scanpipe_project_model_write_input_file(self):
        self.assertEqual([], self.project1.input_files)

        uploaded_file = SimpleUploadedFile("file.ext", content=b"content")
        self.project1.write_input_file(uploaded_file)

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

    def test_scanpipe_project_model_inputs_with_source(self):
        inputs, missing_inputs = self.project1.inputs_with_source
        self.assertEqual([], inputs)
        self.assertEqual({}, missing_inputs)

        uploaded_file = SimpleUploadedFile("file.ext", content=b"content")
        self.project1.add_uploads([uploaded_file])
        self.project1.copy_input_from(self.data_location / "notice.NOTICE")
        self.project1.add_input_source(filename="missing.zip", source="uploaded")

        inputs, missing_inputs = self.project1.inputs_with_source
        sha256_1 = "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73"
        sha256_2 = "b323607418a36b5bd700fcf52ae9ca49f82ec6359bc4b89b1b2d73cf75321757"
        expected = [
            {
                "is_file": True,
                "name": "file.ext",
                "sha256": sha256_1,
                "size": 7,
                "source": "uploaded",
            },
            {
                "is_file": True,
                "name": "notice.NOTICE",
                "sha256": sha256_2,
                "size": 1178,
                "source": "not_found",
            },
        ]

        def sort_by_name(x):
            return x.get("name")

        self.assertEqual(
            sorted(expected, key=sort_by_name), sorted(inputs, key=sort_by_name)
        )
        self.assertEqual({"missing.zip": "uploaded"}, missing_inputs)

    def test_scanpipe_project_model_can_add_input(self):
        self.assertTrue(self.project1.can_add_input)

        run = self.project1.add_pipeline("docker")
        self.project1 = Project.objects.get(uuid=self.project1.uuid)
        self.assertTrue(self.project1.can_add_input)

        run.task_start_date = timezone.now()
        run.save()
        self.project1 = Project.objects.get(uuid=self.project1.uuid)
        self.assertFalse(self.project1.can_add_input)

    def test_scanpipe_project_model_add_input_source(self):
        self.assertEqual({}, self.project1.input_sources)

        self.project1.add_input_source("filename", "source", save=True)
        self.project1.refresh_from_db()
        self.assertEqual({"filename": "source"}, self.project1.input_sources)

    def test_scanpipe_project_model_add_downloads(self):
        file_location = self.data_location / "notice.NOTICE"
        copy_inputs([file_location], self.project1.tmp_path)

        download = Download(
            uri="https://example.com/filename.zip",
            directory="",
            filename="notice.NOTICE",
            path=self.project1.tmp_path / "notice.NOTICE",
            size="",
            sha1="",
            md5="",
        )

        self.project1.add_downloads([download])

        inputs, missing_inputs = self.project1.inputs_with_source
        sha256 = "b323607418a36b5bd700fcf52ae9ca49f82ec6359bc4b89b1b2d73cf75321757"
        expected = [
            {
                "is_file": True,
                "name": "notice.NOTICE",
                "sha256": sha256,
                "size": 1178,
                "source": "https://example.com/filename.zip",
            }
        ]
        self.assertEqual(expected, inputs)
        self.assertEqual({}, missing_inputs)

    def test_scanpipe_project_model_add_uploads(self):
        uploaded_file = SimpleUploadedFile("file.ext", content=b"content")
        self.project1.add_uploads([uploaded_file])

        inputs, missing_inputs = self.project1.inputs_with_source
        sha256 = "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73"
        expected = [
            {
                "name": "file.ext",
                "is_file": True,
                "sha256": sha256,
                "size": 7,
                "source": "uploaded",
            }
        ]
        self.assertEqual(expected, inputs)
        self.assertEqual({}, missing_inputs)

    def test_scanpipe_project_model_add_webhook_subscription(self):
        self.assertEqual(0, self.project1.webhooksubscriptions.count())
        self.project1.add_webhook_subscription("https://localhost")
        self.assertEqual(1, self.project1.webhooksubscriptions.count())

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

    def test_scanpipe_project_model_raise_if_run_in_progress(self):
        run1 = self.create_run()
        self.assertIsNone(self.project1._raise_if_run_in_progress())

        run1.set_task_started(task_id=1)
        with self.assertRaises(RunInProgressError):
            self.project1._raise_if_run_in_progress()

        with self.assertRaises(RunInProgressError):
            self.project1.archive()

        with self.assertRaises(RunInProgressError):
            self.project1.delete()

        with self.assertRaises(RunInProgressError):
            self.project1.reset()

    def test_scanpipe_project_queryset_with_counts(self):
        self.project_asgiref.add_error("error 1", "model")
        self.project_asgiref.add_error("error 2", "model")

        project_qs = Project.objects.with_counts(
            "codebaseresources",
            "discoveredpackages",
            "projecterrors",
        )

        project = project_qs.get(pk=self.project_asgiref.pk)
        self.assertEqual(18, project.codebaseresources_count)
        self.assertEqual(18, project.codebaseresources.count())
        self.assertEqual(2, project.discoveredpackages_count)
        self.assertEqual(2, project.discoveredpackages.count())
        self.assertEqual(2, project.projecterrors_count)
        self.assertEqual(2, project.projecterrors.count())

    def test_scanpipe_project_related_queryset_get_or_none(self):
        self.assertIsNone(CodebaseResource.objects.get_or_none(path="path/"))
        self.assertIsNone(DiscoveredPackage.objects.get_or_none(name="name"))

    def test_scanpipe_run_model_set_scancodeio_version(self):
        run1 = Run.objects.create(project=self.project1)
        self.assertEqual("", run1.scancodeio_version)

        run1.set_scancodeio_version()
        self.assertEqual(scancodeio_version, run1.scancodeio_version)

        with self.assertRaises(ValueError) as cm:
            run1.set_scancodeio_version()
        self.assertIn("Field scancodeio_version already set to", str(cm.exception))

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

        run1.set_task_staled()
        run1.refresh_from_db()
        self.assertIsNone(run1.execution_time)

    def test_scanpipe_run_model_execution_time_for_display_property(self):
        run1 = self.create_run()

        self.assertIsNone(run1.execution_time_for_display)

        run1.task_start_date = datetime(1984, 10, 10, 10, 10, 10, tzinfo=timezone.utc)
        run1.save()
        self.assertIsNone(run1.execution_time_for_display)

        run1.task_end_date = datetime(1984, 10, 10, 10, 10, 35, tzinfo=timezone.utc)
        run1.save()
        self.assertEqual("25 seconds", run1.execution_time_for_display)

        run1.task_end_date = datetime(1984, 10, 10, 10, 12, 35, tzinfo=timezone.utc)
        run1.save()
        self.assertEqual("145 seconds (2.4 minutes)", run1.execution_time_for_display)

        run1.task_end_date = datetime(1984, 10, 10, 11, 12, 35, tzinfo=timezone.utc)
        run1.save()
        self.assertEqual("3745 seconds (1.0 hours)", run1.execution_time_for_display)

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

    def test_scanpipe_run_model_set_task_methods(self):
        run1 = self.create_run()
        self.assertIsNone(run1.task_id)
        self.assertEqual(Run.Status.NOT_STARTED, run1.status)

        run1.set_task_queued()
        run1.refresh_from_db()
        self.assertEqual(run1.pk, run1.task_id)
        self.assertEqual(Run.Status.QUEUED, run1.status)

        run1.set_task_started(run1.pk)
        self.assertTrue(run1.task_start_date)
        self.assertEqual(Run.Status.RUNNING, run1.status)

        run1.set_task_ended(exitcode=0)
        self.assertTrue(run1.task_end_date)
        self.assertEqual(Run.Status.SUCCESS, run1.status)
        self.assertTrue(run1.task_succeeded)

        run1.set_task_ended(exitcode=1)
        self.assertEqual(Run.Status.FAILURE, run1.status)
        self.assertTrue(run1.task_failed)

        run1.set_task_staled()
        self.assertEqual(Run.Status.STALE, run1.status)
        self.assertTrue(run1.task_staled)

        run1.set_task_stopped()
        self.assertEqual(Run.Status.STOPPED, run1.status)
        self.assertTrue(run1.task_stopped)

    @override_settings(SCANCODEIO_ASYNC=False)
    def test_scanpipe_run_model_stop_task_method(self):
        run1 = self.create_run()
        run1.stop_task()
        self.assertEqual(Run.Status.STOPPED, run1.status)
        self.assertTrue(run1.task_stopped)

    @override_settings(SCANCODEIO_ASYNC=False)
    def test_scanpipe_run_model_delete_task_method(self):
        run1 = self.create_run()
        run1.delete_task()
        self.assertFalse(Run.objects.filter(pk=run1.pk).exists())
        self.assertFalse(self.project1.runs.exists())

    def test_scanpipe_run_model_queryset_methods(self):
        now = timezone.now()

        running = self.create_run(
            pipeline="running", task_start_date=now, task_id=uuid.uuid4()
        )
        not_started = self.create_run(pipeline="not_started")
        queued = self.create_run(pipeline="queued", task_id=uuid.uuid4())
        executed = self.create_run(
            pipeline="executed", task_start_date=now, task_end_date=now
        )
        succeed = self.create_run(
            pipeline="succeed", task_start_date=now, task_end_date=now, task_exitcode=0
        )
        failed = self.create_run(
            pipeline="failed", task_start_date=now, task_end_date=now, task_exitcode=1
        )

        qs = self.project1.runs.has_start_date()
        self.assertQuerySetEqual(qs, [running, executed, succeed, failed])

        qs = self.project1.runs.not_started()
        self.assertQuerySetEqual(qs, [not_started])

        qs = self.project1.runs.queued()
        self.assertQuerySetEqual(qs, [queued])

        qs = self.project1.runs.running()
        self.assertQuerySetEqual(qs, [running])

        qs = self.project1.runs.executed()
        self.assertQuerySetEqual(qs, [executed, succeed, failed])

        qs = self.project1.runs.succeed()
        self.assertQuerySetEqual(qs, [succeed])

        qs = self.project1.runs.failed()
        self.assertQuerySetEqual(qs, [failed])

        queued_or_running_qs = self.project1.runs.queued_or_running()
        self.assertQuerySetEqual(queued_or_running_qs, [running, queued])

    def test_scanpipe_run_model_status_property(self):
        now = timezone.now()

        running = self.create_run(task_start_date=now)
        not_started = self.create_run()
        queued = self.create_run(task_id=uuid.uuid4())
        succeed = self.create_run(
            task_start_date=now, task_end_date=now, task_exitcode=0
        )
        failed = self.create_run(
            task_start_date=now, task_end_date=now, task_exitcode=1
        )

        self.assertEqual(Run.Status.RUNNING, running.status)
        self.assertEqual(Run.Status.NOT_STARTED, not_started.status)
        self.assertEqual(Run.Status.QUEUED, queued.status)
        self.assertEqual(Run.Status.SUCCESS, succeed.status)
        self.assertEqual(Run.Status.FAILURE, failed.status)

    @override_settings(SCANCODEIO_ASYNC=True)
    @mock.patch("scanpipe.models.Run.execute_task_async")
    @mock.patch("scanpipe.models.Run.job_status", new_callable=mock.PropertyMock)
    def test_scanpipe_run_model_sync_with_job_async_mode(
        self, mock_job_status, mock_execute_task
    ):
        queued = self.create_run(task_id=uuid.uuid4())
        self.assertEqual(Run.Status.QUEUED, queued.status)
        mock_job_status.return_value = None
        queued.sync_with_job()
        mock_execute_task.assert_called_once()

        running = self.create_run(task_id=uuid.uuid4(), task_start_date=timezone.now())
        self.assertEqual(Run.Status.RUNNING, running.status)
        mock_job_status.return_value = None
        running.sync_with_job()
        running.refresh_from_db()
        self.assertTrue(running.task_staled)

        running = self.create_run(task_id=uuid.uuid4(), task_start_date=timezone.now())
        mock_job_status.return_value = JobStatus.STOPPED
        running.sync_with_job()
        running.refresh_from_db()
        self.assertTrue(running.task_stopped)

        running = self.create_run(task_id=uuid.uuid4(), task_start_date=timezone.now())
        mock_job_status.return_value = JobStatus.FAILED
        running.sync_with_job()
        running.refresh_from_db()
        self.assertTrue(running.task_failed)
        expected = "Job was moved to the FailedJobRegistry during cleanup"
        self.assertEqual(expected, running.task_output)

        running = self.create_run(task_id=uuid.uuid4(), task_start_date=timezone.now())
        mock_job_status.return_value = "Something else"
        running.sync_with_job()
        running.refresh_from_db()
        self.assertTrue(running.task_staled)

    @override_settings(SCANCODEIO_ASYNC=False)
    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_run_model_sync_with_job_sync_mode(self, mock_execute_task):
        queued = self.create_run(task_id=uuid.uuid4())
        self.assertEqual(Run.Status.QUEUED, queued.status)
        queued.sync_with_job()
        mock_execute_task.assert_called_once()

        running = self.create_run(task_id=uuid.uuid4(), task_start_date=timezone.now())
        self.assertEqual(Run.Status.RUNNING, running.status)
        running.sync_with_job()
        running.refresh_from_db()
        self.assertTrue(running.task_staled)

    def test_scanpipe_run_model_append_to_log(self):
        run1 = self.create_run()

        with self.assertRaises(ValueError):
            run1.append_to_log("multiline\nmessage")

        run1.append_to_log("line1")
        run1.append_to_log("line2", save=True)

        run1.refresh_from_db()
        self.assertEqual("line1\nline2\n", run1.log)

    @mock.patch("scanpipe.models.WebhookSubscription.deliver")
    def test_scanpipe_run_model_deliver_project_subscriptions(self, mock_deliver):
        self.project1.add_webhook_subscription("https://localhost")
        run1 = self.create_run()
        run1.deliver_project_subscriptions()
        mock_deliver.assert_called_once_with(pipeline_run=run1)

    def test_scanpipe_run_model_profile_method(self):
        run1 = self.create_run()
        self.assertIsNone(run1.profile())

        run1.log = (
            "2021-02-05 12:46:47.63 Pipeline [ScanCodebase] starting\n"
            "2021-02-05 12:46:47.63 Step [copy_inputs_to_codebase_directory] starting\n"
            "2021-02-05 12:46:47.63 Step [copy_inputs_to_codebase_directory]"
            " completed in 0.00 seconds\n"
            "2021-02-05 12:46:47.63 Step [extract_archives] starting\n"
            "2021-02-05 12:46:48.13 Step [extract_archives] completed in 0.50 seconds\n"
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
            "extract_archives": 0.5,
            "run_scancode": 4.45,
        }
        self.assertEqual(expected, run1.profile())

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertIsNone(run1.profile(print_results=True))

        expected = (
            "copy_inputs_to_codebase_directory  0.0 seconds 0.0%\n"
            "extract_archives                   0.5 seconds 9.7%\n"
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
        self.assertEqual("content\n", resource.file_content)

        package = DiscoveredPackage.objects.create(project=self.project1)
        resource.discovered_packages.add(package)
        self.assertEqual([str(package.uuid)], resource.for_packages)

    def test_scanpipe_codebase_resource_model_file_content(self):
        resource = self.project1.codebaseresources.create(path="filename.ext")

        with open(resource.location, "w") as f:
            f.write("content")
        self.assertEqual("content\n", resource.file_content)

        file_with_long_lines = self.data_location / "decompose_l_u_8hpp_source.html"
        copy_input(file_with_long_lines, self.project1.codebase_path)

        resource.path = "decompose_l_u_8hpp_source.html"
        resource.save()

        line_count = len(resource.file_content.split("\n"))
        self.assertEqual(101, line_count)

    def test_scanpipe_codebase_resource_model_unique_license_expressions(self):
        resource = CodebaseResource(project=self.project1)
        resource.license_expressions = [
            "mit",
            "apache-2.0",
            "apache-2.0",
            "mit AND apache-2.0",
            "gpl-3.0",
        ]
        expected = ["apache-2.0", "gpl-3.0", "mit", "mit AND apache-2.0"]
        self.assertEqual(expected, resource.unique_license_expressions)

    def test_scanpipe_pipes_codebase_resources_inject_licenses_policy(self):
        resource = CodebaseResource(
            licenses=[
                {"key": "mit"},
                {"key": "apache-2.0"},
                {"key": "gpl-3.0"},
            ]
        )

        expected = [
            {"key": "mit", "policy": None},
            {
                "key": "apache-2.0",
                "policy": {
                    "color_code": "#008000",
                    "compliance_alert": "",
                    "label": "Approved License",
                    "license_key": "apache-2.0",
                },
            },
            {
                "key": "gpl-3.0",
                "policy": {
                    "color_code": "#c83025",
                    "compliance_alert": "error",
                    "label": "Prohibited License",
                    "license_key": "gpl-3.0",
                },
            },
        ]

        resource.inject_licenses_policy(license_policies_index)
        self.assertEqual(expected, resource.licenses)

    def test_scanpipe_pipes_scancode_codebase_resources_inject_policy_on_save(self):
        scanpipe_app.license_policies_index = license_policies_index

        resource = CodebaseResource.objects.create(
            project=self.project1, path="file", licenses=[{"key": "gpl-3.0"}]
        )
        expected = [
            {
                "key": "gpl-3.0",
                "policy": {
                    "color_code": "#c83025",
                    "compliance_alert": "error",
                    "label": "Prohibited License",
                    "license_key": "gpl-3.0",
                },
            }
        ]
        self.assertEqual(expected, resource.licenses)

        resource.licenses = [{"key": "not-in-index"}]
        resource.save()
        expected = [{"key": "not-in-index", "policy": None}]
        self.assertEqual(expected, resource.licenses)

        resource.licenses = [{"key": "apache-2.0"}]
        resource.save()
        expected = [
            {
                "key": "apache-2.0",
                "policy": {
                    "color_code": "#008000",
                    "compliance_alert": "",
                    "label": "Approved License",
                    "license_key": "apache-2.0",
                },
            }
        ]
        self.assertEqual(expected, resource.licenses)

    def test_scanpipe_codebase_resource_model_compliance_alert(self):
        scanpipe_app.license_policies_index = license_policies_index
        resource = CodebaseResource.objects.create(project=self.project1, path="file")
        self.assertEqual("", resource.compliance_alert)

        license_key = "bsd-new"
        self.assertNotIn(license_key, scanpipe_app.license_policies_index)
        resource.licenses = [{"key": license_key}]
        resource.save()
        self.assertEqual("missing", resource.compliance_alert)

        license_key = "apache-2.0"
        self.assertIn(license_key, scanpipe_app.license_policies_index)
        resource.licenses = [{"key": license_key}]
        resource.save()
        self.assertEqual("ok", resource.compliance_alert)

        license_key = "mpl-2.0"
        self.assertIn(license_key, scanpipe_app.license_policies_index)
        resource.licenses = [{"key": license_key}]
        resource.save()
        self.assertEqual("warning", resource.compliance_alert)

        license_key = "gpl-3.0"
        self.assertIn(license_key, scanpipe_app.license_policies_index)
        resource.licenses = [{"key": license_key}]
        resource.save()
        self.assertEqual("error", resource.compliance_alert)

        resource.licenses = [
            {"key": "apache-2.0"},
            {"key": "mpl-2.0"},
            {"key": "gpl-3.0"},
        ]
        resource.save()
        self.assertEqual("error", resource.compliance_alert)

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

    def test_scanpipe_codebase_resource_queryset_methods(self):
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

        qs = CodebaseResource.objects.empty()
        self.assertEqual(3, len(qs))
        file.size = 1
        file.save()
        qs = CodebaseResource.objects.empty()
        self.assertEqual(2, len(qs))
        self.assertNotIn(file, qs)
        file.size = 0
        file.save()
        qs = CodebaseResource.objects.empty()
        self.assertEqual(3, len(qs))

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

        qs = CodebaseResource.objects.unknown_license()
        self.assertEqual(0, len(qs))

        file.license_expressions = ["gpl-3.0", "unknown"]
        file.save()
        qs = CodebaseResource.objects.unknown_license()
        self.assertEqual(1, len(qs))
        self.assertIn(file, qs)

        file.license_expressions = ["unknown AND mit", "gpl-3.0-plus"]
        file.save()
        qs = CodebaseResource.objects.unknown_license()
        self.assertEqual(1, len(qs))
        self.assertIn(file, qs)

        file.license_expressions = ["gpl-3.0-plus OR unknown"]
        file.save()
        qs = CodebaseResource.objects.unknown_license()
        self.assertEqual(1, len(qs))
        self.assertIn(file, qs)

        self.assertEqual(0, CodebaseResource.objects.in_package().count())
        self.assertEqual(3, CodebaseResource.objects.not_in_package().count())

        file.create_and_add_package(package_data1)
        self.assertEqual(1, CodebaseResource.objects.in_package().count())
        self.assertEqual(2, CodebaseResource.objects.not_in_package().count())

    def test_scanpipe_codebase_resource_queryset_licenses_categories(self):
        CodebaseResource.objects.all().delete()

        resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path="1",
            licenses=[{"key": "gpl-3.0", "category": "Copyleft"}],
        )

        resource2 = CodebaseResource.objects.create(
            project=self.project1,
            path="2",
            licenses=[{"key": "lgpl-3.0-plus", "category": "Copyleft Limited"}],
        )

        resource_qs = self.project1.codebaseresources

        categories = ["Permissive"]
        self.assertQuerySetEqual([], resource_qs.licenses_categories(categories))

        categories = ["Copyleft"]
        expected = [resource1]
        self.assertQuerySetEqual(expected, resource_qs.licenses_categories(categories))

        categories = ["Copyleft Limited"]
        expected = [resource2]
        self.assertQuerySetEqual(expected, resource_qs.licenses_categories(categories))

        categories = ["Copyleft", "Copyleft Limited"]
        expected = [resource1, resource2]
        self.assertQuerySetEqual(expected, resource_qs.licenses_categories(categories))

    def _create_resources_for_queryset_methods(self):
        resource1 = CodebaseResource.objects.create(project=self.project1, path="1")
        resource1.holders = [
            {"holder": "H1", "end_line": 51, "start_line": 50},
            {"holder": "H2", "end_line": 61, "start_line": 60},
        ]
        resource1.mime_type = "application/zip"
        resource1.save()

        resource2 = CodebaseResource.objects.create(project=self.project1, path="2")
        resource2.holders = [{"holder": "H3", "end_line": 558, "start_line": 556}]
        resource2.mime_type = "application/zip"
        resource2.save()

        resource3 = CodebaseResource.objects.create(project=self.project1, path="3")
        resource3.mime_type = "text/plain"
        resource3.save()

        return resource1, resource2, resource3

    def test_scanpipe_codebase_resource_queryset_json_field_contains(self):
        resource1, resource2, resource3 = self._create_resources_for_queryset_methods()

        qs = CodebaseResource.objects
        self.assertQuerySetEqual([resource2], qs.json_field_contains("holders", "H3"))
        self.assertQuerySetEqual([resource1], qs.json_field_contains("holders", "H1"))
        expected = [resource1, resource2]
        self.assertQuerySetEqual(expected, qs.json_field_contains("holders", "H"))

    def test_scanpipe_codebase_resource_queryset_json_list_contains(self):
        resource1, resource2, resource3 = self._create_resources_for_queryset_methods()
        qs = CodebaseResource.objects

        results = qs.json_list_contains("holders", "holder", ["H3"])
        self.assertQuerySetEqual([resource2], results)

        results = qs.json_list_contains("holders", "holder", ["H1"])
        self.assertQuerySetEqual([resource1], results)
        results = qs.json_list_contains("holders", "holder", ["H2"])
        self.assertQuerySetEqual([resource1], results)
        results = qs.json_list_contains("holders", "holder", ["H1", "H2"])
        self.assertQuerySetEqual([resource1], results)

        results = qs.json_list_contains("holders", "holder", ["H1", "H2", "H3"])
        self.assertQuerySetEqual([resource1, resource2], results)

        results = qs.json_list_contains("holders", "holder", ["H"])
        self.assertQuerySetEqual([], results)

    def test_scanpipe_codebase_resource_queryset_values_from_json_field(self):
        CodebaseResource.objects.all().delete()
        self._create_resources_for_queryset_methods()
        qs = CodebaseResource.objects

        results = qs.values_from_json_field("holders", "nothing")
        self.assertEqual(["", "", "", ""], results)

        results = qs.values_from_json_field("holders", "holder")
        self.assertEqual(["H1", "H2", "H3", ""], results)

    def test_scanpipe_codebase_resource_queryset_group_by(self):
        CodebaseResource.objects.all().delete()
        self._create_resources_for_queryset_methods()
        expected = [
            {"mime_type": "application/zip", "count": 2},
            {"mime_type": "text/plain", "count": 1},
        ]
        self.assertEqual(expected, list(CodebaseResource.objects.group_by("mime_type")))

    def test_scanpipe_codebase_resource_queryset_most_common_values(self):
        CodebaseResource.objects.all().delete()
        self._create_resources_for_queryset_methods()
        results = CodebaseResource.objects.most_common_values("mime_type", limit=1)
        self.assertQuerySetEqual(["application/zip"], results)

    def test_scanpipe_codebase_resource_queryset_less_common_values(self):
        CodebaseResource.objects.all().delete()
        self._create_resources_for_queryset_methods()
        CodebaseResource.objects.create(
            project=self.project1, path="4", mime_type="text/x-script.python"
        )

        results = CodebaseResource.objects.less_common_values("mime_type", limit=1)
        expected = ["text/plain", "text/x-script.python"]
        self.assertQuerySetEqual(expected, results, ordered=False)

    def test_scanpipe_codebase_resource_queryset_less_common(self):
        CodebaseResource.objects.all().delete()
        resource1, resource2, resource3 = self._create_resources_for_queryset_methods()
        resource4 = CodebaseResource.objects.create(
            project=self.project1, path="4", mime_type="text/x-script.python"
        )
        resource4.holders = [
            {"holder": "H1", "end_line": 51, "start_line": 50},
            {"holder": "H1", "end_line": 51, "start_line": 50},
            {"holder": "H2", "end_line": 51, "start_line": 50},
            {"holder": "H2", "end_line": 51, "start_line": 50},
        ]
        resource4.save()

        qs = CodebaseResource.objects
        results = qs.less_common("mime_type", limit=1)
        self.assertQuerySetEqual([resource3, resource4], results)

        results = qs.less_common("holders", limit=2)
        self.assertQuerySetEqual([resource2], results)

    def test_scanpipe_codebase_resource_descendants(self):
        path = "asgiref-3.3.0-py3-none-any.whl-extract/asgiref"
        resource = self.project_asgiref.codebaseresources.get(path=path)
        descendants = list(resource.descendants())
        self.assertEqual(9, len(descendants))
        self.assertNotIn(resource.path, descendants)
        expected = [
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/"
            "current_thread_executor.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/local.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/server.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/wsgi.py",
        ]
        self.assertEqual(expected, sorted([resource.path for resource in descendants]))

    def test_scanpipe_codebase_resource_children(self):
        path = "asgiref-3.3.0-py3-none-any.whl-extract"
        resource = self.project_asgiref.codebaseresources.get(path=path)
        children = list(resource.children())
        self.assertEqual(2, len(children))
        self.assertNotIn(resource.path, children)
        expected = [
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info",
        ]
        self.assertEqual(expected, [resource.path for resource in children])

    def test_scanpipe_codebase_resource_add_package(self):
        resource = CodebaseResource.objects.create(project=self.project1, path="file")
        package = DiscoveredPackage.create_from_data(self.project1, package_data1)
        resource.add_package(package)
        self.assertEqual(1, resource.discovered_packages.count())
        self.assertEqual(package, resource.discovered_packages.get())

    def test_scanpipe_codebase_resource_create_and_add_package(self):
        resource = CodebaseResource.objects.create(project=self.project1, path="file")
        package = resource.create_and_add_package(package_data1)
        self.assertEqual(self.project1, package.project)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", str(package))
        self.assertEqual(1, resource.discovered_packages.count())
        self.assertEqual(package, resource.discovered_packages.get())

    def test_scanpipe_discovered_package_model_queryset_methods(self):
        DiscoveredPackage.create_from_data(self.project1, package_data1)
        inputs = [
            ("pkg:deb/debian/adduser@3.118?arch=all", 1),
            ("pkg:deb/debian/adduser@3.118", 1),
            ("pkg:deb/debian/adduser", 1),
            ("pkg:deb/debian", 0),
            ("pkg:deb/debian/adduser@4", 0),
        ]

        for purl, expected_count in inputs:
            qs = DiscoveredPackage.objects.for_package_url(purl)
            self.assertEqual(expected_count, qs.count(), msg=purl)

    @skipIf(sys.platform != "linux", "Ordering differs on macOS.")
    def test_scanpipe_codebase_resource_model_walk_method(self):
        fixtures = self.data_location / "asgiref-3.3.0_walk_test_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        asgiref_root = self.project_asgiref.codebaseresources.get(
            path="asgiref-3.3.0.whl-extract"
        )

        topdown_paths = list(r.path for r in asgiref_root.walk(topdown=True))
        expected_topdown_paths = [
            "asgiref-3.3.0.whl-extract/asgiref",
            "asgiref-3.3.0.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0.whl-extract/asgiref/current_thread_executor.py",
            "asgiref-3.3.0.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0.whl-extract/asgiref/local.py",
            "asgiref-3.3.0.whl-extract/asgiref/server.py",
            "asgiref-3.3.0.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0.whl-extract/asgiref/wsgi.py",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/LICENSE",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/METADATA",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/RECORD",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/top_level.txt",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/WHEEL",
        ]
        self.assertEqual(expected_topdown_paths, topdown_paths)

        bottom_up_paths = list(r.path for r in asgiref_root.walk(topdown=False))
        expected_bottom_up_paths = [
            "asgiref-3.3.0.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0.whl-extract/asgiref/current_thread_executor.py",
            "asgiref-3.3.0.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0.whl-extract/asgiref/local.py",
            "asgiref-3.3.0.whl-extract/asgiref/server.py",
            "asgiref-3.3.0.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0.whl-extract/asgiref/wsgi.py",
            "asgiref-3.3.0.whl-extract/asgiref",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/LICENSE",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/METADATA",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/RECORD",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/top_level.txt",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info/WHEEL",
            "asgiref-3.3.0.whl-extract/asgiref-3.3.0.dist-info",
        ]
        self.assertEqual(expected_bottom_up_paths, bottom_up_paths)

        # Test parent-related methods
        asgiref_resource = self.project_asgiref.codebaseresources.get(
            path="asgiref-3.3.0.whl-extract/asgiref/compatibility.py"
        )
        expected_parent_path = "asgiref-3.3.0.whl-extract/asgiref"
        self.assertEqual(expected_parent_path, asgiref_resource.parent_path())
        self.assertTrue(asgiref_resource.has_parent())
        expected_parent = self.project_asgiref.codebaseresources.get(
            path="asgiref-3.3.0.whl-extract/asgiref"
        )
        self.assertEqual(expected_parent, asgiref_resource.parent())

        # Test sibling-related methods
        expected_siblings = [
            "asgiref-3.3.0.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0.whl-extract/asgiref/current_thread_executor.py",
            "asgiref-3.3.0.whl-extract/asgiref/local.py",
            "asgiref-3.3.0.whl-extract/asgiref/server.py",
            "asgiref-3.3.0.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0.whl-extract/asgiref/wsgi.py",
        ]
        asgiref_resource_siblings = [r.path for r in asgiref_resource.siblings()]
        self.assertEqual(sorted(expected_siblings), sorted(asgiref_resource_siblings))

    def test_scanpipe_codebase_resource_model_walk_method_problematic_filenames(self):
        project = Project.objects.create(name="walk_test_problematic_filenames")
        resource1 = CodebaseResource.objects.create(
            project=project, path="qt-everywhere-opensource-src-5.3.2/gnuwin32/bin"
        )
        CodebaseResource.objects.create(
            project=project,
            path="qt-everywhere-opensource-src-5.3.2/gnuwin32/bin/flex++.exe",
        )
        expected_paths = [
            "qt-everywhere-opensource-src-5.3.2/gnuwin32/bin/flex++.exe",
        ]
        result = [r.path for r in resource1.walk()]
        self.assertEqual(expected_paths, result)

    @mock.patch("requests.post")
    def test_scanpipe_webhook_subscription_deliver_method(self, mock_post):
        webhook = self.project1.add_webhook_subscription("https://localhost")
        self.assertFalse(webhook.delivered)
        run1 = self.create_run()

        mock_post.side_effect = RequestException("Error from exception")
        self.assertFalse(webhook.deliver(pipeline_run=run1))
        webhook.refresh_from_db()
        self.assertEqual("Error from exception", webhook.delivery_error)
        self.assertFalse(webhook.delivered)
        self.assertFalse(webhook.success)

        mock_post.side_effect = None
        mock_post.return_value = mock.Mock(status_code=404, text="text")
        self.assertTrue(webhook.deliver(pipeline_run=run1))
        webhook.refresh_from_db()
        self.assertTrue(webhook.delivered)
        self.assertFalse(webhook.success)
        self.assertEqual("text", webhook.response_text)

        mock_post.return_value = mock.Mock(status_code=200, text="text")
        self.assertTrue(webhook.deliver(pipeline_run=run1))
        webhook.refresh_from_db()
        self.assertTrue(webhook.delivered)
        self.assertTrue(webhook.success)
        self.assertEqual("text", webhook.response_text)

    def test_scanpipe_discovered_package_model_extract_purl_data(self):
        package_data = {}
        expected = {
            "type": "",
            "namespace": "",
            "name": "",
            "version": "",
            "qualifiers": "",
            "subpath": "",
        }
        purl_data = DiscoveredPackage.extract_purl_data(package_data)
        self.assertEqual(expected, purl_data)

        expected = {
            "name": "adduser",
            "namespace": "debian",
            "qualifiers": "arch=all",
            "subpath": "",
            "type": "deb",
            "version": "3.118",
        }
        purl_data = DiscoveredPackage.extract_purl_data(package_data1)
        self.assertEqual(expected, purl_data)

    def test_scanpipe_discovered_package_model_update_from_data(self):
        package = DiscoveredPackage.create_from_data(self.project1, package_data1)
        new_data = {
            "name": "new name",
            "notice_text": "NOTICE",
            "description": "new description",
            "unknown_field": "value",
        }
        updated_fields = package.update_from_data(new_data)
        self.assertEqual(["notice_text"], updated_fields)

        package.refresh_from_db()
        # PURL field, not updated
        self.assertEqual(package_data1["name"], package.name)
        # Empty field, updated
        self.assertEqual(new_data["notice_text"], package.notice_text)
        # Already a value, not updated
        self.assertEqual(package_data1["description"], package.description)

        updated_fields = package.update_from_data(new_data, override=True)
        self.assertEqual(["description"], updated_fields)
        self.assertEqual(new_data["description"], package.description)

    def test_scanpipe_discovered_package_model_add_resources(self):
        package = DiscoveredPackage.create_from_data(self.project1, package_data1)
        resource1 = CodebaseResource.objects.create(project=self.project1, path="file1")
        resource2 = CodebaseResource.objects.create(project=self.project1, path="file2")

        package.add_resources([resource1])
        self.assertEqual(1, package.codebase_resources.count())
        self.assertIn(resource1, package.codebase_resources.all())
        package.add_resources([resource2])
        self.assertEqual(2, package.codebase_resources.count())
        self.assertIn(resource2, package.codebase_resources.all())

        package.codebase_resources.remove(resource1)
        package.codebase_resources.remove(resource2)
        self.assertEqual(0, package.codebase_resources.count())
        package.add_resources([resource1, resource2])
        self.assertEqual(2, package.codebase_resources.count())
        self.assertIn(resource1, package.codebase_resources.all())
        self.assertIn(resource2, package.codebase_resources.all())

    def test_scanpipe_discovered_package_model_as_cyclonedx(self):
        package = DiscoveredPackage.create_from_data(self.project1, package_data1)
        cyclonedx_component = package.as_cyclonedx()

        self.assertEqual("library", cyclonedx_component.type)
        self.assertEqual(package_data1["name"], cyclonedx_component.name)
        self.assertEqual(package_data1["version"], cyclonedx_component.version)
        purl = "pkg:deb/debian/adduser@3.118?arch=all"
        self.assertEqual(purl, str(cyclonedx_component.bom_ref))
        self.assertEqual(purl, cyclonedx_component.purl)
        self.assertEqual(1, len(cyclonedx_component.licenses))
        expected = "GPL-2.0-only AND GPL-2.0-or-later AND LicenseRef-scancode-unknown"
        self.assertEqual(expected, cyclonedx_component.licenses[0].expression)
        self.assertEqual(package_data1["copyright"], cyclonedx_component.copyright)
        self.assertEqual(package_data1["description"], cyclonedx_component.description)
        self.assertEqual(1, len(cyclonedx_component.hashes))
        self.assertEqual(package_data1["md5"], cyclonedx_component.hashes[0].content)

        properties = {prop.name: prop.value for prop in cyclonedx_component.properties}
        expected_properties = {
            "aboutcode:download_url": "https://download.url/package.zip",
            "aboutcode:filename": "package.zip",
            "aboutcode:homepage_url": "https://packages.debian.org",
            "aboutcode:primary_language": "bash",
        }
        self.assertEqual(expected_properties, properties)

        external_references = cyclonedx_component.external_references
        self.assertEqual(1, len(external_references))
        self.assertEqual("vcs", external_references[0].type)
        self.assertEqual("https://packages.vcs.url", external_references[0].url)

    def test_scanpipe_model_create_user_creates_auth_token(self):
        basic_user = User.objects.create_user(username="basic_user")
        self.assertTrue(basic_user.auth_token.key)
        self.assertEqual(40, len(basic_user.auth_token.key))

    def test_scanpipe_discovered_dependency_model_update_from_data(self):
        DiscoveredPackage.create_from_data(self.project1, package_data1)
        CodebaseResource.objects.create(
            project=self.project1, path="data.tar.gz-extract/Gemfile.lock"
        )
        dependency = DiscoveredDependency.create_from_data(
            self.project1, dependency_data2
        )

        new_data = {
            "name": "new name",
            "extracted_requirement": "new requirement",
            "scope": "new scope",
            "unknown_field": "value",
        }
        updated_fields = dependency.update_from_data(new_data)
        self.assertEqual(["extracted_requirement"], updated_fields)

        dependency.refresh_from_db()
        # PURL field, not updated
        self.assertEqual("appraisal", dependency.name)
        # Empty field, updated
        self.assertEqual(
            new_data["extracted_requirement"], dependency.extracted_requirement
        )
        # Already a value, not updated
        self.assertEqual(dependency_data2["scope"], dependency.scope)

        updated_fields = dependency.update_from_data(new_data, override=True)
        self.assertEqual(["scope"], updated_fields)
        self.assertEqual(new_data["scope"], dependency.scope)


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

        pipeline_name = "not_available"
        with self.assertRaises(ValueError) as error:
            project1.add_pipeline(pipeline_name)
        self.assertEqual("Unknown pipeline: not_available", str(error.exception))

        pipeline_name = "inspect_manifest"
        project1.add_pipeline(pipeline_name)
        pipeline_class = scanpipe_app.pipelines.get(pipeline_name)

        self.assertEqual(1, project1.runs.count())
        run = project1.runs.get()
        self.assertEqual(pipeline_name, run.pipeline_name)
        self.assertEqual(pipeline_class.get_summary(), run.description)
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

    def test_scanpipe_project_model_update_extra_data(self):
        project1 = Project.objects.create(name="Analysis")
        self.assertEqual({}, project1.extra_data)

        with self.assertRaises(ValueError):
            project1.update_extra_data("not_a_dict")

        data = {"key": "value"}
        project1.update_extra_data(data)
        self.assertEqual(data, project1.extra_data)
        project1.refresh_from_db()
        self.assertEqual(data, project1.extra_data)

        more_data = {"more": "data"}
        project1.update_extra_data(more_data)
        expected = {"key": "value", "more": "data"}
        self.assertEqual(expected, project1.extra_data)
        project1.refresh_from_db()
        self.assertEqual(expected, project1.extra_data)

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

    @skipIf(connection.vendor == "sqlite", "No max_length constraints on SQLite.")
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
            "value too long for type character varying(255)", error.message
        )

        codebase_resource = CodebaseResource.objects.create(
            project=project1, type=long_value
        )
        self.assertIsNone(codebase_resource.id)
        self.assertEqual(0, CodebaseResource.objects.count())
        self.assertEqual(2, project1.projecterrors.count())

    @skipIf(connection.vendor == "sqlite", "No max_length constraints on SQLite.")
    def test_scanpipe_discovered_package_model_create_from_data(self):
        project1 = Project.objects.create(name="Analysis")

        package = DiscoveredPackage.create_from_data(project1, package_data1)
        self.assertEqual(project1, package.project)
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

        package_count = DiscoveredPackage.objects.count()
        incomplete_data = dict(package_data1)
        incomplete_data["name"] = ""
        self.assertIsNone(DiscoveredPackage.create_from_data(project1, incomplete_data))
        self.assertEqual(package_count, DiscoveredPackage.objects.count())
        error = project1.projecterrors.latest("created_date")
        self.assertEqual("DiscoveredPackage", error.model)
        expected_message = "No values for the following required fields: name"
        self.assertEqual(expected_message, error.message)
        self.assertEqual(package_data1["purl"], error.details["purl"])
        self.assertEqual("", error.details["name"])
        self.assertEqual("", error.traceback)

        package_count = DiscoveredPackage.objects.count()
        project_error_count = ProjectError.objects.count()
        bad_data = dict(package_data1)
        bad_data["version"] = "a" * 200
        # The exception are not capture at the DiscoveredPackage.create_from_data but
        # rather in the CodebaseResource.create_and_add_package method so resource data
        # can be injected in the ProjectError record.
        with self.assertRaises(DataError):
            DiscoveredPackage.create_from_data(project1, bad_data)

        self.assertEqual(package_count, DiscoveredPackage.objects.count())
        self.assertEqual(project_error_count, ProjectError.objects.count())

    @skipIf(connection.vendor == "sqlite", "No max_length constraints on SQLite.")
    def test_scanpipe_discovered_dependency_model_create_from_data(self):
        project1 = Project.objects.create(name="Analysis")

        DiscoveredPackage.create_from_data(project1, package_data1)
        CodebaseResource.objects.create(
            project=project1, path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO"
        )
        dependency = DiscoveredDependency.create_from_data(
            project1, dependency_data1, strip_datafile_path_root=False
        )
        self.assertEqual(project1, dependency.project)
        self.assertEqual("pkg:pypi/dask", dependency.purl)
        self.assertEqual("dask<2023.0.0,>=2022.6.0", dependency.extracted_requirement)
        self.assertEqual("install", dependency.scope)
        self.assertTrue(dependency.is_runtime)
        self.assertFalse(dependency.is_optional)
        self.assertFalse(dependency.is_resolved)
        self.assertEqual(
            "pkg:pypi/dask?uuid=e656b571-7d3f-46d1-b95b-8f037aef9692",
            dependency.dependency_uid,
        )
        self.assertEqual(
            "pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b",
            dependency.for_package_uid,
        )
        self.assertEqual(
            "daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
            dependency.datafile_path,
        )
        self.assertEqual("pypi_sdist_pkginfo", dependency.datasource_id)

        # Test field validation when using create_from_data
        dependency_count = DiscoveredDependency.objects.count()
        incomplete_data = dict(dependency_data1)
        incomplete_data["dependency_uid"] = ""
        self.assertIsNone(
            DiscoveredDependency.create_from_data(project1, incomplete_data)
        )
        self.assertEqual(dependency_count, DiscoveredDependency.objects.count())
        error = project1.projecterrors.latest("created_date")
        self.assertEqual("DiscoveredDependency", error.model)
        expected_message = "No values for the following required fields: dependency_uid"
        self.assertEqual(expected_message, error.message)
        self.assertEqual(dependency_data1["purl"], error.details["purl"])
        self.assertEqual("", error.details["dependency_uid"])
        self.assertEqual("", error.traceback)

    def test_scanpipe_discovered_package_model_unique_package_uid_in_project(self):
        project1 = Project.objects.create(name="Analysis")

        self.assertTrue(package_data1["package_uid"])
        package = DiscoveredPackage.create_from_data(project1, package_data1)
        self.assertTrue(package.package_uid)

        with self.assertRaises(IntegrityError):
            DiscoveredPackage.create_from_data(project1, package_data1)

        package_data_no_uid = package_data1.copy()
        package_data_no_uid.pop("package_uid")
        package2 = DiscoveredPackage.create_from_data(project1, package_data_no_uid)
        self.assertFalse(package2.package_uid)
        package3 = DiscoveredPackage.create_from_data(project1, package_data_no_uid)
        self.assertFalse(package3.package_uid)

    @skipIf(connection.vendor == "sqlite", "No max_length constraints on SQLite.")
    def test_scanpipe_codebase_resource_create_and_add_package_errors(self):
        project1 = Project.objects.create(name="Analysis")
        resource = CodebaseResource.objects.create(project=project1, path="p")

        package_count = DiscoveredPackage.objects.count()
        bad_data = dict(package_data1)
        bad_data["version"] = "a" * 200

        package = resource.create_and_add_package(bad_data)
        self.assertIsNone(package)
        self.assertEqual(package_count, DiscoveredPackage.objects.count())
        error = project1.projecterrors.latest("created_date")
        self.assertEqual("DiscoveredPackage", error.model)
        expected_message = "value too long for type character varying(100)"
        self.assertEqual(expected_message, error.message)
        self.assertEqual(bad_data["version"], error.details["version"])
        self.assertTrue(error.details["codebase_resource_pk"])
        self.assertEqual(resource.path, error.details["codebase_resource_path"])
        self.assertIn("in save", error.traceback)

    def test_scanpipe_package_model_integrity_with_toolkit_package_model(self):
        toolkit_package_fields = [field.name for field in PackageData.__attrs_attrs__]
        discovered_packages_fields = [
            field.name for field in DiscoveredPackage._meta.get_fields()
        ]
        for toolkit_field_name in toolkit_package_fields:
            self.assertIn(toolkit_field_name, discovered_packages_fields)

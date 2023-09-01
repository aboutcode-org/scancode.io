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

from unittest import mock

from django.conf import settings
from django.test import TestCase

from scanpipe import tasks
from scanpipe.models import Project


class ScanPipeTasksTest(TestCase):
    @mock.patch("scanpipe.pipelines.Pipeline.execute")
    def test_scanpipe_tasks_execute_pipeline_task(self, mock_execute):
        project = Project.objects.create(name="my_project")
        run = project.add_pipeline("do_nothing")

        mock_execute.return_value = 0, ""
        tasks.execute_pipeline_task(run.pk)
        mock_execute.assert_called_once()

        run.refresh_from_db()
        self.assertEqual(0, run.task_exitcode)
        self.assertEqual("", run.task_output)
        self.assertIsNotNone(run.task_start_date)
        self.assertIsNotNone(run.task_end_date)

    @mock.patch("scanpipe.pipelines.Pipeline.execute")
    def test_scanpipe_tasks_execute_pipeline_run_next_on_success(self, mock_execute):
        project = Project.objects.create(name="my_project")
        run = project.add_pipeline("do_nothing")
        run2 = project.add_pipeline("do_nothing")

        mock_execute.return_value = 0, ""
        tasks.execute_pipeline_task(run.pk)
        mock_execute.assert_called()

        run.refresh_from_db()
        self.assertEqual(0, run.task_exitcode)
        self.assertEqual("", run.task_output)
        run2.refresh_from_db()
        if settings.SCANCODEIO_ASYNC:
            self.assertEqual(run2.Status.QUEUED, run2.status)
        else:
            self.assertEqual(0, run2.task_exitcode)
            self.assertEqual("", run2.task_output)

    @mock.patch("scanpipe.pipelines.Pipeline.execute")
    def test_scanpipe_tasks_execute_pipeline_no_run_next_on_failure(self, mock_execute):
        project = Project.objects.create(name="my_project")
        run = project.add_pipeline("do_nothing")
        run2 = project.add_pipeline("do_nothing")

        mock_execute.return_value = 1, "error"
        tasks.execute_pipeline_task(run.pk)
        mock_execute.assert_called_once()

        run.refresh_from_db()
        self.assertEqual(1, run.task_exitcode)
        self.assertEqual("error", run.task_output)
        self.assertIsNotNone(run.task_start_date)
        self.assertIsNotNone(run.task_end_date)

        run2.refresh_from_db()
        self.assertIsNone(run2.task_exitcode)
        self.assertEqual("", run2.task_output)
        self.assertIsNone(run2.task_start_date)
        self.assertIsNone(run2.task_end_date)

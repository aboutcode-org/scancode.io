#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

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

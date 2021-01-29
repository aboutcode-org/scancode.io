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

import sys
from unittest import mock

from django.test import TestCase

from scanpipe import tasks
from scanpipe.models import Project


# WARNING: Running the actual Pipeline execution within a subprocess will not be
# within the test context and will hit the default database.
# Therefore, the mocking of subprocess function is required to test the tasks functions.
@mock.patch("subprocess.getstatusoutput")
class ScanPipeTasksTest(TestCase):
    pipeline_location = "scanpipe/pipelines/docker.py"

    def test_scanpipe_tasks_run_pipeline_task(self, mock_getstatusoutput):
        project = Project.objects.create(name="my_project")
        run = project.add_pipeline(self.pipeline_location)

        mock_getstatusoutput.return_value = (0, "mocked_output")
        tasks.run_pipeline_task(run.pk)
        expected_cmd = (
            f"{sys.executable} {self.pipeline_location} run "
            f'--project "my_project" '
            f'--run-uuid "{run.uuid}"'
        )
        mock_getstatusoutput.assert_called_once_with(expected_cmd)

        run.refresh_from_db()
        self.assertEqual(0, run.task_exitcode)
        self.assertEqual("mocked_output", run.task_output)
        self.assertIsNotNone(run.task_start_date)
        self.assertIsNotNone(run.task_end_date)

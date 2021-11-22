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

import uuid
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone

from scanpipe.apps import ScanPipeConfig
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.tests import license_policies
from scanpipe.tests import license_policies_index
from scanpipe.tests.pipelines.register_from_file import RegisterFromFile

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipeAppsTest(TestCase):
    data_location = Path(__file__).parent / "data"
    pipelines_location = Path(__file__).parent / "pipelines"

    def test_scanpipe_apps_get_policies_index(self):
        self.assertEqual({}, ScanPipeConfig.get_policies_index([], "license_key"))
        policies_index = ScanPipeConfig.get_policies_index(
            policies_list=license_policies,
            key="license_key",
        )
        self.assertEqual(license_policies_index, policies_index)

    def test_scanpipe_apps_set_policies(self):
        scanpipe_app.license_policies_index = {}
        policies_files = None
        with override_settings(SCANCODEIO_POLICIES_FILE=policies_files):
            scanpipe_app.set_policies()
            self.assertEqual({}, scanpipe_app.license_policies_index)

        scanpipe_app.license_policies_index = {}
        policies_files = "not_existing"
        with override_settings(SCANCODEIO_POLICIES_FILE=policies_files):
            scanpipe_app.set_policies()
            self.assertEqual({}, scanpipe_app.license_policies_index)

        scanpipe_app.license_policies_index = {}
        policies_files = self.data_location / "policies.yml"
        with override_settings(SCANCODEIO_POLICIES_FILE=policies_files):
            scanpipe_app.set_policies()
            self.assertEqual(
                license_policies_index, scanpipe_app.license_policies_index
            )

    def test_scanpipe_apps_policies_enabled(self):
        scanpipe_app.license_policies_index = {}
        self.assertFalse(scanpipe_app.policies_enabled)
        scanpipe_app.license_policies_index = {"key": "value"}
        self.assertTrue(scanpipe_app.policies_enabled)

    def test_scanpipe_apps_register_pipeline_from_file(self):
        path = self.pipelines_location / "do_nothing.py"
        with self.assertRaises(ImproperlyConfigured):
            scanpipe_app.register_pipeline_from_file(path)

        path = self.pipelines_location / "register_from_file.py"
        scanpipe_app.register_pipeline_from_file(path)

        self.assertEqual(
            RegisterFromFile.__name__,
            scanpipe_app.pipelines.get("register_from_file").__name__,
        )

        project1 = Project.objects.create(name="Analysis")
        run = project1.add_pipeline("register_from_file")
        pipeline_instance = run.make_pipeline_instance()

        exitcode, output = pipeline_instance.execute()
        self.assertEqual(0, exitcode)

    @mock.patch("scanpipe.models.Run.sync_with_job")
    def test_scanpipe_apps_sync_runs_and_jobs(self, mock_sync_with_job):
        project1 = Project.objects.create(name="Analysis")
        not_started = Run.objects.create(project=project1, pipeline_name="pipeline")
        queued = Run.objects.create(
            project=project1, pipeline_name="pipeline", task_id=uuid.uuid4()
        )
        running = Run.objects.create(
            project=project1,
            pipeline_name="pipeline",
            task_id=uuid.uuid4(),
            task_start_date=timezone.now(),
        )

        self.assertEqual(Run.Status.NOT_STARTED, not_started.status)
        self.assertEqual(Run.Status.QUEUED, queued.status)
        self.assertEqual(Run.Status.RUNNING, running.status)

        scanpipe_app.sync_runs_and_jobs()
        self.assertEqual(2, mock_sync_with_job.call_count)

# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import uuid
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone

from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.tests import filter_warnings
from scanpipe.tests import global_policies
from scanpipe.tests.pipelines.register_from_file import RegisterFromFile

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipeAppsTest(TestCase):
    data = Path(__file__).parent / "data"
    pipelines_location = Path(__file__).parent / "pipelines"

    @patch.object(scanpipe_app, "policies", new_callable=dict)
    def test_scanpipe_apps_set_policies(self, mock_policies):
        # Case 1: No file set
        with override_settings(SCANPIPE={"POLICIES_FILE": None}):
            scanpipe_app.set_policies()
            self.assertEqual({}, scanpipe_app.policies)

        # Case 2: Non-existing file
        with override_settings(SCANPIPE={"POLICIES_FILE": "not_existing"}):
            scanpipe_app.set_policies()
            self.assertEqual({}, scanpipe_app.policies)

        # Case 3: Valid file
        policies_files = self.data / "policies" / "policies.yml"
        with override_settings(SCANPIPE={"POLICIES_FILE": str(policies_files)}):
            scanpipe_app.set_policies()
            self.assertEqual(global_policies, scanpipe_app.policies)

    def test_scanpipe_apps_check_allowed_private_hosts(self):
        allowed_hosts = ["dejacode.internal:8000"]
        with override_settings(SCANPIPE={"ALLOWED_PRIVATE_HOSTS": allowed_hosts}):
            scanpipe_app.check_allowed_private_hosts()

        allowed_hosts = ["http://dejacode.internal:8000"]
        with override_settings(SCANPIPE={"ALLOWED_PRIVATE_HOSTS": allowed_hosts}):
            with self.assertRaises(ImproperlyConfigured):
                scanpipe_app.check_allowed_private_hosts()

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

    def test_scanpipe_apps_get_pipeline_choices(self):
        blank_entry = ("", "---------")
        main_pipeline = ("scan_codebase", "scan_codebase")
        addon_pipeline = ("find_vulnerabilities", "find_vulnerabilities")

        choices = scanpipe_app.get_pipeline_choices()
        self.assertIn(blank_entry, choices)
        self.assertIn(main_pipeline, choices)
        self.assertIn(addon_pipeline, choices)

        choices = scanpipe_app.get_pipeline_choices(include_blank=False)
        self.assertNotIn(blank_entry, choices)
        self.assertIn(main_pipeline, choices)
        self.assertIn(addon_pipeline, choices)

        choices = scanpipe_app.get_pipeline_choices(include_addon=False)
        self.assertIn(blank_entry, choices)
        self.assertIn(main_pipeline, choices)
        self.assertNotIn(addon_pipeline, choices)

        unavailable_pipeline = ("scan_nix_package", "scan_nix_package")
        missing_commands = ["nix-build"]
        with mock.patch(
            "scanpipe.pipes.nix.get_missing_commands", return_value=missing_commands
        ):
            choices = scanpipe_app.get_pipeline_choices(include_unavailable=False)
        self.assertIn(main_pipeline, choices)
        self.assertNotIn(unavailable_pipeline, choices)

    @mock.patch("scanpipe.pipes.nix.get_missing_commands")
    def test_scanpipe_apps_get_pipelines(self, mock_missing_commands):
        mock_missing_commands.return_value = ["nix-build"]
        scan_codebase = scanpipe_app.pipelines["scan_codebase"]
        scan_nix_package = scanpipe_app.pipelines["scan_nix_package"]

        pipelines = scanpipe_app.get_pipelines()
        self.assertEqual(scanpipe_app.pipelines, pipelines)

        pipelines = scanpipe_app.get_pipelines(include_addon=False)
        self.assertIs(scan_codebase, pipelines["scan_codebase"])
        self.assertIs(scan_nix_package, pipelines["scan_nix_package"])
        self.assertNotIn("find_vulnerabilities", pipelines)

        pipelines = scanpipe_app.get_pipelines(include_unavailable=False)
        self.assertIs(scan_codebase, pipelines["scan_codebase"])
        self.assertNotIn("scan_nix_package", pipelines)

        mock_missing_commands.return_value = []
        pipelines = scanpipe_app.get_pipelines(include_unavailable=False)
        self.assertIs(scan_nix_package, pipelines["scan_nix_package"])

    @mock.patch("scanpipe.pipes.nix.get_missing_commands")
    def test_scanpipe_apps_get_pipeline_unavailable_message(
        self, mock_missing_commands
    ):
        mock_missing_commands.return_value = ["nix-build"]
        expected = (
            "scan_nix_package is not available: "
            "Missing commands: nix-build. Use the full ScanCode.io image."
        )
        message = scanpipe_app.get_pipeline_unavailable_message("scan_nix_package")
        self.assertEqual(expected, message)

        mock_missing_commands.return_value = []
        message = scanpipe_app.get_pipeline_unavailable_message("scan_nix_package")
        self.assertEqual("", message)

    @filter_warnings("ignore", category=DeprecationWarning, module="scanpipe")
    def test_scanpipe_apps_get_new_pipeline_name(self):
        self.assertEqual(
            "scan_codebase", scanpipe_app.get_new_pipeline_name("scan_codebase")
        )
        self.assertEqual(
            "not_existing", scanpipe_app.get_new_pipeline_name("not_existing")
        )
        self.assertEqual(
            "analyze_docker_image", scanpipe_app.get_new_pipeline_name("docker")
        )

    def test_scanpipe_apps_extract_group_from_pipeline(self):
        pipeline = "map_deploy_to_develop"

        pipeline_str = pipeline
        pipeline_name, groups = scanpipe_app.extract_group_from_pipeline(pipeline_str)
        self.assertEqual(pipeline, pipeline_name)
        self.assertEqual(None, groups)

        pipeline_str = "map_deploy_to_develop:"
        pipeline_name, groups = scanpipe_app.extract_group_from_pipeline(pipeline_str)
        self.assertEqual(pipeline, pipeline_name)
        self.assertEqual([], groups)

        pipeline_str = "map_deploy_to_develop:group1"
        pipeline_name, groups = scanpipe_app.extract_group_from_pipeline(pipeline_str)
        self.assertEqual(pipeline, pipeline_name)
        self.assertEqual(["group1"], groups)

        pipeline_str = "map_deploy_to_develop:group1,group2"
        pipeline_name, groups = scanpipe_app.extract_group_from_pipeline(pipeline_str)
        self.assertEqual(pipeline, pipeline_name)
        self.assertEqual(["group1", "group2"], groups)

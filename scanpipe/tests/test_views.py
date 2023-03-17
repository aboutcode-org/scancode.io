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
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.tests import license_policies_index
from scanpipe.views import ProjectDetailView

scanpipe_app = apps.get_app_config("scanpipe")


@override_settings(SCANCODEIO_REQUIRE_AUTHENTICATION=False)
class ScanPipeViewsTest(TestCase):
    data_location = Path(__file__).parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_views_project_list_is_archived(self):
        project2 = Project.objects.create(name="project2", is_archived=True)
        url = reverse("project_list")
        is_archive_filter = "?is_archived=true"

        response = self.client.get(url)
        self.assertContains(response, self.project1.name)
        self.assertNotContains(response, project2.name)
        self.assertContains(response, url)
        self.assertContains(response, is_archive_filter)

        response = self.client.get(url + is_archive_filter)
        self.assertNotContains(response, self.project1.name)
        self.assertContains(response, project2.name)

    def test_scanpipe_views_project_list_filters(self):
        url = reverse("project_list")
        response = self.client.get(url)

        is_archived_filters = """
        <li>
          <a href="?is_archived=" class=" is-active">
            <i class="fas fa-seedling"></i> 1 Active
          </a>
        </li>
        <li>
          <a href="?is_archived=true" class="">
            <i class="fas fa-dice-d6"></i> 0 Archived
          </a>
        </li>
        """
        self.assertContains(response, is_archived_filters, html=True)

        pipeline_filters = [
            "?pipeline=docker",
            "?pipeline=docker_windows",
            "?pipeline=load_inventory",
            "?pipeline=root_filesystems",
            "?pipeline=scan_codebase",
            "?pipeline=scan_package",
        ]
        for pipeline_filter in pipeline_filters:
            self.assertContains(response, pipeline_filter)

        status_filters = """
        <li><a href="?status=" class="dropdown-item is-active">All</a></li>
        <li><a href="?status=not_started" class="dropdown-item">Not started</a></li>
        <li><a href="?status=queued" class="dropdown-item">Queued</a></li>
        <li><a href="?status=running" class="dropdown-item">Running</a></li>
        <li><a href="?status=succeed" class="dropdown-item">Success</a></li>
        <li><a href="?status=failed" class="dropdown-item">Failure</a></li>
        """
        self.assertContains(response, status_filters, html=True)

        sort_filters = """
        <li><a href="?sort=" class="dropdown-item is-active">Newest</a></li>
        <li><a href="?sort=created_date" class="dropdown-item">Oldest</a></li>
        <li><a href="?sort=name" class="dropdown-item">Name (A-z)</a></li>
        <li><a href="?sort=-name" class="dropdown-item">Name (z-A)</a></li>
        """
        self.assertContains(response, sort_filters, html=True)

    def test_scanpipe_views_project_list_state_of_filters_in_search_form(self):
        url = reverse("project_list")
        data = {
            "status": "failed",
            "search": "query",
        }
        response = self.client.get(url, data=data)

        expected = (
            '<input class="input " type="text" placeholder="Search projects" '
            'name="search" value="query">'
        )
        self.assertContains(response, expected, html=True)

        expected = '<input type="hidden" name="status" value="failed">'
        self.assertContains(response, expected, html=True)

    @mock.patch("scanpipe.views.ProjectListView.get_paginate_by")
    def test_scanpipe_views_project_list_filters_exclude_page(self, mock_paginate_by):
        url = reverse("project_list")
        # Create another project to enable pagination
        Project.objects.create(name="project2")
        mock_paginate_by.return_value = 1

        data = {"page": "2"}
        response = self.client.get(url, data=data)

        expected = '<a class="is-black-link" href="?page=2&amp;sort=name">Name</a>'
        self.assertContains(response, expected)
        expected = '<li><a href="?status=" class="dropdown-item is-active">All</a></li>'
        self.assertContains(response, expected)
        expected = '<a href="?pipeline=" class="dropdown-item is-active">All</a>'
        self.assertContains(response, expected)
        expected = '<a href="?sort=" class="dropdown-item is-active">Newest</a>'
        self.assertContains(response, expected)

    def test_scanpipe_views_project_details_is_archived(self):
        url = self.project1.get_absolute_url()
        expected1 = "WARNING: This project is archived and read-only."
        expected2 = 'id="modal-archive"'

        response = self.client.get(url)
        self.assertNotContains(response, expected1)
        self.assertContains(response, expected2)

        self.project1.archive()
        response = self.client.get(url)
        self.assertContains(response, expected1)
        self.assertNotContains(response, expected2)

    @mock.patch("requests.get")
    def test_scanpipe_views_project_details_add_inputs(self, mock_get):
        url = self.project1.get_absolute_url()

        data = {
            "input_urls": "https://example.com/archive.zip",
            "add-inputs-submit": "",
        }

        mock_get.side_effect = Exception
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "Input file addition error.")

        mock_get.side_effect = None
        mock_get.return_value = mock.Mock(
            content=b"\x00",
            headers={},
            status_code=200,
            url="url/archive.zip",
        )
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "Input file(s) added.")

        self.assertEqual(["archive.zip"], self.project1.input_files)
        expected = {"archive.zip": "https://example.com/archive.zip"}
        self.project1.refresh_from_db()
        self.assertEqual(expected, self.project1.input_sources)

    def test_scanpipe_views_project_details_missing_inputs(self):
        self.project1.add_input_source(
            filename="missing.zip", source="uploaded", save=True
        )
        url = self.project1.get_absolute_url()
        response = self.client.get(url)
        expected = (
            '<div class="message-body">'
            "    The following input files are not available on disk anymore:<br>"
            "    - missing.zip"
            "</div>"
        )
        self.assertContains(response, expected, html=True)

    def test_scanpipe_views_project_details_add_pipelines(self):
        url = self.project1.get_absolute_url()
        data = {
            "pipeline": "docker",
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "Pipeline added.")
        run = self.project1.runs.get()
        self.assertEqual("docker", run.pipeline_name)
        self.assertIsNone(run.task_start_date)

    def test_scanpipe_views_project_details_charts_compliance_alert(self):
        url = reverse("project_charts", args=[self.project1.uuid])
        expected = 'id="compliance_alert_chart"'

        scanpipe_app.license_policies_index = None
        response = self.client.get(url)
        self.assertNotContains(response, expected)

        scanpipe_app.license_policies_index = license_policies_index
        response = self.client.get(url)
        self.assertNotContains(response, expected)

        CodebaseResource.objects.create(
            project=self.project1,
            compliance_alert="error",
            type=CodebaseResource.Type.FILE,
        )
        response = self.client.get(url)
        self.assertContains(response, expected)

    def test_scanpipe_views_project_details_scan_summary_panels(self):
        url = self.project1.get_absolute_url()

        expected1 = 'id="license-clarity-panel"'
        expected2 = 'id="scan-summary-panel"'

        response = self.client.get(url)
        self.assertNotContains(response, expected1)
        self.assertNotContains(response, expected2)

        summary_file = self.project1.get_output_file_path("summary", "json")
        with summary_file.open("wb") as opened_file:
            opened_file.write(b"\x21")

        response = self.client.get(url)
        self.assertNotContains(response, expected1)
        self.assertNotContains(response, expected2)

        scan_summary = self.data_location / "is-npm-1.0.0_scan_package_summary.json"
        with summary_file.open("w") as opened_file:
            opened_file.write(scan_summary.read_text())

        response = self.client.get(url)
        self.assertContains(response, expected1)
        self.assertContains(response, expected2)

    def test_scanpipe_views_project_details_get_license_clarity_data(self):
        get_license_clarity_data = ProjectDetailView.get_license_clarity_data

        scan_summary = self.data_location / "is-npm-1.0.0_scan_package_summary.json"
        scan_summary_json = json.loads(scan_summary.read_text())
        license_clarity_data = get_license_clarity_data(scan_summary_json)

        self.assertEqual(7, len(license_clarity_data))
        expected = ["label", "value", "help_text", "weight"]
        self.assertEqual(expected, list(license_clarity_data[0].keys()))

        score_entry = license_clarity_data[-1]
        self.assertEqual("Score", score_entry.get("label"))
        self.assertEqual(90, score_entry.get("value"))
        self.assertIsNone(score_entry.get("weight"))

    def test_scanpipe_views_project_details_get_scan_summary_data(self):
        get_scan_summary_data = ProjectDetailView.get_scan_summary_data

        scan_summary = self.data_location / "is-npm-1.0.0_scan_package_summary.json"
        scan_summary_json = json.loads(scan_summary.read_text())
        scan_summary_data = get_scan_summary_data(scan_summary_json)

        self.assertEqual(6, len(scan_summary_data))
        expected = [
            "Declared license",
            "Declared holder",
            "Primary language",
            "Other licenses",
            "Other holders",
            "Other languages",
        ]
        self.assertEqual(expected, list(scan_summary_data.keys()))

    def test_scanpipe_views_project_archive_view(self):
        url = reverse("project_archive", args=[self.project1.uuid])
        run = self.project1.add_pipeline("docker")
        run.set_task_started(run.pk)

        response = self.client.post(url, follow=True)
        expected = (
            "Cannot execute this action until all associated pipeline runs "
            "are completed."
        )
        self.assertContains(response, expected)

        run.set_task_ended(exitcode=0)
        response = self.client.post(url, follow=True)
        expected = "has been archived."
        self.assertContains(response, expected)
        self.project1.refresh_from_db()
        self.assertTrue(self.project1.is_archived)

    def test_scanpipe_views_project_delete_view(self):
        url = reverse("project_delete", args=[self.project1.uuid])
        run = self.project1.add_pipeline("docker")
        run.set_task_started(run.pk)

        response = self.client.post(url, follow=True)
        expected = (
            "Cannot execute this action until all associated pipeline runs "
            "are completed."
        )
        self.assertContains(response, expected)

        run.set_task_ended(exitcode=0)
        response = self.client.post(url, follow=True)
        expected = "all its related data have been removed."
        self.assertContains(response, expected)
        self.assertFalse(Project.objects.filter(name=self.project1.name).exists())

    def test_scanpipe_views_project_reset_view(self):
        url = reverse("project_reset", args=[self.project1.uuid])
        run = self.project1.add_pipeline("docker")
        run.set_task_started(run.pk)

        response = self.client.post(url, follow=True)
        expected = (
            "Cannot execute this action until all associated pipeline runs "
            "are completed."
        )
        self.assertContains(response, expected)

        run.set_task_ended(exitcode=0)
        response = self.client.post(url, follow=True)
        expected = "have been removed."
        self.assertContains(response, expected)
        self.assertTrue(Project.objects.filter(name=self.project1.name).exists())

    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_views_execute_pipeline_view(self, mock_execute_task):
        run = self.project1.add_pipeline("docker")
        url = reverse("project_execute_pipeline", args=[self.project1.pk, run.uuid])

        response = self.client.get(url, follow=True)
        expected = f"Pipeline {run.pipeline_name} run started."
        self.assertContains(response, expected)
        mock_execute_task.assert_called_once()

        run.set_task_queued()
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

        run.set_task_started(run.pk)
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

        run.set_task_stopped()
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

    @mock.patch("scanpipe.models.Run.stop_task")
    def test_scanpipe_views_stop_pipeline_view(self, mock_stop_task):
        run = self.project1.add_pipeline("docker")
        url = reverse("project_stop_pipeline", args=[self.project1.pk, run.uuid])

        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

        run.set_task_started(run.pk)
        response = self.client.get(url, follow=True)
        expected = f"Pipeline {run.pipeline_name} stopped."
        self.assertContains(response, expected)
        mock_stop_task.assert_called_once()

    @mock.patch("scanpipe.models.Run.delete_task")
    def test_scanpipe_views_delete_pipeline_view(self, mock_delete_task):
        run = self.project1.add_pipeline("docker")
        url = reverse("project_delete_pipeline", args=[self.project1.pk, run.uuid])

        response = self.client.get(url, follow=True)
        expected = f"Pipeline {run.pipeline_name} deleted."
        self.assertContains(response, expected)
        mock_delete_task.assert_called_once()

        run.set_task_stopped()
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

    def test_scanpipe_views_run_status_view(self):
        run = self.project1.add_pipeline("docker")
        url = reverse("run_status", args=[run.uuid])

        response = self.client.get(url)
        expected = '<span class="tag is-light">Not started</span>'
        self.assertContains(response, expected)

        run.set_task_queued()
        run.refresh_from_db()
        response = self.client.get(url)
        expected = '<i class="fas fa-clock mr-1"></i>Queued'
        self.assertContains(response, expected)
        self.assertContains(response, f'hx-get="{url}?current_status={run.status}"')

        run.current_step = "1/2 Step A"
        run.set_task_started(run.pk)
        run.refresh_from_db()
        response = self.client.get(url)
        expected = (
            '<i class="fas fa-spinner fa-pulse mr-1" aria-hidden="true"></i>Running'
        )
        self.assertContains(response, expected)
        self.assertContains(response, f'hx-get="{url}?current_status={run.status}"')

        response = self.client.get(url, data={"display_current_step": True})
        expected = (
            f'hx-get="{url}?current_status={run.status}&display_current_step=True"'
        )
        self.assertContains(response, expected)
        self.assertContains(response, "1/2 Step A")

        run.set_task_ended(exitcode=1)
        response = self.client.get(url)
        expected = '<span class="tag is-danger">Failure</span>'
        self.assertContains(response, expected)

        run.set_task_ended(exitcode=0)
        response = self.client.get(url)
        expected = '<span class="tag is-success">Success</span>'
        self.assertContains(response, expected)

        run.set_task_staled()
        response = self.client.get(url)
        expected = '<span class="tag is-dark">Stale</span>'
        self.assertContains(response, expected)

        run.set_task_stopped()
        response = self.client.get(url)
        expected = '<span class="tag is-danger">Stopped</span>'
        self.assertContains(response, expected)

    def test_scanpipe_views_codebase_resource_details_annotations_missing_policy(self):
        resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path="resource1",
            licenses=[{"key": "key", "policy": None, "start_line": 1, "end_line": 2}],
        )
        url = resource1.get_absolute_url()

        response = self.client.get(url)
        expected = (
            '{"start_line": 1, "end_line": 2, "text": null, "className": "ace_info"}'
        )
        self.assertContains(response, expected)

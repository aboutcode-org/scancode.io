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

from pathlib import Path
from unittest import mock

from django.apps import apps
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.tests import license_policies_index

scanpipe_app = apps.get_app_config("scanpipe")


@override_settings(SCANCODEIO_REQUIRE_AUTHENTICATION=False)
class ScanPipeViewsTest(TestCase):
    data_location = Path(__file__).parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_views_project_list_is_archived(self):
        project2 = Project.objects.create(name="project2", is_archived=True)
        url = reverse("project_list")
        url_with_filter = url + "?is_archived=true"

        response = self.client.get(url)
        self.assertContains(response, self.project1.name)
        self.assertNotContains(response, project2.name)
        self.assertContains(response, url)
        self.assertContains(response, url_with_filter)

        response = self.client.get(url_with_filter)
        self.assertNotContains(response, self.project1.name)
        self.assertContains(response, project2.name)

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

    def test_scanpipe_views_project_details_compliance_alert(self):
        url = self.project1.get_absolute_url()
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

    def test_scanpipe_views_codebase_resource_details_annotations_missing_policy(self):
        resource1 = CodebaseResource.objects.create(
            project=self.project1,
            licenses=[{"key": "key", "policy": None, "start_line": 1, "end_line": 2}],
        )
        url = resource1.get_absolute_url()

        response = self.client.get(url)
        expected = (
            '{"licenses": [{"start_line": 1, "end_line": 2, "text": null, '
            '"type": "info"}]'
        )
        self.assertContains(response, expected)

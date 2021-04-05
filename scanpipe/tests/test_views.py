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

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.tests import license_policies_index

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipeViewsTest(TestCase):
    data_location = Path(__file__).parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

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
        expected = 'id="complianceAlertChart"'

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

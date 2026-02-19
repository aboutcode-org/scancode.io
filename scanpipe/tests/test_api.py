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
import json
import uuid
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

import openpyxl
from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIClient

from scanpipe.api.serializers import CodebaseRelationSerializer
from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredDependencySerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import ProjectMessageSerializer
from scanpipe.api.serializers import ProjectSerializer
from scanpipe.api.serializers import get_model_serializer
from scanpipe.api.serializers import get_serializer_fields
from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectMessage
from scanpipe.models import Run
from scanpipe.models import WebhookSubscription
from scanpipe.pipes.input import copy_input
from scanpipe.pipes.output import JSONResultsGenerator
from scanpipe.tests import dependency_data1
from scanpipe.tests import filter_warnings
from scanpipe.tests import make_message
from scanpipe.tests import make_package
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_file
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1


# TransactionTestCase is required for the Run related actions that use
# the transaction.on_commit() signal
class ScanPipeAPITest(TransactionTestCase):
    data = Path(__file__).parent / "data"

    def setUp(self):
        self.project1 = make_project(name="Analysis")
        self.resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        self.discovered_package1 = self.resource1.create_and_add_package(package_data1)
        self.discovered_dependency1 = DiscoveredDependency.create_from_data(
            self.project1, dependency_data1
        )
        self.codebase_relation1 = CodebaseRelation.objects.create(
            project=self.project1,
            from_resource=self.resource1,
            to_resource=self.resource1,
            map_type="java_to_class",
        )

        self.project_list_url = reverse("project-list")
        self.project1_detail_url = reverse("project-detail", args=[self.project1.uuid])

        self.user = User.objects.create_user("username", "e@mail.com", "secret")
        self.auth = f"Token {self.user.auth_token.key}"

        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.csrf_client.credentials(HTTP_AUTHORIZATION=self.auth)

    def test_scanpipe_api_browsable_formats_available(self):
        response = self.csrf_client.get(self.project_list_url + "?format=api")
        self.assertContains(response, self.project1_detail_url)
        response = self.csrf_client.get(self.project_list_url + "?format=admin")
        self.assertContains(response, self.project1_detail_url)
        response = self.csrf_client.get(self.project_list_url + "?format=json")
        self.assertContains(response, self.project1_detail_url)

    def test_scanpipe_api_project_list(self):
        make_project(name="2")
        make_project(name="3")

        with self.assertNumQueries(8):
            response = self.csrf_client.get(self.project_list_url)

        self.assertContains(response, self.project1_detail_url)
        self.assertEqual(3, response.data["count"])
        self.assertContains(response, "input_sources")
        self.assertNotContains(response, "input_root")
        self.assertNotContains(response, "next_run")
        self.assertNotContains(response, "extra_data")
        self.assertNotContains(response, "message_count")
        self.assertNotContains(response, "resource_count")
        self.assertNotContains(response, "package_count")
        self.assertNotContains(response, "dependency_count")

    def test_scanpipe_api_project_list_filters(self):
        project2 = make_project(name="pro2ject", is_archived=True)
        project3 = make_project(name="3project", is_archived=True)

        response = self.csrf_client.get(self.project_list_url)
        self.assertEqual(3, response.data["count"])
        self.assertContains(response, self.project1.uuid)
        self.assertContains(response, project2.uuid)
        self.assertContains(response, project3.uuid)

        data = {"uuid": self.project1.uuid}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, self.project1.uuid)
        self.assertNotContains(response, project2.uuid)
        self.assertNotContains(response, project3.uuid)

        data = {"name": project2.name}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, self.project1.uuid)
        self.assertContains(response, project2.uuid)
        self.assertNotContains(response, project3.uuid)

        data = {"name__contains": "2"}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, self.project1.uuid)
        self.assertContains(response, project2.uuid)
        self.assertNotContains(response, project3.uuid)

        data = {"name__startswith": project3.name}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, self.project1.uuid)
        self.assertNotContains(response, project2.uuid)
        self.assertContains(response, project3.uuid)

        data = {"name__endswith": self.project1.name[-3:]}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, self.project1.uuid)
        self.assertNotContains(response, project2.uuid)
        self.assertNotContains(response, project3.uuid)

        data = {"names": f"{self.project1.name[2:5]}, {project2.name}, "}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(2, response.data["count"])
        self.assertContains(response, self.project1.uuid)
        self.assertContains(response, project2.uuid)
        self.assertNotContains(response, project3.uuid)

        data = {"is_archived": True}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(2, response.data["count"])
        self.assertNotContains(response, self.project1.uuid)
        self.assertContains(response, project2.uuid)
        self.assertContains(response, project3.uuid)

        project2.labels.add("label1")
        project3.labels.add("label1")
        data = {"label": "label1"}
        response = self.csrf_client.get(self.project_list_url, data=data)
        self.assertEqual(2, response.data["count"])
        self.assertNotContains(response, self.project1.uuid)
        self.assertContains(response, project2.uuid)
        self.assertContains(response, project3.uuid)

    def test_scanpipe_api_project_detail(self):
        response = self.csrf_client.get(self.project1_detail_url)
        self.assertIn(self.project1_detail_url, response.data["url"])
        self.assertEqual(str(self.project1.uuid), response.data["uuid"])
        self.assertEqual(self.project1.name, response.data["name"])
        self.assertEqual([], response.data["input_sources"])
        self.assertIn("input_root", response.data)
        self.assertIn("extra_data", response.data)
        self.assertEqual(0, response.data["message_count"])
        self.assertEqual(1, response.data["resource_count"])
        self.assertEqual(1, response.data["package_count"])
        self.assertEqual(1, response.data["dependency_count"])
        self.assertEqual(1, response.data["relation_count"])
        self.assertEqual(
            f"http://testserver/api/projects/{self.project1.uuid}/results/",
            response.data["results_url"],
        )
        self.assertEqual(
            f"http://testserver/api/projects/{self.project1.uuid}/summary/",
            response.data["summary_url"],
        )

        expected = {"": 1}
        self.assertEqual(expected, response.data["codebase_resources_summary"])

        expected = {
            "total": 1,
            "with_missing_resources": 0,
            "with_modified_resources": 0,
        }
        self.assertEqual(expected, response.data["discovered_packages_summary"])

        expected = {
            "total": 1,
            "is_runtime": 1,
            "is_optional": 0,
            "is_pinned": 0,
        }
        self.assertEqual(expected, response.data["discovered_dependencies_summary"])

        expected = {"java_to_class": 1}
        self.assertEqual(expected, response.data["codebase_relations_summary"])

        input1 = self.project1.add_input_source(filename="file1", is_uploaded=True)
        input2 = self.project1.add_input_source(
            filename="file2", download_url="https://download.url"
        )

        response = self.csrf_client.get(self.project1_detail_url)
        expected = [
            {
                "filename": "file1",
                "download_url": "",
                "is_uploaded": True,
                "tag": "",
                "exists": False,
                "uuid": str(input1.uuid),
            },
            {
                "filename": "file2",
                "download_url": "https://download.url",
                "is_uploaded": False,
                "tag": "",
                "exists": False,
                "uuid": str(input2.uuid),
            },
        ]
        self.assertEqual(expected, response.data["input_sources"])

    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_api_project_create_base(self, mock_execute_pipeline_task):
        data = {}
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {
            "name": [ErrorDetail(string="This field is required.", code="required")]
        }
        self.assertEqual(expected, response.data)

        data = {"name": "A project name"}
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(data["name"], response.data["name"])
        project = Project.objects.get(name=data["name"])
        self.assertEqual({}, project.extra_data)

        data = {
            "name": "Name",
            "pipeline": "wrong_pipeline",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {
            "pipeline": [
                ErrorDetail(
                    string='"wrong_pipeline" is not a valid choice.',
                    code="invalid_choice",
                )
            ]
        }
        self.assertEqual(expected, response.data)

        data = {
            "name": "Name",
            "pipeline": "analyze_docker_image",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(data["pipeline"], response.data["runs"][0]["pipeline_name"])
        mock_execute_pipeline_task.assert_not_called()

        data = {
            "name": "OtherName",
            "pipeline": "analyze_docker_image",
            "upload_file": io.BytesIO(b"Content"),
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(data["pipeline"], response.data["runs"][0]["pipeline_name"])
        mock_execute_pipeline_task.assert_not_called()
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        self.assertEqual(["upload_file"], response.data["input_root"])

        data = {
            "name": "BetterName",
            "pipeline": "analyze_docker_image",
            "upload_file": io.BytesIO(b"Content"),
            "upload_file_tag": "tag value",
            "execute_now": True,
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        mock_execute_pipeline_task.assert_called_once()
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        self.assertEqual(["upload_file"], response.data["input_root"])
        self.assertEqual("tag value", response.data["input_sources"][0]["tag"])

        data = {
            "name": "Upload",
            "input_urls": ["https://example.com/archive.zip"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        expected = [
            {
                "filename": "",
                "download_url": "https://example.com/archive.zip",
                "is_uploaded": False,
                "tag": "",
                "exists": False,
                "uuid": response.data["input_sources"][0]["uuid"],
            }
        ]
        self.assertEqual(expected, response.data["input_sources"])

        data = {
            "name": "Upload 2 archives",
            "input_urls": [
                "https://example.com/archive.zip",
                "https://example.com/second.tar.gz",
            ],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        expected = [
            {
                "filename": "",
                "download_url": "https://example.com/archive.zip",
                "is_uploaded": False,
                "tag": "",
                "exists": False,
                "uuid": response.data["input_sources"][0]["uuid"],
            },
            {
                "filename": "",
                "download_url": "https://example.com/second.tar.gz",
                "is_uploaded": False,
                "tag": "",
                "exists": False,
                "uuid": response.data["input_sources"][1]["uuid"],
            },
        ]
        self.assertEqual(expected, response.data["input_sources"])

    def test_scanpipe_api_project_create_input_urls(self):
        url1 = "https://example.com/1.zip#from"
        url2 = "https://example.com/2.zip#to"
        data = {
            "name": "Inputs as list",
            "input_urls": [url1, url2],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(2, len(response.data["input_sources"]))

        data = {
            "name": "Inputs as string",
            "input_urls": f"{url1} {url2}",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(2, len(response.data["input_sources"]))

        data = {
            "name": "Inputs as list of string",
            "input_urls": [f"{url1} {url2}"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(2, len(response.data["input_sources"]))

        data = {
            "name": "Inputs as mixed content",
            "input_urls": [f"{url1} {url2}", "https://example.com/3.zip"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(3, len(response.data["input_sources"]))

    def test_scanpipe_api_project_create_multiple_pipelines(self):
        data = {
            "name": "Single string",
            "pipeline": "analyze_docker_image",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(
            "analyze_docker_image", response.data["runs"][0]["pipeline_name"]
        )

        data = {
            "name": "Single list",
            "pipeline": ["analyze_docker_image"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(
            "analyze_docker_image", response.data["runs"][0]["pipeline_name"]
        )

        data = {
            "name": "Multi list",
            "pipeline": ["analyze_docker_image", "scan_single_package"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(2, len(response.data["runs"]))
        self.assertEqual(
            "analyze_docker_image", response.data["runs"][0]["pipeline_name"]
        )
        self.assertEqual(
            "scan_single_package", response.data["runs"][1]["pipeline_name"]
        )

        # Not supported as the comma `,` is used as the separator for optional steps.
        data = {
            "name": "Multi string",
            "pipeline": "analyze_docker_image,scan_single_package",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {
            "pipeline": [
                ErrorDetail(
                    string='"analyze_docker_image,scan_single_package" is not a valid '
                    "choice.",
                    code="invalid_choice",
                )
            ]
        }
        self.assertEqual(expected, response.data)

    @filter_warnings("ignore", category=DeprecationWarning, module="scanpipe")
    def test_scanpipe_api_project_create_pipeline_old_name_compatibility(self):
        data = {
            "name": "Single string",
            "pipeline": "docker",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(
            "analyze_docker_image", response.data["runs"][0]["pipeline_name"]
        )

        data = {
            "name": "Multi list",
            "pipeline": ["docker_windows", "scan_package"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(2, len(response.data["runs"]))
        self.assertEqual(
            "analyze_windows_docker_image", response.data["runs"][0]["pipeline_name"]
        )
        self.assertEqual(
            "scan_single_package", response.data["runs"][1]["pipeline_name"]
        )

    def test_scanpipe_api_project_create_labels(self):
        data = {
            "name": "Project1",
            "labels": ["label2", "label1"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(sorted(data["labels"]), response.data["labels"])
        project = Project.objects.get(name=data["name"])
        self.assertEqual(sorted(data["labels"]), list(project.labels.names()))

    def test_scanpipe_api_project_create_pipeline_groups(self):
        data = {
            "name": "Project1",
            "pipeline": "inspect_packages:StaticResolver",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(
            ["StaticResolver"], response.data["runs"][0]["selected_groups"]
        )
        run = Project.objects.get(name="Project1").runs.get()
        self.assertEqual("inspect_packages", run.pipeline_name)
        self.assertEqual(["StaticResolver"], run.selected_groups)

        data = {
            "name": "Mix of string and list plus selected groups",
            "pipeline": [
                "map_deploy_to_develop:Java,JavaScript",
                "inspect_packages:StaticResolver",
            ],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(
            "map_deploy_to_develop", response.data["runs"][0]["pipeline_name"]
        )
        self.assertEqual("inspect_packages", response.data["runs"][1]["pipeline_name"])
        self.assertEqual(
            ["Java", "JavaScript"], response.data["runs"][0]["selected_groups"]
        )
        self.assertEqual(
            ["StaticResolver"], response.data["runs"][1]["selected_groups"]
        )
        runs = Project.objects.get(name=data["name"]).runs.all()
        self.assertEqual("map_deploy_to_develop", runs[0].pipeline_name)
        self.assertEqual("inspect_packages", runs[1].pipeline_name)
        self.assertEqual(["Java", "JavaScript"], runs[0].selected_groups)
        self.assertEqual(["StaticResolver"], runs[1].selected_groups)

    def test_scanpipe_api_project_create_webhooks(self):
        data = {
            "name": "Project1",
            "webhooks": [
                {
                    "target_url": "https://1.com",
                    "trigger_on_each_run": False,
                    "include_summary": False,
                    "include_results": False,
                    "is_active": False,
                },
                {
                    "target_url": "https://2.com",
                    "trigger_on_each_run": True,
                    "include_summary": True,
                    "include_results": True,
                    "is_active": True,
                },
            ],
        }

        serializer = ProjectSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

        response = self.csrf_client.post(self.project_list_url, data, format="json")
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        project = Project.objects.get(name=data["name"])
        # Ordered by -created_date by default
        webhook_subscriptions = project.webhooksubscriptions.all()
        self.assertEqual("https://2.com", webhook_subscriptions[0].target_url)
        self.assertTrue(webhook_subscriptions[0].trigger_on_each_run)
        self.assertTrue(webhook_subscriptions[0].include_summary)
        self.assertTrue(webhook_subscriptions[0].include_results)
        self.assertTrue(webhook_subscriptions[0].is_active)

        self.assertEqual("https://1.com", webhook_subscriptions[1].target_url)
        self.assertFalse(webhook_subscriptions[1].trigger_on_each_run)
        self.assertFalse(webhook_subscriptions[1].include_summary)
        self.assertFalse(webhook_subscriptions[1].include_results)
        self.assertFalse(webhook_subscriptions[1].is_active)

    def test_scanpipe_api_project_results_generator(self):
        results_generator = JSONResultsGenerator(self.project1)
        results = json.loads("".join(results_generator))

        expected = ["dependencies", "files", "headers", "packages", "relations"]
        self.assertEqual(expected, sorted(results.keys()))

        self.assertEqual(1, len(results["dependencies"]))
        self.assertEqual(1, len(results["headers"]))
        self.assertEqual(1, len(results["files"]))
        self.assertEqual(1, len(results["packages"]))

    def test_scanpipe_api_project_action_results(self):
        url = reverse("project-results", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        response_value = response.getvalue()
        results = json.loads(response_value)

        expected = ["dependencies", "files", "headers", "packages", "relations"]
        self.assertEqual(expected, sorted(results.keys()))

        self.assertEqual(1, len(results["dependencies"]))
        self.assertEqual(1, len(results["headers"]))
        self.assertEqual(1, len(results["files"]))
        self.assertEqual(1, len(results["packages"]))

    def test_scanpipe_api_project_action_results_download(self):
        url = reverse("project-results-download", args=[self.project1.uuid])
        response = self.csrf_client.get(url)

        expected = 'attachment; filename="scancodeio_analysis.json"'
        self.assertEqual(expected, response["Content-Disposition"])
        self.assertEqual("application/json", response["Content-Type"])

        response_value = response.getvalue()
        results = json.loads(response_value)
        expected = ["dependencies", "files", "headers", "packages", "relations"]
        self.assertEqual(expected, sorted(results.keys()))

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_api_project_action_results_download_output_formats(self):
        url = reverse("project-results-download", args=[self.project1.uuid])
        data = {"output_format": "cyclonedx"}
        response = self.csrf_client.get(url, data=data)

        expected_filename = "scancodeio_analysis_results-2010-10-10-10-10-10.cdx.json"
        expected = f'attachment; filename="{expected_filename}"'
        self.assertEqual(expected, response["Content-Disposition"])
        self.assertEqual("application/json", response["Content-Type"])

        response_value = response.getvalue()
        results = json.loads(response_value)
        self.assertIn("$schema", sorted(results.keys()))

        data = {
            "output_format": "cyclonedx",
            "version": "1.5",
        }
        response = self.csrf_client.get(url, data=data)
        response_value = response.getvalue()
        results = json.loads(response_value)
        self.assertEqual(
            "http://cyclonedx.org/schema/bom-1.5.schema.json", results["$schema"]
        )
        self.assertEqual("1.5", results["specVersion"])

        data = {"output_format": "xlsx"}
        response = self.csrf_client.get(url, data=data)
        expected = [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        ]
        self.assertIn(response["Content-Type"], expected)
        # Forces Django to finish the response and close the file
        # to prevent a "ResourceWarning: unclosed file"
        self.assertTrue(response.getvalue().startswith(b"PK"))

        data = {"output_format": "all_formats"}
        response = self.csrf_client.get(url, data=data)
        expected = ["application/zip"]
        self.assertIn(response["Content-Type"], expected)

        data = {"output_format": "all_outputs"}
        response = self.csrf_client.get(url, data=data)
        expected = ["application/zip"]
        self.assertIn(response["Content-Type"], expected)

    def test_scanpipe_api_project_action_pipelines(self):
        url = reverse("project-pipelines")
        response = self.csrf_client.get(url)
        expected = ["name", "summary", "description", "steps", "available_groups"]
        self.assertEqual(expected, list(response.data[0].keys()))

    def test_scanpipe_api_project_action_report(self):
        url = reverse("project-report")

        response = self.csrf_client.get(url)
        self.assertEqual(400, response.status_code)
        expected = (
            "Specifies the model to include in the XLSX report. Using: ?model=MODEL"
        )
        self.assertEqual(expected, response.data["error"])

        data = {"model": "bad value"}
        response = self.csrf_client.get(url, data=data)
        self.assertEqual(400, response.status_code)
        expected = "bad value is not on of the valid choices"
        self.assertEqual(expected, response.data["error"])

        make_package(self.project1, package_url="pkg:generic/p1")
        project2 = make_project()
        project2.labels.add("label1")
        package2 = make_package(project2, package_url="pkg:generic/p2")

        data = {
            "model": "package",
            "label": "label1",
        }
        response = self.csrf_client.get(url, data=data)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.filename.startswith("scancodeio-report-"))
        self.assertTrue(response.filename.endswith(".xlsx"))

        output_file = io.BytesIO(b"".join(response.streaming_content))
        workbook = openpyxl.load_workbook(output_file, read_only=True, data_only=True)
        self.assertEqual(["PACKAGES"], workbook.sheetnames)

        todos_sheet = workbook["PACKAGES"]
        rows = list(todos_sheet.values)
        self.assertEqual(2, len(rows))
        self.assertEqual("project", rows[0][0])  # header row
        self.assertEqual(project2.name, rows[1][0])
        self.assertEqual(package2.package_url, rows[1][1])

    def test_scanpipe_api_project_action_resources(self):
        url = reverse("project-resources", args=[self.project1.uuid])
        response = self.csrf_client.get(url)

        self.assertEqual(1, response.data["count"])
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        self.assertEqual(1, len(response.data["results"]))

        resource = response.data["results"][0]
        self.assertEqual(
            ["pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b"],
            resource["for_packages"],
        )
        self.assertEqual(
            "daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO", resource["path"]
        )

        self.assertEqual("", resource["compliance_alert"])

        # Using update() to bypass the `compute_compliance_alert` call triggered
        # when using save().
        # The purpose of this test is not to assert on the compliance_alert computation
        # but rather to test the render in the REST API.
        CodebaseResource.objects.filter(id=self.resource1.id).update(
            compliance_alert=CodebaseResource.Compliance.ERROR
        )

        response = self.csrf_client.get(url)
        self.assertEqual("error", response.data["results"][0]["compliance_alert"])

    def test_scanpipe_api_project_action_resources_filterset(self):
        make_resource_file(
            self.project1,
            path="path/",
        )
        url = reverse("project-resources", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(2, response.data["count"])

        response = self.csrf_client.get(url + "?path=path/")
        self.assertEqual(1, response.data["count"])
        package = response.data["results"][0]
        self.assertEqual("path/", package["path"])

        response = self.csrf_client.get(url + "?path=unknown")
        self.assertEqual(0, response.data["count"])

        response = self.csrf_client.get(url + "?compliance_alert=a")
        self.assertEqual(400, response.status_code)
        expected = {
            "compliance_alert": [
                "Select a valid choice. a is not one of the available choices."
            ]
        }
        self.assertEqual(expected, response.data["errors"])

        # Using a field name available on the Project model to make sure the
        # ProjectFilterSet is bypassed.
        response = self.csrf_client.get(url + "?slug=aaa")
        self.assertEqual(2, response.data["count"])

    def test_scanpipe_api_project_action_packages(self):
        url = reverse("project-packages", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(1, response.data["count"])
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        self.assertEqual(1, len(response.data["results"]))

        package = response.data["results"][0]
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", package["purl"])
        self.assertEqual("adduser", package["name"])

    def test_scanpipe_api_project_action_packages_filterset(self):
        make_package(self.project1, package_url="pkg:generic/name@1.0")
        url = reverse("project-packages", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(2, response.data["count"])

        response = self.csrf_client.get(url + "?version=1.0")
        self.assertEqual(1, response.data["count"])
        package = response.data["results"][0]
        self.assertEqual("pkg:generic/name@1.0", package["purl"])

        response = self.csrf_client.get(url + "?version=2.0")
        self.assertEqual(0, response.data["count"])

        response = self.csrf_client.get(url + "?size=a")
        self.assertEqual(400, response.status_code)
        self.assertEqual({"size": ["Enter a number."]}, response.data["errors"])

    def test_scanpipe_api_project_action_dependencies(self):
        url = reverse("project-dependencies", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(1, response.data["count"])
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        self.assertEqual(1, len(response.data["results"]))

        dependency = response.data["results"][0]
        self.assertEqual(dependency_data1["purl"], dependency["purl"])
        self.assertEqual(dependency_data1["scope"], dependency["scope"])
        self.assertEqual(dependency_data1["is_runtime"], dependency["is_runtime"])
        self.assertEqual(
            dependency_data1["dependency_uid"], dependency["dependency_uid"]
        )

    def test_scanpipe_api_project_action_relations(self):
        url = reverse("project-relations", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(1, response.data["count"])
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        self.assertEqual(1, len(response.data["results"]))

        relation = response.data["results"][0]
        expected = {
            "to_resource": "daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
            "status": "",
            "map_type": "java_to_class",
            "score": "",
            "from_resource": "daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        }
        self.assertEqual(expected, relation)

    def test_scanpipe_api_project_action_relations_filterset(self):
        url = reverse("project-relations", args=[self.project1.uuid])
        response = self.csrf_client.get(url + "?map_type=about_file")
        self.assertEqual(0, response.data["count"])

        map_type = self.codebase_relation1.map_type
        response = self.csrf_client.get(url + f"?map_type={map_type}")
        self.assertEqual(1, response.data["count"])

    def test_scanpipe_api_project_action_messages(self):
        url = reverse("project-messages", args=[self.project1.uuid])
        make_message(self.project1, description="Error")

        response = self.csrf_client.get(url)
        self.assertEqual(1, response.data["count"])
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        self.assertEqual(1, len(response.data["results"]))

        message = response.data["results"][0]
        self.assertEqual("error", message["severity"])
        self.assertEqual("Error", message["description"])
        self.assertEqual({}, message["details"])

    def test_scanpipe_api_project_action_file_content(self):
        url = reverse("project-file-content", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Resource not found. Use ?path=<resource_path>"}
        self.assertEqual(expected, response.data)

        response = self.csrf_client.get(url + f"?path={self.resource1.path}")
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "File not available"}
        self.assertEqual(expected, response.data)

    def test_scanpipe_api_project_action_summary(self):
        url = reverse("project-summary", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"error": "Summary file not available"}
        self.assertEqual(expected, response.data)

        summary_file = self.data / "scancode" / "is-npm-1.0.0_scan_package_summary.json"
        copy_input(summary_file, self.project1.output_path)

        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(10, len(response.data.keys()))

    def test_scanpipe_api_project_action_delete(self):
        run = self.project1.add_pipeline("analyze_docker_image")
        run.set_task_started(task_id=uuid.uuid4())
        self.assertEqual(run.Status.RUNNING, run.status)

        response = self.csrf_client.delete(self.project1_detail_url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = "Cannot delete project while a run is in progress."
        self.assertEqual(expected, response.data["status"])

        run.set_task_ended(exitcode=0)
        self.assertEqual(run.Status.SUCCESS, run.status)
        response = self.csrf_client.delete(self.project1_detail_url)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertFalse(Project.objects.filter(pk=self.project1.pk).exists())

    def test_scanpipe_api_project_action_archive(self):
        (self.project1.input_path / "input_file").touch()
        (self.project1.codebase_path / "codebase_file").touch()
        self.assertEqual(1, len(Project.get_root_content(self.project1.input_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.codebase_path)))

        url = reverse("project-archive", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn(
            "POST on this URL to archive the project.", response.data["status"]
        )

        data = {"remove_input": True}
        response = self.csrf_client.post(url, data=data)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.project1.refresh_from_db()
        self.assertTrue(self.project1.is_archived)
        expected = {"status": "The project Analysis has been archived."}
        self.assertEqual(expected, response.data)
        self.assertEqual(0, len(Project.get_root_content(self.project1.input_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.codebase_path)))

    def test_scanpipe_api_project_action_reset(self):
        self.project1.add_pipeline("analyze_docker_image")
        self.assertEqual(1, self.project1.runs.count())
        self.assertEqual(1, self.project1.codebaseresources.count())
        self.assertEqual(1, self.project1.discoveredpackages.count())

        (self.project1.input_path / "input_file").touch()
        (self.project1.codebase_path / "codebase_file").touch()
        self.assertEqual(1, len(Project.get_root_content(self.project1.input_path)))
        self.assertEqual(1, len(Project.get_root_content(self.project1.codebase_path)))

        url = reverse("project-reset", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIn("POST on this URL to reset the project.", response.data["status"])

        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": "The Analysis project has been reset."}
        self.assertEqual(expected, response.data)
        self.assertEqual(0, self.project1.runs.count())
        self.assertEqual(0, self.project1.codebaseresources.count())
        self.assertEqual(0, self.project1.discoveredpackages.count())
        self.assertEqual(1, len(Project.get_root_content(self.project1.input_path)))
        self.assertEqual(0, len(Project.get_root_content(self.project1.codebase_path)))

    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_api_project_action_add_pipeline(self, mock_execute_pipeline_task):
        url = reverse("project-add-pipeline", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual("Pipeline required.", response.data.get("status"))
        self.assertIn("analyze_docker_image", response.data.get("pipelines"))

        data = {"pipeline": "not_available"}
        response = self.csrf_client.post(url, data=data)
        expected = {"status": "not_available is not a valid pipeline."}
        self.assertEqual(expected, response.data)

        data = {"pipeline": "analyze_docker_image"}
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Pipeline added."}, response.data)
        mock_execute_pipeline_task.assert_not_called()

        self.assertEqual(1, self.project1.runs.count())
        run = self.project1.runs.get()
        self.assertEqual(data["pipeline"], run.pipeline_name)

        project2 = make_project(name="Analysis 2")
        url = reverse("project-add-pipeline", args=[project2.uuid])
        data["execute_now"] = True
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Pipeline added."}, response.data)
        mock_execute_pipeline_task.assert_called_once()

    @filter_warnings("ignore", category=DeprecationWarning, module="scanpipe")
    def test_scanpipe_api_project_action_add_pipeline_old_name_compatibility(self):
        url = reverse("project-add-pipeline", args=[self.project1.uuid])
        data = {
            "pipeline": "docker",  # old name
            "execute_now": False,
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Pipeline added."}, response.data)
        self.assertEqual("analyze_docker_image", self.project1.runs.get().pipeline_name)

    def test_scanpipe_api_project_action_add_pipeline_groups(self):
        url = reverse("project-add-pipeline", args=[self.project1.uuid])
        data = {
            "pipeline": "analyze_docker_image:group1,group2",
            "execute_now": False,
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Pipeline added."}, response.data)
        run = self.project1.runs.get()
        self.assertEqual("analyze_docker_image", run.pipeline_name)
        self.assertEqual(["group1", "group2"], run.selected_groups)

    def test_scanpipe_api_project_action_add_input(self):
        url = reverse("project-add-input", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        expected = "upload_file or input_urls required."
        self.assertEqual(expected, response.data.get("status"))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        data = {
            "input_urls": "https://example.com/archive.zip#tag",
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Input(s) added."}, response.data)
        input_source = self.project1.inputsources.get(is_uploaded=False)
        self.assertEqual("", input_source.filename)
        self.assertEqual(data["input_urls"], input_source.download_url)
        self.assertEqual("tag", input_source.tag)

        data = {
            "input_urls": ["docker://alpine", "docker://postgresql"],
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Input(s) added."}, response.data)
        input_sources = self.project1.inputsources.filter(
            download_url__startswith="docker://"
        )
        self.assertEqual(2, len(input_sources))

        data = {
            "upload_file": io.BytesIO(b"Content"),
            "upload_file_tag": "tag value",
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Input(s) added."}, response.data)
        expected = sorted(["upload_file"])
        self.assertEqual(expected, sorted(self.project1.input_root))
        input_source = self.project1.inputsources.get(is_uploaded=True)
        self.assertEqual("upload_file", input_source.filename)
        self.assertEqual("tag value", input_source.tag)

        run = self.project1.add_pipeline("analyze_docker_image")
        run.set_task_started(task_id=uuid.uuid4())
        response = self.csrf_client.get(url)
        expected = "Cannot add inputs once a pipeline has started to execute."
        self.assertEqual(expected, response.data.get("status"))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_scanpipe_api_project_action_add_webhook(self):
        url = reverse("project-add-webhook", args=[self.project1.uuid])

        # Test missing target_url
        response = self.csrf_client.post(url, data={})
        self.assertEqual(
            {"target_url": ["This field is required."]},
            response.data,
        )
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        # Test invalid URL
        data = {"target_url": "invalid-url"}
        response = self.csrf_client.post(url, data=data)
        self.assertIn("target_url", response.data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        # Test valid webhook creation
        data = {
            "target_url": "https://example.com/webhook",
            "trigger_on_each_run": True,
            "include_summary": True,
            "include_results": False,
            "is_active": True,
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Webhook added."}, response.data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        webhook = WebhookSubscription.objects.get(project=self.project1)
        self.assertEqual(webhook.target_url, data["target_url"])
        self.assertTrue(webhook.trigger_on_each_run)
        self.assertTrue(webhook.include_summary)
        self.assertFalse(webhook.include_results)
        self.assertTrue(webhook.is_active)

    def test_scanpipe_api_run_detail(self):
        run1 = self.project1.add_pipeline("analyze_docker_image")
        url = reverse("run-detail", args=[run1.uuid])
        response = self.csrf_client.get(url)

        self.assertEqual(str(run1.uuid), response.data["uuid"])
        self.assertIn(self.project1_detail_url, response.data["project"])
        self.assertEqual("analyze_docker_image", response.data["pipeline_name"])
        self.assertEqual("Analyze Docker images.", response.data["description"])
        self.assertEqual("", response.data["scancodeio_version"])
        self.assertIsNone(response.data["task_id"])
        self.assertIsNone(response.data["task_start_date"])
        self.assertIsNone(response.data["task_end_date"])
        self.assertEqual("", response.data["task_output"])
        self.assertIsNone(response.data["execution_time"])
        self.assertEqual(Run.Status.NOT_STARTED, response.data["status"])

    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_api_run_action_start_pipeline(self, mock_execute_task):
        run1 = self.project1.add_pipeline("analyze_docker_image")
        url = reverse("run-start-pipeline", args=[run1.uuid])
        response = self.csrf_client.post(url)
        expected = {"status": "Pipeline analyze_docker_image started."}
        self.assertEqual(expected, response.data)
        mock_execute_task.assert_called_once()

        run1.task_id = uuid.uuid4()
        run1.save()
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Pipeline already queued."}
        self.assertEqual(expected, response.data)

        run1.task_start_date = timezone.now()
        run1.save()
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Pipeline already started."}
        self.assertEqual(expected, response.data)

        run1.task_end_date = timezone.now()
        run1.save()
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Pipeline already executed."}
        self.assertEqual(expected, response.data)

    @override_settings(SCANCODEIO_ASYNC=False)
    def test_scanpipe_api_run_action_stop_pipeline(self):
        run1 = self.project1.add_pipeline("analyze_docker_image")
        url = reverse("run-stop-pipeline", args=[run1.uuid])
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Pipeline is not running."}
        self.assertEqual(expected, response.data)

        run1.set_task_started(run1.pk)
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": "Pipeline analyze_docker_image stopped."}
        self.assertEqual(expected, response.data)

        run1.refresh_from_db()
        self.assertTrue(run1.task_stopped)

    @override_settings(SCANCODEIO_ASYNC=False)
    def test_scanpipe_api_run_action_delete_pipeline(self):
        run1 = self.project1.add_pipeline("analyze_docker_image")
        url = reverse("run-delete-pipeline", args=[run1.uuid])

        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": "Pipeline analyze_docker_image deleted."}
        self.assertEqual(expected, response.data)
        self.assertFalse(Run.objects.filter(pk=run1.pk).exists())

        run2 = self.project1.add_pipeline("analyze_docker_image")
        url = reverse("run-delete-pipeline", args=[run2.uuid])

        run2.set_task_queued()
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": "Pipeline analyze_docker_image deleted."}
        self.assertEqual(expected, response.data)
        self.assertFalse(Run.objects.filter(pk=run2.pk).exists())

        run3 = self.project1.add_pipeline("analyze_docker_image")
        url = reverse("run-delete-pipeline", args=[run3.uuid])

        run3.set_task_started(run3.pk)
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Only non started or queued pipelines can be deleted."}
        self.assertEqual(expected, response.data)

        run3.set_task_ended(exitcode=0)
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Only non started or queued pipelines can be deleted."}
        self.assertEqual(expected, response.data)

        run3.set_task_stopped()
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Only non started or queued pipelines can be deleted."}
        self.assertEqual(expected, response.data)

    def test_scanpipe_api_project_action_outputs(self):
        url = reverse("project-outputs", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual([], response.data)

        output_file = self.project1.get_output_file_path("scan", "txt")
        output_file.write_text("content")
        response = self.csrf_client.get(url)
        download_url = f"http://testserver{url}?filename={output_file.name}"
        expected = [
            {
                "download_url": download_url,
                "filename": output_file.name,
            }
        ]
        self.assertEqual(expected, response.data)

        response = self.csrf_client.get(download_url)
        self.assertEqual(b"content", response.getvalue())

        response = self.csrf_client.get(f"http://testserver{url}?filename=NOT_FOUND")
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Output file NOT_FOUND not found"}
        self.assertEqual(expected, response.data)

    def test_scanpipe_api_project_action_compliance(self):
        project = make_project()
        url = reverse("project-compliance", args=[project.uuid])
        response = self.csrf_client.get(url)
        expected = {"compliance_alerts": {}}
        self.assertEqual(expected, response.data)

        make_resource_file(
            project,
            path="path/",
            compliance_alert=CodebaseResource.Compliance.WARNING,
        )
        make_package(
            project,
            package_url="pkg:generic/name@1.0",
            compliance_alert=CodebaseResource.Compliance.ERROR,
        )

        response = self.csrf_client.get(url)
        expected = {
            "compliance_alerts": {"packages": {"error": ["pkg:generic/name@1.0"]}}
        }
        self.assertEqual(expected, response.data)

        data = {"fail_level": "WARNING"}
        response = self.csrf_client.get(url, data=data)
        expected = {
            "compliance_alerts": {
                "packages": {"error": ["pkg:generic/name@1.0"]},
                "resources": {"warning": ["path/"]},
            }
        }
        self.assertDictEqual(expected, response.data)

    def test_scanpipe_api_project_action_license_clarity_compliance(self):
        project = make_project()
        url = reverse("project-license-clarity-compliance", args=[project.uuid])

        response = self.csrf_client.get(url)
        expected = {"license_clarity_compliance_alert": None}
        self.assertEqual(expected, response.data)

        project.update_extra_data({"license_clarity_compliance_alert": "ok"})
        response = self.csrf_client.get(url)
        expected = {"license_clarity_compliance_alert": "ok"}
        self.assertEqual(expected, response.data)

        project.update_extra_data({"license_clarity_compliance_alert": "error"})
        response = self.csrf_client.get(url)
        expected = {"license_clarity_compliance_alert": "error"}
        self.assertEqual(expected, response.data)

    def test_scanpipe_api_project_action_scorecard_compliance(self):
        project = make_project()
        url = reverse("project-scorecard-compliance", args=[project.uuid])

        response = self.csrf_client.get(url)
        expected = {"scorecard_compliance_alert": None}
        self.assertEqual(expected, response.data)

        project.update_extra_data({"scorecard_compliance_alert": "ok"})
        response = self.csrf_client.get(url)
        expected = {"scorecard_compliance_alert": "ok"}
        self.assertEqual(expected, response.data)

        project.update_extra_data({"scorecard_compliance_alert": "error"})
        response = self.csrf_client.get(url)
        expected = {"scorecard_compliance_alert": "error"}
        self.assertEqual(expected, response.data)

    def test_scanpipe_api_serializer_get_model_serializer(self):
        self.assertEqual(
            DiscoveredPackageSerializer, get_model_serializer(DiscoveredPackage)
        )
        self.assertEqual(
            DiscoveredDependencySerializer, get_model_serializer(DiscoveredDependency)
        )
        self.assertEqual(
            CodebaseResourceSerializer, get_model_serializer(CodebaseResource)
        )
        self.assertEqual(
            CodebaseRelationSerializer, get_model_serializer(CodebaseRelation)
        )
        self.assertEqual(ProjectMessageSerializer, get_model_serializer(ProjectMessage))

        with self.assertRaises(LookupError):
            get_model_serializer(None)

    def test_scanpipe_api_serializer_get_serializer_fields(self):
        self.assertEqual(49, len(get_serializer_fields(DiscoveredPackage)))
        self.assertEqual(14, len(get_serializer_fields(DiscoveredDependency)))
        self.assertEqual(38, len(get_serializer_fields(CodebaseResource)))
        self.assertEqual(5, len(get_serializer_fields(CodebaseRelation)))
        self.assertEqual(7, len(get_serializer_fields(ProjectMessage)))

        with self.assertRaises(LookupError):
            get_serializer_fields(None)

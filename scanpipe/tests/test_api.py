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
from unittest import mock

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIClient

from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import get_model_serializer
from scanpipe.api.serializers import get_serializer_fields
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.pipes.outputs import JSONResultsGenerator
from scanpipe.tests import package_data1


# TransactionTestCase is required for the Run related actions that use
# the transaction.on_commit() signal
class ScanPipeAPITest(TransactionTestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.codebase_resource1 = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )
        self.discovered_package1 = DiscoveredPackage.create_for_resource(
            package_data1, self.codebase_resource1
        )

        self.project_list_url = reverse("project-list")
        self.project1_detail_url = reverse("project-detail", args=[self.project1.uuid])

        self.user = User.objects.create_user("username", "e@mail.com", "secret")
        self.header_prefix = "Token "
        self.token = Token.objects.create(user=self.user)
        self.auth = self.header_prefix + self.token.key

        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.csrf_client.credentials(HTTP_AUTHORIZATION=self.auth)

    def test_scanpipe_api_project_list(self):
        response = self.csrf_client.get(self.project_list_url)

        self.assertContains(response, self.project1_detail_url)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, "input_root")
        self.assertNotContains(response, "extra_data")

    def test_scanpipe_api_project_detail(self):
        response = self.csrf_client.get(self.project1_detail_url)
        self.assertIn(self.project1_detail_url, response.data["url"])
        self.assertEqual(str(self.project1.uuid), response.data["uuid"])
        self.assertEqual(self.project1.name, response.data["name"])
        self.assertIn("input_root", response.data)
        self.assertIn("extra_data", response.data)

        expected = {"": 1}
        self.assertEqual(expected, response.data["codebase_resources_summary"])
        expected = {
            "total": 1,
            "with_missing_resources": 0,
            "with_modified_resources": 0,
        }
        self.assertEqual(expected, response.data["discovered_package_summary"])

    @mock.patch("scanpipe.models.Run.run_pipeline_task_async")
    def test_scanpipe_api_project_create(self, mock_run_pipeline_task):
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

        data = {"name": "Name", "pipeline": "wrong_pipeline"}
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

        data = {"name": "Name", "pipeline": "scanpipe/pipelines/docker.py"}
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(data["pipeline"], response.data["runs"][0]["pipeline"])
        self.assertEqual(data["pipeline"], response.data["next_run"])
        mock_run_pipeline_task.assert_not_called()

        data = {
            "name": "OtherName",
            "pipeline": "scanpipe/pipelines/docker.py",
            "upload_file": io.BytesIO(b"Content"),
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(data["pipeline"], response.data["runs"][0]["pipeline"])
        self.assertEqual(data["pipeline"], response.data["next_run"])
        mock_run_pipeline_task.assert_called_once()
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        self.assertEqual(["upload_file"], response.data["input_root"])

        data = {"name": "BetterName", "upload_file": io.BytesIO(b"Content")}
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(0, len(response.data["runs"]))
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        self.assertEqual(["upload_file"], response.data["input_root"])

    def test_scanpipe_api_project_results_generator(self):
        results_generator = JSONResultsGenerator(self.project1)
        results = json.loads("".join(results_generator))

        expected = ["files", "headers", "packages"]
        self.assertEqual(expected, sorted(results.keys()))

        self.assertEqual(1, len(results["headers"]))
        self.assertEqual(1, len(results["files"]))
        self.assertEqual(1, len(results["packages"]))

    def test_scanpipe_api_project_action_results(self):
        url = reverse("project-results", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        response_value = response.getvalue()
        results = json.loads(response_value)

        expected = ["files", "headers", "packages"]
        self.assertEqual(expected, sorted(results.keys()))

        self.assertEqual(1, len(results["headers"]))
        self.assertEqual(1, len(results["files"]))
        self.assertEqual(1, len(results["packages"]))

    def test_scanpipe_api_project_action_results_download(self):
        url = reverse("project-results-download", args=[self.project1.uuid])
        response = self.csrf_client.get(url)

        expected = 'attachment; filename="Analysis.json"'
        self.assertEqual(expected, response["Content-Disposition"])
        self.assertEqual("application/json", response["Content-Type"])

        response_value = response.getvalue()
        results = json.loads(response_value)
        expected = ["files", "headers", "packages"]
        self.assertEqual(expected, sorted(results.keys()))

    def test_scanpipe_api_project_action_pipelines(self):
        url = reverse("project-pipelines")
        response = self.csrf_client.get(url)
        docker_pipeline = response.data.get("docker")
        self.assertEqual(
            "scanpipe/pipelines/docker.py", docker_pipeline.get("location")
        )

    def test_scanpipe_api_project_action_resources(self):
        url = reverse("project-resources", args=[self.project1.uuid])
        response = self.csrf_client.get(url)

        self.assertEqual(1, len(response.data))
        resource = response.data[0]
        self.assertEqual(
            ["pkg:deb/debian/adduser@3.118?arch=all"], resource["for_packages"]
        )
        self.assertEqual("filename.ext", resource["path"])

    def test_scanpipe_api_project_action_packages(self):
        url = reverse("project-packages", args=[self.project1.uuid])
        response = self.csrf_client.get(url)

        self.assertEqual(1, len(response.data))
        package = response.data[0]
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", package["purl"])
        self.assertEqual("adduser", package["name"])

    def test_scanpipe_api_project_action_errors(self):
        url = reverse("project-errors", args=[self.project1.uuid])
        ProjectError.objects.create(
            project=self.project1, model="ModelName", details={}, message="Error"
        )

        response = self.csrf_client.get(url)
        self.assertEqual(1, len(response.data))
        error = response.data[0]
        self.assertEqual("ModelName", error["model"])
        self.assertEqual({}, error["details"])
        self.assertEqual("Error", error["message"])

    def test_scanpipe_api_project_action_file_content(self):
        url = reverse("project-file-content", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Resource not found. Use ?path=<resource_path>"}
        self.assertEqual(expected, response.data)

        response = self.csrf_client.get(url + f"?path={self.codebase_resource1.path}")
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "File not available"}
        self.assertEqual(expected, response.data)

    def test_scanpipe_api_project_action_add_pipeline(self):
        url = reverse("project-add-pipeline", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual("Pipeline required.", response.data.get("status"))
        self.assertIn("scanpipe/pipelines/docker.py", response.data.get("pipelines"))

        data = {"pipeline": "scanpipe/pipelines/docker.py"}
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Pipeline added."}, response.data)

        self.assertEqual(1, self.project1.runs.count())
        run = self.project1.runs.get()
        self.assertEqual(data["pipeline"], run.pipeline)

    def test_scanpipe_api_run_detail(self):
        run1 = self.project1.add_pipeline("scanpipe/pipelines/docker.py")
        url = reverse("run-detail", args=[run1.uuid])
        response = self.csrf_client.get(url)

        self.assertEqual(str(run1.uuid), response.data["uuid"])
        self.assertIn(self.project1_detail_url, response.data["project"])
        self.assertEqual("scanpipe/pipelines/docker.py", response.data["pipeline"])
        self.assertEqual(
            "A pipeline to analyze a Docker image.", response.data["description"]
        )
        self.assertIsNone(response.data["task_id"])
        self.assertIsNone(response.data["task_start_date"])
        self.assertIsNone(response.data["task_end_date"])
        self.assertEqual([], response.data["task_output"])
        self.assertIsNone(response.data["execution_time"])
        self.assertIsNone(response.data["run_id"])

        run1.task_output = "Workflow starting (run-id 1593181041039832):"
        run1.save()
        response = self.csrf_client.get(url)
        self.assertEqual("1593181041039832", response.data["run_id"])

    @mock.patch("scanpipe.models.Run.run_pipeline_task_async")
    def test_scanpipe_api_run_action_start_pipeline(self, mock_run_pipeline_task):
        run1 = self.project1.add_pipeline("scanpipe/pipelines/docker.py")
        url = reverse("run-start-pipeline", args=[run1.uuid])
        response = self.csrf_client.get(url)
        expected = {"status": "Pipeline scanpipe/pipelines/docker.py started."}
        self.assertEqual(expected, response.data)
        mock_run_pipeline_task.assert_called_once()

        run1.task_start_date = timezone.now()
        run1.save()
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Pipeline already started."}
        self.assertEqual(expected, response.data)

        run1.task_end_date = timezone.now()
        run1.save()
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Pipeline already executed."}
        self.assertEqual(expected, response.data)

    @mock.patch("scanpipe.models.Run.resume_pipeline_task_async")
    def test_scanpipe_api_run_action_resume_pipeline(self, mock_resume_pipeline_task):
        run1 = self.project1.add_pipeline("scanpipe/pipelines/docker.py")
        url = reverse("run-resume-pipeline", args=[run1.uuid])
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Cannot resume never started pipeline run."}
        self.assertEqual(expected, response.data)

        run1.task_exitcode = 0
        run1.save()
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Cannot resume a successful pipeline run."}
        self.assertEqual(expected, response.data)

        run1.task_exitcode = None
        run1.task_start_date = timezone.now()
        run1.save()
        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": f"Pipeline {run1.pipeline} resumed."}
        self.assertEqual(expected, response.data)
        mock_resume_pipeline_task.assert_called_once()

    def test_scanpipe_api_serializer_get_model_serializer(self):
        self.assertEqual(
            DiscoveredPackageSerializer, get_model_serializer(DiscoveredPackage)
        )
        self.assertEqual(
            CodebaseResourceSerializer, get_model_serializer(CodebaseResource)
        )
        with self.assertRaises(LookupError):
            get_model_serializer(None)

    def test_scanpipe_api_serializer_get_serializer_fields(self):
        self.assertEqual(28, len(get_serializer_fields(DiscoveredPackage)))
        self.assertEqual(20, len(get_serializer_fields(CodebaseResource)))
        with self.assertRaises(LookupError):
            get_serializer_fields(None)

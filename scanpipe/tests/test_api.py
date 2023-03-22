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

from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIClient

from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredDependencySerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import get_model_serializer
from scanpipe.api.serializers import get_serializer_fields
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.pipes.input import copy_input
from scanpipe.pipes.output import JSONResultsGenerator
from scanpipe.tests import dependency_data1
from scanpipe.tests import package_data1


# TransactionTestCase is required for the Run related actions that use
# the transaction.on_commit() signal
class ScanPipeAPITest(TransactionTestCase):
    data_location = Path(__file__).parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        self.discovered_package1 = self.resource1.create_and_add_package(package_data1)
        self.discovered_dependency1 = DiscoveredDependency.create_from_data(
            self.project1, dependency_data1
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
        response = self.csrf_client.get(self.project_list_url)

        self.assertContains(response, self.project1_detail_url)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, "input_root")
        self.assertNotContains(response, "extra_data")
        self.assertNotContains(response, "error_count")
        self.assertNotContains(response, "resource_count")
        self.assertNotContains(response, "package_count")
        self.assertNotContains(response, "dependency_count")

    def test_scanpipe_api_project_list_filters(self):
        project2 = Project.objects.create(name="pro2ject", is_archived=True)
        project3 = Project.objects.create(name="3project", is_archived=True)

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

    def test_scanpipe_api_project_detail(self):
        response = self.csrf_client.get(self.project1_detail_url)
        self.assertIn(self.project1_detail_url, response.data["url"])
        self.assertEqual(str(self.project1.uuid), response.data["uuid"])
        self.assertEqual(self.project1.name, response.data["name"])
        self.assertEqual([], response.data["input_sources"])
        self.assertIn("input_root", response.data)
        self.assertIn("extra_data", response.data)
        self.assertEqual(0, response.data["error_count"])
        self.assertEqual(1, response.data["resource_count"])
        self.assertEqual(1, response.data["package_count"])
        self.assertEqual(1, response.data["dependency_count"])

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
            "is_resolved": 0,
        }
        self.assertEqual(expected, response.data["discovered_dependencies_summary"])

        self.project1.add_input_source(filename="file1", source="uploaded")
        self.project1.add_input_source(filename="file2", source="https://download.url")
        self.project1.save()
        response = self.csrf_client.get(self.project1_detail_url)
        expected = [
            {"filename": "file1", "source": "uploaded"},
            {"filename": "file2", "source": "https://download.url"},
        ]
        self.assertEqual(expected, response.data["input_sources"])

    @mock.patch("requests.get")
    @mock.patch("scanpipe.models.Run.execute_task_async")
    def test_scanpipe_api_project_create(self, mock_execute_pipeline_task, mock_get):
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
            "pipeline": "docker",
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(data["pipeline"], response.data["runs"][0]["pipeline_name"])
        self.assertEqual(data["pipeline"], response.data["next_run"])
        mock_execute_pipeline_task.assert_not_called()

        data = {
            "name": "OtherName",
            "pipeline": "docker",
            "upload_file": io.BytesIO(b"Content"),
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        self.assertEqual(data["pipeline"], response.data["runs"][0]["pipeline_name"])
        self.assertEqual(data["pipeline"], response.data["next_run"])
        mock_execute_pipeline_task.assert_not_called()
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        self.assertEqual(["upload_file"], response.data["input_root"])

        data = {
            "name": "BetterName",
            "pipeline": "docker",
            "upload_file": io.BytesIO(b"Content"),
            "execute_now": True,
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(1, len(response.data["runs"]))
        mock_execute_pipeline_task.assert_called_once()
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        self.assertEqual(["upload_file"], response.data["input_root"])

        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url="archive.zip"
        )
        data = {
            "name": "Upload",
            "input_urls": ["https://example.com/archive.zip"],
        }
        response = self.csrf_client.post(self.project_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        created_project_detail_url = response.data["url"]
        response = self.csrf_client.get(created_project_detail_url)
        expected = {
            "filename": "archive.zip",
            "source": "https://example.com/archive.zip",
        }
        self.assertEqual([expected], response.data["input_sources"])
        self.assertEqual(["archive.zip"], response.data["input_root"])

    def test_scanpipe_api_project_results_generator(self):
        results_generator = JSONResultsGenerator(self.project1)
        results = json.loads("".join(results_generator))

        expected = ["dependencies", "files", "headers", "packages"]
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

        expected = ["dependencies", "files", "headers", "packages"]
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
        expected = ["dependencies", "files", "headers", "packages"]
        self.assertEqual(expected, sorted(results.keys()))

    def test_scanpipe_api_project_action_pipelines(self):
        url = reverse("project-pipelines")
        response = self.csrf_client.get(url)
        expected = ["name", "summary", "description", "steps"]
        self.assertEqual(expected, list(response.data[0].keys()))

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
        self.resource1.compliance_alert = CodebaseResource.Compliance.ERROR
        self.resource1.save()
        response = self.csrf_client.get(url)
        self.assertEqual("error", response.data["results"][0]["compliance_alert"])

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

    def test_scanpipe_api_project_action_errors(self):
        url = reverse("project-errors", args=[self.project1.uuid])
        ProjectError.objects.create(
            project=self.project1, model="ModelName", details={}, message="Error"
        )

        response = self.csrf_client.get(url)
        self.assertEqual(1, response.data["count"])
        self.assertIsNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        self.assertEqual(1, len(response.data["results"]))

        error = response.data["results"][0]
        self.assertEqual("ModelName", error["model"])
        self.assertEqual({}, error["details"])
        self.assertEqual("Error", error["message"])

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

        summary_file = self.data_location / "is-npm-1.0.0_scan_package_summary.json"
        copy_input(summary_file, self.project1.output_path)

        response = self.csrf_client.get(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(10, len(response.data.keys()))

    def test_scanpipe_api_project_action_delete(self):
        run = self.project1.add_pipeline("docker")
        run.set_task_started(task_id=uuid.uuid4())
        self.assertEqual(run.Status.RUNNING, run.status)

        response = self.csrf_client.delete(self.project1_detail_url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = (
            "Cannot execute this action until all associated pipeline runs are "
            "completed."
        )
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
        self.project1.add_pipeline("docker")
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
        expected = {
            "status": "All data, except inputs, for the Analysis project have been "
            "removed."
        }
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
        self.assertIn("docker", response.data.get("pipelines"))

        data = {"pipeline": "not_available"}
        response = self.csrf_client.post(url, data=data)
        expected = {"status": "not_available is not a valid pipeline."}
        self.assertEqual(expected, response.data)

        data = {"pipeline": "docker"}
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Pipeline added."}, response.data)
        mock_execute_pipeline_task.assert_not_called()

        self.assertEqual(1, self.project1.runs.count())
        run = self.project1.runs.get()
        self.assertEqual(data["pipeline"], run.pipeline_name)

        data["execute_now"] = True
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Pipeline added."}, response.data)
        mock_execute_pipeline_task.assert_called_once()

    @mock.patch("requests.get")
    def test_scanpipe_api_project_action_add_input(self, mock_get):
        url = reverse("project-add-input", args=[self.project1.uuid])
        response = self.csrf_client.get(url)
        expected = "upload_file or input_urls required."
        self.assertEqual(expected, response.data.get("status"))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        mock_get.side_effect = None
        mock_get.return_value = mock.Mock(
            content=b"\x00",
            headers={},
            status_code=200,
            url="https://example.com/archive.zip",
        )
        data = {
            "input_urls": "https://example.com/archive.zip",
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Input(s) added."}, response.data)
        self.assertEqual(["archive.zip"], self.project1.input_root)

        data = {
            "upload_file": io.BytesIO(b"Content"),
        }
        response = self.csrf_client.post(url, data=data)
        self.assertEqual({"status": "Input(s) added."}, response.data)
        expected = sorted(["upload_file", "archive.zip"])
        self.assertEqual(expected, sorted(self.project1.input_root))

        run = self.project1.add_pipeline("docker")
        run.set_task_started(task_id=uuid.uuid4())
        response = self.csrf_client.get(url)
        expected = "Cannot add inputs once a pipeline has started to execute."
        self.assertEqual(expected, response.data.get("status"))
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_scanpipe_api_run_detail(self):
        run1 = self.project1.add_pipeline("docker")
        url = reverse("run-detail", args=[run1.uuid])
        response = self.csrf_client.get(url)

        self.assertEqual(str(run1.uuid), response.data["uuid"])
        self.assertIn(self.project1_detail_url, response.data["project"])
        self.assertEqual("docker", response.data["pipeline_name"])
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
        run1 = self.project1.add_pipeline("docker")
        url = reverse("run-start-pipeline", args=[run1.uuid])
        response = self.csrf_client.post(url)
        expected = {"status": "Pipeline docker started."}
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
        run1 = self.project1.add_pipeline("docker")
        url = reverse("run-stop-pipeline", args=[run1.uuid])
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Pipeline is not running."}
        self.assertEqual(expected, response.data)

        run1.set_task_started(run1.pk)
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": "Pipeline docker stopped."}
        self.assertEqual(expected, response.data)

        run1.refresh_from_db()
        self.assertTrue(run1.task_stopped)

    @override_settings(SCANCODEIO_ASYNC=False)
    def test_scanpipe_api_run_action_delete_pipeline(self):
        run1 = self.project1.add_pipeline("docker")
        url = reverse("run-delete-pipeline", args=[run1.uuid])

        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": "Pipeline docker deleted."}
        self.assertEqual(expected, response.data)
        self.assertFalse(Run.objects.filter(pk=run1.pk).exists())

        run2 = self.project1.add_pipeline("docker")
        url = reverse("run-delete-pipeline", args=[run2.uuid])

        run2.set_task_queued()
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        expected = {"status": "Pipeline docker deleted."}
        self.assertEqual(expected, response.data)
        self.assertFalse(Run.objects.filter(pk=run2.pk).exists())

        run3 = self.project1.add_pipeline("docker")
        url = reverse("run-delete-pipeline", args=[run3.uuid])

        run3.set_task_started(run3.pk)
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Only non started or queued pipelines can be deleted."}
        self.assertEqual(expected, response.data)

        run3.set_task_ended(0)
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Only non started or queued pipelines can be deleted."}
        self.assertEqual(expected, response.data)

        run3.set_task_stopped()
        response = self.csrf_client.post(url)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"status": "Only non started or queued pipelines can be deleted."}
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
        with self.assertRaises(LookupError):
            get_model_serializer(None)

    def test_scanpipe_api_serializer_get_serializer_fields(self):
        self.assertEqual(38, len(get_serializer_fields(DiscoveredPackage)))
        self.assertEqual(11, len(get_serializer_fields(DiscoveredDependency)))
        self.assertEqual(30, len(get_serializer_fields(CodebaseResource)))

        with self.assertRaises(LookupError):
            get_serializer_fields(None)

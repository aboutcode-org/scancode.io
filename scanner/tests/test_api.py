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

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIClient

from scanner.models import EmailSubscription
from scanner.models import Scan
from scanner.models import WebhookSubscription


class ScannerAPITest(TestCase):
    data_location = Path(__file__).parent / "data"

    def setUp(self):
        self.scan_list_url = reverse("scan-list")

        self.scan1 = Scan.objects.create(uri="https://nexb.com/scancode.zip")
        self.scan1_detail_url = reverse("scan-detail", args=[self.scan1.uuid])

        self.scan2 = Scan.objects.create(uri="https://nexb.com/django.zip")
        self.scan2_detail_url = reverse("scan-detail", args=[self.scan2.uuid])

        self.user = User.objects.create_user("username", "e@mail.com", "secret")
        self.header_prefix = "Token "
        self.token = Token.objects.create(user=self.user)
        self.auth = self.header_prefix + self.token.key

        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.csrf_client.credentials(HTTP_AUTHORIZATION=self.auth)

    def create_with_dates(self, **kwargs):
        now = timezone.now()
        return Scan.objects.create(
            task_start_date=now,
            task_end_date=now,
            **kwargs,
        )

    def test_api_token_authentication(self):
        # Reset the pre-set credentials
        self.csrf_client.credentials()

        response = self.client.get(self.scan_list_url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        auth = ""
        response = self.csrf_client.get(self.scan_list_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        auth = self.header_prefix
        response = self.csrf_client.get(self.scan_list_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        auth = self.header_prefix + "bad_token"
        response = self.csrf_client.get(self.scan_list_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

        auth = self.header_prefix + self.token.key
        response = self.csrf_client.get(self.scan_list_url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_api_scan_list_endpoint_results(self):
        response = self.csrf_client.get(self.scan_list_url)
        self.assertContains(response, self.scan1_detail_url)
        self.assertContains(response, self.scan2_detail_url)
        self.assertEqual(2, response.data["count"])
        self.assertNotContains(response, "task_output")

    def test_api_scan_list_endpoint_search(self):
        data = {"search": "scancode"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, self.scan1_detail_url)
        self.assertNotContains(response, self.scan2_detail_url)

    def test_api_scan_list_endpoint_filters(self):
        data = {"uuid": self.scan1.uuid}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, self.scan1_detail_url)
        self.assertNotContains(response, self.scan2_detail_url)

        self.scan2.created_by = uuid.uuid4()
        self.scan2.save()
        data = {"created_by": self.scan2.created_by}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, self.scan1_detail_url)
        self.assertContains(response, self.scan2_detail_url)

        self.scan2.task_id = uuid.uuid4()
        self.scan2.save()
        data = {"task_id": self.scan2.task_id}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertNotContains(response, self.scan1_detail_url)
        self.assertContains(response, self.scan2_detail_url)

    def test_api_scan_list_endpoint_multiple_uri_filters(self):
        scan3 = Scan.objects.create(uri="https://nexb.com/p3.zip")
        scan3_detail_url = reverse("scan-detail", args=[scan3.uuid])

        data = {"uri": self.scan1.uri}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, self.scan1_detail_url)
        self.assertNotContains(response, self.scan2_detail_url)
        self.assertNotContains(response, scan3_detail_url)

        filters = f"?uri={self.scan2.uri}&uri={scan3.uri}"
        response = self.csrf_client.get(self.scan_list_url + filters)
        self.assertEqual(2, response.data["count"])
        self.assertNotContains(response, self.scan1_detail_url)
        self.assertContains(response, self.scan2_detail_url)
        self.assertContains(response, scan3_detail_url)

        data = {"uri": [self.scan2.uri, scan3.uri]}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(2, response.data["count"])
        self.assertNotContains(response, self.scan1_detail_url)
        self.assertContains(response, self.scan2_detail_url)
        self.assertContains(response, scan3_detail_url)

    def test_api_scan_list_endpoint_status_filter(self):
        Scan.objects.all().delete()

        completed = self.create_with_dates(
            uri="completed.zip",
            task_exitcode=0,
        )
        completed_with_issues = self.create_with_dates(
            uri="issues.zip",
            task_exitcode=1,
            task_output="Scanning done.",
        )
        download_failed = self.create_with_dates(
            uri="download_failed.zip",
            task_exitcode=404,
        )
        scan_failed = self.create_with_dates(
            uri="scan_failed.zip",
            task_exitcode=1,
        )
        in_progress = Scan.objects.create(
            uri="in_progress.zip",
            task_start_date=timezone.now(),
        )
        not_started_yet = Scan.objects.create(
            uri="not_started_yet.zip",
        )

        data = {"status": "not existing status"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertIn("status", response.data)

        data = {"status": "completed"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, completed.uri)

        data = {"status": "completed-with-issues"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, completed_with_issues.uri)

        data = {"status": "failed"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(2, response.data["count"])
        self.assertContains(response, download_failed.uri)
        self.assertContains(response, scan_failed.uri)

        data = {"status": "download-failed"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, download_failed.uri)

        data = {"status": "scan-failed"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, scan_failed.uri)

        data = {"status": "in-progress"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, in_progress.uri)

        data = {"status": "not-started-yet"}
        response = self.csrf_client.get(self.scan_list_url, data)
        self.assertEqual(1, response.data["count"])
        self.assertContains(response, not_started_yet.uri)

    def test_api_scan_list_endpoint_status_action(self):
        Scan.objects.all().delete()

        Scan.objects.create(uri="not_started")
        Scan.objects.create(uri="started", task_start_date=timezone.now())
        self.create_with_dates(uri="completed")
        self.create_with_dates(uri="succeed", task_exitcode=0)
        self.create_with_dates(uri="scan_failed", task_exitcode=1)
        self.create_with_dates(uri="task_failed", task_exitcode=3)
        self.create_with_dates(uri="task_timeout", task_exitcode=4)
        self.create_with_dates(uri="download_failed", task_exitcode=404)

        scans_status_url = reverse("scan-status")
        response = self.csrf_client.get(scans_status_url)
        expected = {
            "not_started": 1,
            "started": 1,
            "completed": 6,
            "succeed": 1,
            "failed": 4,
            "scan_failed": 1,
            "task_failed": 1,
            "task_timeout": 1,
            "download_failed": 1,
        }
        self.assertEqual(expected, response.data)

    def test_api_scan_detail_endpoint(self):
        response = self.csrf_client.get(self.scan1_detail_url)
        self.assertIn(self.scan1_detail_url, response.data["url"])
        self.assertEqual(str(self.scan1.uuid), response.data["uuid"])
        self.assertEqual(self.scan1.uri, response.data["uri"])
        self.assertIsNone(response.data["task_id"])
        self.assertIsNone(response.data["task_start_date"])
        self.assertIsNone(response.data["task_end_date"])
        self.assertEqual("", response.data["task_output"])
        self.assertEqual("not started yet", response.data["status"])
        self.assertIsNone(response.data["execution_time"])
        self.assertIn("/data/", response.data["data_url"])
        self.assertIn("/summary/", response.data["summary_url"])
        self.assertNotIn("created_by", response.data)

    @mock.patch("scanner.api.serializers.download_and_scan")
    def test_api_scan_endpoint_create(self, mock_download_and_scan):
        mock_download_and_scan.return_value = None

        data = {"uri": self.scan1.uri}
        response = self.csrf_client.post(self.scan_list_url, data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {"uri": ["scan with this URI already exists."]}
        self.assertEqual(expected, response.data)

        data = {"uri": "   https://nexb.com/new_package.zip   "}
        response = self.csrf_client.post(self.scan_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual("https://nexb.com/new_package.zip", response.data["uri"])

        data = {"uri": "https://nexb.com/other_package.zip", "email": "user@nexb.com"}
        response = self.csrf_client.post(self.scan_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        subscription = EmailSubscription.objects.latest("id")
        self.assertEqual(data["email"], subscription.email)
        self.assertEqual(data["uri"], subscription.scan.uri)

        user_uuid = uuid.uuid4()
        data = {
            "uri": "https://nexb.com/package_with_webhook.zip",
            "webhook_url": "https://webhook_url.com",
            "created_by": user_uuid,
        }
        response = self.csrf_client.post(self.scan_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        webhook_subscription = WebhookSubscription.objects.latest("id")
        self.assertEqual(data["uri"], webhook_subscription.scan.uri)
        self.assertEqual(data["webhook_url"], webhook_subscription.target_url)
        self.assertEqual(data["created_by"], webhook_subscription.user_uuid)
        self.assertFalse(webhook_subscription.sent)

    @mock.patch("scanner.api.serializers.download_and_scan")
    def test_api_scan_endpoint_create_created_by(self, mock_download_and_scan):
        mock_download_and_scan.return_value = None

        data = {
            "uri": "https://nexb.com/package10.zip",
            "created_by": "user",
        }
        response = self.csrf_client.post(self.scan_list_url, data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected = {
            "created_by": [ErrorDetail(string="Must be a valid UUID.", code="invalid")],
        }
        self.assertEqual(expected, response.data)

        data["created_by"] = uuid.uuid4()
        response = self.csrf_client.post(self.scan_list_url, data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        self.assertNotIn("created_by", response.data)
        self.assertEqual("https://nexb.com/package10.zip", response.data["uri"])

        scan = Scan.objects.get(uri=data["uri"])
        self.assertEqual(data["created_by"], scan.created_by)

    def test_api_scan_endpoint_update(self):
        response = self.csrf_client.put(self.scan_list_url)
        self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, response.status_code)

    def test_api_scan_endpoint_data_and_summary_action(self):
        action_url = reverse("scan-data", args=[self.scan1.uuid])
        response = self.csrf_client.get(action_url)
        expected = {"error": "Scan data not available"}
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(expected, response.data)

        self.scan1.output_file = "invalid_path.json"
        self.scan1.save()
        response = self.csrf_client.get(action_url)
        expected = {"error": "Scan data not available"}
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(expected, response.data)

        # /api/scans/[UUID]/data/
        self.scan1.output_file = str(
            self.data_location / "scan_django_filter-1.1.0.whl.json"
        )
        self.scan1.summary = self.scan1.get_summary_from_output()
        self.scan1.save()
        response = self.csrf_client.get(action_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        headers = response.data.get("headers")[0]
        self.assertEqual("3.1.1", headers["tool_version"])

        action_url = reverse("scan-summary", args=[self.scan1.uuid])
        response = self.csrf_client.get(action_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        expected = [
            {"count": 29, "value": None},
            {"count": 5, "value": "bsd-new"},
            {"count": 4, "value": "free-unknown"},
            {"count": 3, "value": "unknown"},
        ]
        self.assertEqual(expected, response.data["license_expressions"])

        expected = [
            {"value": None, "count": 35},
            {
                "value": "Copyright (c) Alex Gaynor and individual contributors",
                "count": 1,
            },
        ]
        self.assertEqual(expected, response.data["copyrights"])

        expected = [
            {"value": None, "count": 38},
            {"value": "Alex Gaynor and individual contributors", "count": 1},
        ]
        self.assertEqual(expected, response.data["holders"])

        expected = [
            {"value": None, "count": 38},
            {
                "value": "Carlton Gibson Author-email carlton.gibson@noumenal.es",
                "count": 1,
            },
        ]
        self.assertEqual(expected, response.data["authors"])

        expected = [
            {"value": None, "count": 20},
            {"value": "Python", "count": 16},
            {"value": "HTML", "count": 3},
        ]
        self.assertEqual(expected, response.data["programming_language"])

        expected = {
            "score": 0,
            "declared": False,
            "discovered": 0.03,
            "consistency": False,
            "spdx": False,
            "license_texts": False,
        }
        self.assertEqual(expected, response.data["license_clarity_score"])

        key_files = response.data["key_files"]
        self.assertEqual(1, len(key_files))
        self.assertEqual(
            "ethtool-3.16.tar.xz-extract/ethtool-3.16/COPYING", key_files[0]["path"]
        )
        self.assertEqual(
            "ethtool is available under the terms of the GNU Public License version 2.",
            key_files[0]["content"],
        )

        license_matches_data = response.data["license_matches"]
        expected = {
            "path": "django_filter-1.1.0-py2.py3-none-any.whl-extract/"
            "django_filter-1.1.0.dist-info/METADATA",
            "matched_text": "License: BSD",
        }
        self.assertEqual(expected, license_matches_data.get("bsd-new")[1])
        expected = {
            "path": "django_filter-1.1.0-py2.py3-none-any.whl-extract/"
            "django_filter-1.1.0.dist-info/METADATA",
            "matched_text": "Classifier: License :: OSI Approved :: BSD License",
        }
        self.assertEqual(expected, license_matches_data.get("bsd-new")[2])

    @mock.patch("scanner.models.download_and_scan")
    def test_api_scan_endpoint_rescan_action(self, mock_download_and_scan):
        mock_download_and_scan.return_value = None
        action_url = reverse("scan-rescan", args=[self.scan1.uuid])
        response = self.csrf_client.get(action_url)
        expected = {"message": "Re-scan requested."}
        self.assertEqual(expected, response.data)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

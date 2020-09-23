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
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest import mock

from django.core import mail
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from scanner.models import EmailSubscription
from scanner.models import Scan
from scanner.models import WebhookSubscription
from scanner.tasks import DOWNLOAD_SIZE_THRESHOLD


class ScannerModelsTest(TestCase):
    def setUp(self):
        self.data_location = Path(__file__).parent / "data"
        self.scan_output_file = str(
            self.data_location / "scan_django_filter-1.1.0.whl.json"
        )

        self.scan1 = Scan.objects.create(uri="https://uri.com")

    def test_scanner_model_uri_field_unique(self):
        with self.assertRaises(IntegrityError):
            Scan.objects.create(uri=self.scan1.uri)

    def test_scanner_model_status_property(self):
        self.assertEqual("not started yet", self.scan1.status)

        self.scan1.task_start_date = timezone.now()
        self.scan1.save()

        self.assertEqual("in progress", self.scan1.status)

        self.scan1.task_end_date = timezone.now()
        self.scan1.save()
        self.assertEqual("completed", self.scan1.status)

        self.scan1.task_exitcode = 404
        self.scan1.save()
        self.assertEqual("download failed", self.scan1.status)

        self.scan1.task_exitcode = 1
        self.scan1.save()
        self.assertEqual("scan failed", self.scan1.status)

        self.scan1.task_output = "Scanning done."
        self.scan1.save()
        self.assertEqual("completed with issues", self.scan1.status)

        self.scan1.task_exitcode = 0
        self.scan1.save()
        self.assertEqual("completed", self.scan1.status)

    def test_scanner_model_queryset_methods(self):
        Scan.objects.all().delete()

        not_started = Scan.objects.create(uri="not_started")
        self.assertEqual([not_started], list(Scan.objects.not_started()))

        started = Scan.objects.create(uri="started", task_start_date=timezone.now())
        self.assertEqual([started], list(Scan.objects.started()))

        completed = Scan.objects.create(uri="completed", task_end_date=timezone.now())
        self.assertEqual([completed], list(Scan.objects.completed()))

        succeed = Scan.objects.create(uri="succeed", task_exitcode=0)
        self.assertEqual([succeed], list(Scan.objects.succeed()))

        scan_failed = Scan.objects.create(uri="scan_failed", task_exitcode=1)
        self.assertEqual([scan_failed], list(Scan.objects.scan_failed()))

        task_failed = Scan.objects.create(uri="task_failed", task_exitcode=3)
        self.assertEqual([task_failed], list(Scan.objects.task_failed()))

        task_timeout = Scan.objects.create(uri="task_timeout", task_exitcode=4)
        self.assertEqual([task_timeout], list(Scan.objects.task_timeout()))

        download_failed = Scan.objects.create(uri="download_failed", task_exitcode=404)
        self.assertEqual([download_failed], list(Scan.objects.download_failed()))

        self.assertEqual(
            [download_failed, task_timeout, task_failed, scan_failed],
            list(Scan.objects.failed()),
        )

        small = Scan.objects.create(uri="small", size=1024)
        large = Scan.objects.create(uri="large", size=DOWNLOAD_SIZE_THRESHOLD + 1)
        self.assertEqual([small], list(Scan.objects.small()))
        self.assertEqual([large], list(Scan.objects.large()))

    def test_scanner_model_reset_values_method(self):
        scan = Scan.objects.create(
            uri="http://a.com/a.zip",
            scancode_version="1.0",
            task_start_date=timezone.now(),
            task_end_date=timezone.now(),
            task_exitcode=0,
            task_output="Output",
        )

        scan.reset_values()
        self.assertIsNone(scan.size)
        self.assertIsNone(scan.task_start_date)
        self.assertIsNone(scan.task_end_date)
        self.assertIsNone(scan.task_exitcode)
        self.assertEqual("", scan.task_output)
        self.assertEqual("", scan.scancode_version)
        self.assertEqual("", scan.filename)
        self.assertEqual("", scan.sha1)
        self.assertEqual("", scan.md5)

    def test_scanner_model_has_output_file(self):
        self.assertFalse(Scan().has_output_file)

        scan = Scan.objects.create(
            uri="http://a.com/a.zip", output_file="non-existing-path"
        )
        self.assertFalse(scan.has_output_file)

        scan.output_file = self.scan_output_file
        self.assertTrue(scan.has_output_file)

    def test_scanner_model_output_path(self):
        scan = Scan()
        self.assertFalse(scan.has_output_file)
        self.assertIsNone(scan.output_path)

        scan = Scan(output_file="non-existing-path")
        self.assertFalse(scan.has_output_file)
        self.assertIsNone(scan.output_path)

        scan = Scan(output_file=self.scan_output_file)
        self.assertTrue(scan.has_output_file)
        self.assertEqual(self.data_location, scan.output_path)

    def test_scanner_model_delete_removes_output_path(self):
        scan = Scan()
        self.assertTrue(scan.delete())

        scan = Scan(output_file="non-existing-path")
        self.assertFalse(scan.has_output_file)
        with mock.patch("shutil.rmtree") as mock_rmtree:
            self.assertTrue(scan.delete())
        mock_rmtree.assert_not_called()

        scan_output_location_path = Path(tempfile.mkdtemp())
        scan_output_file = scan_output_location_path / "scan.json"
        shutil.copyfile(self.scan_output_file, scan_output_file)

        scan = Scan(output_file=str(scan_output_file))
        self.assertTrue(scan.has_output_file)
        self.assertTrue(scan.delete())
        self.assertFalse(scan_output_file.exists())
        self.assertFalse(scan_output_location_path.exists())

    def test_scanner_model_data(self):
        self.assertIsNone(Scan().data)

        scan = Scan.objects.create(
            uri="http://a.com/a.zip",
            output_file=self.scan_output_file,
        )
        self.assertTrue(scan.data)
        headers = scan.data.get("headers")[0]
        self.assertEqual("3.1.1", headers["tool_version"])

    def test_scanner_model_key_files_output_file(self):
        self.assertFalse(Scan().key_files_output_file)

        scan = Scan(output_file="/fake/path/scan_django_filter-1.1.0.whl.scan.json")
        expected = "/fake/path/key_files_django_filter-1.1.0.whl.scan.json"
        self.assertEqual(expected, scan.key_files_output_file)

    def test_scanner_model_get_key_files_data(self):
        self.assertIsNone(Scan().get_key_files_data())

        scan = Scan.objects.create(output_file=self.scan_output_file)
        key_files_data = scan.get_key_files_data()
        self.assertTrue(key_files_data)
        self.assertTrue(key_files_data[0].get("is_top_level"))

    def test_scanner_model_get_license_matches_data(self):
        self.assertIsNone(Scan().get_license_matches_data())

        scan = Scan.objects.create(output_file=self.scan_output_file)
        license_matches_data = scan.get_license_matches_data()
        self.assertTrue(license_matches_data)

        metadata_path = (
            "django_filter-1.1.0-py2.py3-none-any.whl-extract/"
            "django_filter-1.1.0.dist-info/METADATA"
        )
        expected = {
            "path": metadata_path,
            "matched_text": "License: BSD",
        }
        self.assertEqual(expected, license_matches_data.get("bsd-new")[1])

        expected = {
            "path": metadata_path,
            "matched_text": "Classifier: License :: OSI Approved :: BSD License",
        }
        self.assertEqual(expected, license_matches_data.get("bsd-new")[2])

    def test_scanner_model_get_summary_from_output(self):
        self.assertIsNone(Scan().get_summary_from_output())

        scan = Scan.objects.create(output_file=self.scan_output_file)
        summary_data = scan.get_summary_from_output()
        self.assertTrue(summary_data)

        summary_reference_location = self.data_location / "summary.json"
        # Un-comment to regenerate the reference data
        # with summary_reference_location.open('w') as f:
        #     f.write(json.dumps(summary_data, indent=2))

        expected = json.load(summary_reference_location.open())
        self.assertEqual(expected, summary_data)


class SubscriptionModelsTest(TestCase):
    def setUp(self):
        self.scan1 = Scan.objects.create(uri="https://uri.com")
        self.email_subscription1 = EmailSubscription.objects.create(
            scan=self.scan1, email="user@nexb.com"
        )

        user_uuid = uuid.uuid4()
        self.webhook_subscription1 = WebhookSubscription.objects.create(
            scan=self.scan1,
            user_uuid=user_uuid,
            target_url="https://example.com",
        )

    def test_email_subscription_model_str(self):
        self.assertEqual(
            "user@nexb.com follows https://uri.com", str(self.email_subscription1)
        )

    def test_scanner_model_has_subscription(self):
        self.assertTrue(self.scan1.has_subscriptions())

        self.email_subscription1.delete()
        self.assertTrue(self.scan1.has_subscriptions())

        self.webhook_subscription1.delete()
        self.assertFalse(self.scan1.has_subscriptions())

    def test_email_subscription_model_notify(self):
        self.email_subscription1.notify()
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["user@nexb.com"])
        self.assertEqual(email.bcc, [])
        self.assertEqual(email.subject, "[ScanCode.io] Scan completed")
        self.assertIn("The scan for https://uri.com is completed.", email.body)
        self.assertIn("This email is a service from ScanCode.io", email.body)

    def test_email_subscription_scanner_model_run_subscriptions(self):
        email_subscription2 = EmailSubscription.objects.create(
            scan=self.scan1, email="user2@nexb.com"
        )
        self.scan1.run_subscriptions()
        self.assertEqual(len(mail.outbox), 2)
        expected = sorted([self.email_subscription1.email, email_subscription2.email])
        self.assertEqual(expected, sorted(mail.outbox[0].to + mail.outbox[1].to))

    def test_webhook_subscription_model_str(self):
        self.assertEqual(
            f"{self.webhook_subscription1.user_uuid} follows https://uri.com",
            str(self.webhook_subscription1),
        )

    @mock.patch("requests.post")
    def test_webhook_subscription_model_notify(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=404)
        self.assertFalse(self.webhook_subscription1.notify())
        self.webhook_subscription1.refresh_from_db()
        self.assertFalse(self.webhook_subscription1.sent)

        mock_post.return_value = mock.Mock(status_code=200)
        self.assertTrue(self.webhook_subscription1.notify())
        self.webhook_subscription1.refresh_from_db()
        self.assertTrue(self.webhook_subscription1.sent)

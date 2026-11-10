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

import sys
import uuid
from importlib import reload
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import clear_url_caches
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from scanpipe.admin import ProjectAdmin
from scanpipe.admin import admin_site
from scanpipe.models import CodebaseRelation
from scanpipe.models import DiscoveredLicense
from scanpipe.models import OriginMatch
from scanpipe.models import Project
from scanpipe.models import ProjectMessage
from scanpipe.models import Run
from scanpipe.models import WebhookSubscription
from scanpipe.tests import make_dependency
from scanpipe.tests import make_package
from scanpipe.tests import make_resource_file

User = get_user_model()

scanpipe_app = apps.get_app_config("scanpipe")


def refresh_url_cache():
    """
    Clear the URLs cache and reloading the URLs module.
    Useful when changing the value of a settings trigger different URLs availability.
    """
    clear_url_caches()
    if settings.ROOT_URLCONF in sys.modules:
        reload(sys.modules[settings.ROOT_URLCONF])


@override_settings(SCANPIPE={"ENABLE_ADMIN_SITE": True})
class ScanPipeAdminTest(TestCase):
    data = Path(__file__).parent / "data"

    def setUp(self):
        refresh_url_cache()
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_admin_site_is_enabled_setting(self):
        self.assertEqual("/admin/", reverse("admin:index"))
        self.assertEqual(
            "/admin/scanpipe/project/", reverse("admin:scanpipe_project_changelist")
        )
        self.assertEqual(
            f"/admin/scanpipe/project/{self.project1.uuid}/change/",
            reverse("admin:scanpipe_project_change", args=[self.project1.pk]),
        )

        with override_settings(SCANPIPE={"ENABLE_ADMIN_SITE": False}):
            refresh_url_cache()
            with self.assertRaises(NoReverseMatch):
                reverse("admin:index")

    def test_scanpipe_admin_models_get_admin_url(self):
        resource = make_resource_file(self.project1, "path")
        self.assertEqual(
            f"/admin/scanpipe/codebaseresource/{resource.id}/change/",
            resource.get_admin_url(),
        )
        package = make_package(self.project1, "pkg:type/a")
        self.assertEqual(
            f"/admin/scanpipe/discoveredpackage/{package.id}/change/",
            package.get_admin_url(),
        )
        dependency = make_dependency(self.project1, for_package=package)
        self.assertEqual(
            f"/admin/scanpipe/discovereddependency/{dependency.id}/change/",
            dependency.get_admin_url(),
        )
        origin_match = OriginMatch.objects.create(
            project=self.project1,
            resource=resource,
            purl="pkg:pypi/six@1.17.0",
            match_type=OriginMatch.MatchType.FILE,
            tool="matchcode",
        )
        self.assertEqual(
            f"/admin/scanpipe/originmatch/{origin_match.uuid}/change/",
            origin_match.get_admin_url(),
        )

        with override_settings(SCANPIPE={"ENABLE_ADMIN_SITE": False}):
            refresh_url_cache()
            self.assertIsNone(resource.get_admin_url())
            self.assertIsNone(package.get_admin_url())
            self.assertIsNone(dependency.get_admin_url())
            self.assertIsNone(origin_match.get_admin_url())

    def test_scanpipe_admin_newly_registered_models_changelist(self):
        password = str(uuid.uuid4())
        admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password=password
        )
        self.client.force_login(admin_user)

        DiscoveredLicense.objects.create(
            project=self.project1,
            identifier="apache-2.0",
            license_expression="apache-2.0",
            detection_count=2,
            compliance_alert="ok",
        )
        ProjectMessage.objects.create(
            project=self.project1,
            severity=ProjectMessage.Severity.ERROR,
            model="CodebaseResource",
            description="Extraction error occurred",
            traceback="Traceback...",
        )
        resource1 = make_resource_file(self.project1, "path/to/file1.c")
        resource2 = make_resource_file(self.project1, "path/to/file2.h")
        CodebaseRelation.objects.create(
            project=self.project1,
            from_resource=resource1,
            to_resource=resource2,
            map_type="c_include",
        )
        Run.objects.create(
            project=self.project1,
            pipeline_name="analyze_codebase",
        )
        WebhookSubscription.objects.create(
            project=self.project1,
            target_url="https://example.com/webhook/",
            is_active=True,
            trigger_on_each_run=True,
        )

        # DiscoveredLicense changelist
        license_url = reverse("admin:scanpipe_discoveredlicense_changelist")
        response = self.client.get(license_url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "apache-2.0")
        response = self.client.get(license_url, {"q": "apache"})
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "apache-2.0")
        response = self.client.get(license_url, {"compliance_alert": "ok"})
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "apache-2.0")
        response = self.client.get(
            license_url, {"project__uuid__exact": str(self.project1.uuid)}
        )
        self.assertEqual(200, response.status_code)

        # ProjectMessage changelist
        message_url = reverse("admin:scanpipe_projectmessage_changelist")
        response = self.client.get(message_url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Extraction error occurred")
        response = self.client.get(message_url, {"q": "Extraction"})
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Extraction error occurred")
        response = self.client.get(message_url, {"severity": "error"})
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Extraction error occurred")
        response = self.client.get(
            message_url, {"project__uuid__exact": str(self.project1.uuid)}
        )
        self.assertEqual(200, response.status_code)

        # CodebaseRelation changelist
        relation_url = reverse("admin:scanpipe_codebaserelation_changelist")
        response = self.client.get(relation_url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "c_include")
        response = self.client.get(relation_url, {"map_type": "c_include"})
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "c_include")
        response = self.client.get(
            relation_url, {"project__uuid__exact": str(self.project1.uuid)}
        )
        self.assertEqual(200, response.status_code)

        # Run changelist
        run_url = reverse("admin:scanpipe_run_changelist")
        response = self.client.get(run_url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "analyze_codebase")
        response = self.client.get(run_url, {"pipeline_name": "analyze_codebase"})
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "analyze_codebase")
        response = self.client.get(
            run_url, {"project__uuid__exact": str(self.project1.uuid)}
        )
        self.assertEqual(200, response.status_code)

        # WebhookSubscription changelist
        webhook_url = reverse("admin:scanpipe_webhooksubscription_changelist")
        response = self.client.get(webhook_url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "https://example.com/webhook/")
        response = self.client.get(
            webhook_url, {"project__uuid__exact": str(self.project1.uuid)}
        )
        self.assertEqual(200, response.status_code)

    def test_scanpipe_admin_project_admin_link_helpers(self):
        project_admin = ProjectAdmin(Project, admin_site)

        DiscoveredLicense.objects.create(
            project=self.project1,
            identifier="mit",
            license_expression="mit",
            detection_count=1,
        )
        ProjectMessage.objects.create(
            project=self.project1,
            severity=ProjectMessage.Severity.INFO,
            description="Notice",
        )
        resource1 = make_resource_file(self.project1, "path/to/res1")
        resource2 = make_resource_file(self.project1, "path/to/res2")
        CodebaseRelation.objects.create(
            project=self.project1,
            from_resource=resource1,
            to_resource=resource2,
            map_type="relation",
        )
        Run.objects.create(
            project=self.project1,
            pipeline_name="test_pipeline",
        )

        self.project1.update_counts()
        self.project1.refresh_from_db()

        expected_license_url = reverse("admin:scanpipe_discoveredlicense_changelist")
        expected_license_link = (
            f'<a href="{expected_license_url}?project__uuid__exact='
            f'{self.project1.uuid}">1</a>'
        )
        self.assertEqual(
            expected_license_link, project_admin.licenses_link(self.project1)
        )

        expected_message_url = reverse("admin:scanpipe_projectmessage_changelist")
        expected_message_link = (
            f'<a href="{expected_message_url}?project__uuid__exact='
            f'{self.project1.uuid}">1</a>'
        )
        self.assertEqual(
            expected_message_link, project_admin.messages_link(self.project1)
        )

        expected_relation_url = reverse("admin:scanpipe_codebaserelation_changelist")
        expected_relation_link = (
            f'<a href="{expected_relation_url}?project__uuid__exact='
            f'{self.project1.uuid}">1</a>'
        )
        self.assertEqual(
            expected_relation_link, project_admin.relations_link(self.project1)
        )

        expected_run_url = reverse("admin:scanpipe_run_changelist")
        expected_run_link = (
            f'<a href="{expected_run_url}?project__uuid__exact='
            f'{self.project1.uuid}">1</a>'
        )
        self.assertEqual(expected_run_link, project_admin.runs_link(self.project1))

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

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from scancodeio.auth import is_authenticated_when_required

User = get_user_model()

TEST_PASSWORD = str(uuid.uuid4())

login_url = reverse("login")
project_list_url = reverse("project_list")
logout_url = reverse("logout")
profile_url = reverse("account_profile")
login_redirect_url = reverse(settings.LOGIN_REDIRECT_URL)


class ScanCodeIOAuthTest(TestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUser()
        self.basic_user = User.objects.create_user(
            username="basic_user", password=TEST_PASSWORD
        )

    def test_scancodeio_auth_is_authenticated_when_required(self):
        self.assertFalse(self.anonymous_user.is_authenticated)
        self.assertFalse(is_authenticated_when_required(user=self.anonymous_user))

        self.assertTrue(self.basic_user.is_authenticated)
        self.assertTrue(is_authenticated_when_required(user=self.basic_user))

        with override_settings(SCANCODEIO_REQUIRE_AUTHENTICATION=False):
            self.assertTrue(is_authenticated_when_required(user=None))
            self.assertTrue(is_authenticated_when_required(user=self.anonymous_user))
            self.assertTrue(is_authenticated_when_required(user=self.basic_user))

    def test_scancodeio_auth_login_view(self):
        data = {"username": self.basic_user.username, "password": ""}
        response = self.client.post(login_url, data)
        form = response.context_data["form"]
        expected_error = {"password": ["This field is required."]}
        self.assertEqual(expected_error, form.errors)

        data = {"username": self.basic_user.username, "password": "wrong"}
        response = self.client.post(login_url, data)
        form = response.context_data["form"]
        expected_error = {
            "__all__": [
                "Please enter a correct username and password. "
                "Note that both fields may be case-sensitive."
            ]
        }
        self.assertEqual(expected_error, form.errors)

        data = {"username": self.basic_user.username, "password": TEST_PASSWORD}
        response = self.client.post(login_url, data, follow=True)
        self.assertRedirects(response, login_redirect_url)
        expected = '<a class="navbar-link">basic_user</a>'
        self.assertContains(response, expected, html=True)

    def test_scancodeio_auth_logged_in_navbar_header(self):
        response = self.client.get(project_list_url)
        self.assertRedirects(response, f"{login_url}?next={project_list_url}")

        self.client.login(username=self.basic_user.username, password=TEST_PASSWORD)
        response = self.client.get(project_list_url)
        expected = '<a class="navbar-link">basic_user</a>'
        self.assertContains(response, expected, html=True)
        expected = f'<a class="navbar-item" href="{profile_url}">Profile settings</a>'
        self.assertContains(response, expected, html=True)
        expected = f'<form id="logout-form" method="post" action="{logout_url}">'
        self.assertContains(response, expected)

    def test_scancodeio_auth_logout_view(self):
        response = self.client.get(logout_url)
        self.assertEqual(405, response.status_code)

        response = self.client.post(logout_url)
        self.assertRedirects(response, login_url)

        self.client.login(username=self.basic_user.username, password=TEST_PASSWORD)
        response = self.client.post(logout_url)
        self.assertRedirects(response, login_url)

    def test_scancodeio_account_profile_view(self):
        self.client.login(username=self.basic_user.username, password=TEST_PASSWORD)
        response = self.client.get(profile_url)
        expected = '<label class="label">API Key</label>'
        self.assertContains(response, expected, html=True)
        self.assertContains(response, self.basic_user.auth_token.key)

    def test_scancodeio_auth_views_are_protected(self):
        a_uuid = uuid.uuid4()
        a_int = 1
        a_string = "string"

        views = [
            ("account_profile", None),
            ("project_add", None),
            ("project_list", None),
            ("project_resources", [a_uuid]),
            ("project_packages", [a_uuid]),
            ("project_messages", [a_uuid]),
            ("project_archive", [a_uuid]),
            ("project_delete", [a_uuid]),
            ("project_reset", [a_uuid]),
            ("project_detail", [a_uuid]),
            ("project_results", [a_uuid, a_string]),
            ("resource_raw", [a_uuid, a_int]),
            ("resource_detail", [a_uuid, a_int]),
            ("project_execute_pipelines", [a_uuid]),
            ("project_stop_pipeline", [a_uuid, a_uuid]),
            ("project_delete_pipeline", [a_uuid, a_uuid]),
            ("run_detail", [a_uuid]),
            ("run_status", [a_uuid]),
            ("license_list", None),
            ("license_detail", [a_string]),
        ]

        for viewname, args in views:
            url = reverse(viewname, args=args)
            response = self.client.get(url)
            self.assertEqual(302, response.status_code, msg=viewname)

    def test_scancodeio_auth_api_required_authentication(self):
        api_project_list_url = reverse("project-list")
        response = self.client.get(api_project_list_url)
        expected = {"detail": "Authentication credentials were not provided."}
        self.assertEqual(expected, response.json())
        self.assertEqual(401, response.status_code)

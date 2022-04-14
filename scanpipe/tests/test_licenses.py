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

from unittest import mock

from django.test import TestCase
from django.urls import reverse


class LicensesTest(TestCase):
    def test_license_list_view(self):
        url = reverse("license_list")
        response = self.client.get(url)
        self.assertContains(response, url)

    def test_license_details_view(self):
        key = "apache-2.0"
        license_url = reverse("license_details", args=(key,))
        response = self.client.get(license_url)
        self.assertContains(response, license_url)

        key = "abcdefg"
        dummy_license_url = reverse("license_details", args=(key,))
        response = self.client.get(dummy_license_url)
        self.assertNotContains(response, dummy_license_url)

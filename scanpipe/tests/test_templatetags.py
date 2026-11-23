# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from django.template.loader import render_to_string
from django.test import TestCase

from scanpipe.templatetags.scanpipe_tags import is_http_url

UNSAFE_URLS = [
    "javascript:alert(1)",
    "JAVASCRIPT:alert(1)",
    " javascript:alert(1)",
    "\njavascript:alert(1)",
    "\x01javascript:alert(1)",
    "java\tscript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "/relative/path",
    "//example.com/path",
    "http://[invalid",
    "",
    None,
]

SAFE_URLS = [
    "http://example.com/path",
    "https://example.com/path",
    "HTTPS://example.com/path",
]


class ScanPipeTemplateTagsTest(TestCase):
    def test_scanpipe_templatetags_is_http_url(self):
        for url in SAFE_URLS:
            with self.subTest(url=url):
                self.assertTrue(is_http_url(url))

        for url in UNSAFE_URLS:
            with self.subTest(url=url):
                self.assertFalse(is_http_url(url))

    @staticmethod
    def render_vulnerability_id(resource_url):
        vulnerability = {"resource_url": resource_url, "advisory_id": "VCID-1"}
        context = {"vulnerability": vulnerability}
        return render_to_string("scanpipe/includes/vulnerability_id.html", context)

    def test_scanpipe_templatetags_vulnerability_id_resource_url(self):
        for url in SAFE_URLS:
            with self.subTest(url=url):
                rendered = self.render_vulnerability_id(url)
                self.assertIn(f'<a href="{url}" target="_blank">VCID-1', rendered)

        for url in UNSAFE_URLS:
            with self.subTest(url=url):
                rendered = self.render_vulnerability_id(url)
                self.assertNotIn("<a ", rendered)
                self.assertIn("VCID-1", rendered)

    @staticmethod
    def render_license_detections_tab(rule_url):
        match = {
            "from_file": "file.txt",
            "rule_url": rule_url,
            "rule_identifier": "mit_1.RULE",
        }
        context = {
            "project": {"slug": "project"},
            "tab_data": {"fields": {"matches": {"value": [match]}}},
        }
        return render_to_string("scanpipe/tabset/tab_license_detections.html", context)

    def test_scanpipe_templatetags_license_detections_rule_url(self):
        for url in SAFE_URLS:
            with self.subTest(url=url):
                rendered = self.render_license_detections_tab(url)
                self.assertIn(f'<a href="{url}">', rendered)

        for url in UNSAFE_URLS:
            with self.subTest(url=url):
                rendered = self.render_license_detections_tab(url)
                self.assertEqual(1, rendered.count("<a "))
                self.assertIn("mit_1.RULE", rendered)

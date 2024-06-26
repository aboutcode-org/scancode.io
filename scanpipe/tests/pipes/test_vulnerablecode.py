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
from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes.vulnerablecode import fetch_vulnerabilities
from scanpipe.pipes.vulnerablecode import filter_vulnerabilities
from scanpipe.tests import make_package


class ScanPipeVulnerableCodeTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    @mock.patch("scanpipe.pipes.vulnerablecode.bulk_search_by_purl")
    def test_scanpipe_pipes_vulnerablecode_fetch_vulnerabilities(
        self, mock_search_by_purl
    ):
        django_5_0 = make_package(self.project1, "pkg:pypi/django@5.0")
        data = self.data / "vulnerablecode/django-5.0_package_data.json"
        package_data = json.loads(data.read_text())
        mock_search_by_purl.return_value = [package_data]
        buffer = io.StringIO()

        fetch_vulnerabilities(packages=[django_5_0], logger=buffer.write)
        django_5_0.refresh_from_db()
        self.assertEqual(2, len(package_data.get("affected_by_vulnerabilities")))
        self.assertEqual(
            package_data.get("affected_by_vulnerabilities"),
            django_5_0.affected_by_vulnerabilities,
        )
        self.assertEqual(
            "1 discovered packages updated with vulnerability data.", buffer.getvalue()
        )

        fetch_vulnerabilities(packages=[django_5_0], ignore_set={"VCID-3gge-bre2-aaac"})
        django_5_0.refresh_from_db()
        self.assertEqual(1, len(django_5_0.affected_by_vulnerabilities))

    def test_scanpipe_pipes_vulnerablecode_filter_vulnerabilities(self):
        data = self.data / "vulnerablecode/django-5.0_package_data.json"
        package_data = json.loads(data.read_text())
        vulnerability_data = package_data["affected_by_vulnerabilities"]
        self.assertEqual(2, len(vulnerability_data))

        vulnerability1 = vulnerability_data[0]
        self.assertEqual("VCID-3gge-bre2-aaac", vulnerability1.get("vulnerability_id"))
        ignore_set = {vulnerability1.get("vulnerability_id")}
        self.assertEqual(1, len(filter_vulnerabilities(vulnerability_data, ignore_set)))

        ignore_set = {vulnerability1.get("aliases")[0]}
        self.assertEqual(1, len(filter_vulnerabilities(vulnerability_data, ignore_set)))

        vulnerability2 = vulnerability_data[1]
        ignore_set.add(vulnerability2.get("aliases")[1])
        self.assertEqual([], filter_vulnerabilities(vulnerability_data, ignore_set))

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
from scanpipe.pipes.vulnerablecode import chunked
from scanpipe.pipes.vulnerablecode import fetch_vulnerabilities
from scanpipe.pipes.vulnerablecode import filter_vulnerabilities
from scanpipe.pipes.vulnerablecode import get_purls
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
        # POST /api/v3/packages with data:
        # {"purls": ["pkg:pypi/django@5.0"], "details": true}
        data = self.data / "vulnerablecode" / "django-5.0_package_data.json"
        response_json = json.loads(data.read_text())
        mock_search_by_purl.return_value = response_json
        buffer = io.StringIO()

        package_data = response_json.get("results")[0]
        fetch_vulnerabilities(packages=[django_5_0], logger=buffer.write)
        django_5_0.refresh_from_db()
        self.assertEqual(27, len(package_data.get("affected_by_vulnerabilities")))
        self.assertEqual(
            package_data.get("affected_by_vulnerabilities"),
            django_5_0.affected_by_vulnerabilities,
        )
        self.assertEqual(
            "1 discovered packages updated with vulnerability data.", buffer.getvalue()
        )

        fetch_vulnerabilities(packages=[django_5_0], ignore_set={"PYSEC-2024-28"})
        django_5_0.refresh_from_db()
        self.assertEqual(26, len(django_5_0.affected_by_vulnerabilities))

    def test_scanpipe_pipes_vulnerablecode_filter_vulnerabilities(self):
        data = self.data / "vulnerablecode/django-5.0_package_data.json"
        response_json = json.loads(data.read_text())
        package_data = response_json.get("results")[0]
        vulnerability_data = package_data["affected_by_vulnerabilities"]
        self.assertEqual(27, len(vulnerability_data))

        vulnerability1 = vulnerability_data[0]
        self.assertEqual("PYSEC-2024-102", vulnerability1.get("advisory_id"))
        ignore_set = {vulnerability1.get("advisory_id")}
        self.assertEqual(
            26, len(filter_vulnerabilities(vulnerability_data, ignore_set))
        )

        ignore_set = {vulnerability1.get("aliases")[0]}
        self.assertEqual(
            26, len(filter_vulnerabilities(vulnerability_data, ignore_set))
        )

    def test_scanpipe_pipes_vulnerablecode_chunked(self):
        result = list(chunked([1, 2, 3, 4, 5], 2))
        self.assertEqual([[1, 2], [3, 4], [5]], result)

        result = list(chunked([1, 2, 3, 4, 5], 3))
        self.assertEqual([[1, 2, 3], [4, 5]], result)

        result = list(chunked([], 10))
        self.assertEqual([], result)

        result = list(chunked([1], 5))
        self.assertEqual([[1]], result)

        result = list(chunked([1, 2, 3], 3))
        self.assertEqual([[1, 2, 3]], result)

    def test_scanpipe_pipes_vulnerablecode_get_purls(self):
        pkg1 = make_package(self.project1, "pkg:pypi/django@5.0")
        pkg2 = make_package(self.project1, "pkg:npm/express@4.18.2")
        purls = get_purls([pkg1, pkg2])
        self.assertEqual(["pkg:pypi/django@5.0", "pkg:npm/express@4.18.2"], purls)

    def test_scanpipe_pipes_vulnerablecode_get_purls_empty(self):
        purls = get_purls([])
        self.assertEqual([], purls)

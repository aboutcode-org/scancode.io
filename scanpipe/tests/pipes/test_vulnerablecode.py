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

import io
import json
from functools import partial
from pathlib import Path
from unittest import mock

from django.test import TestCase

import requests

from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes.vulnerablecode import VulnerableCodeError
from scanpipe.pipes.vulnerablecode import bulk_search_by_purl
from scanpipe.pipes.vulnerablecode import chunked
from scanpipe.pipes.vulnerablecode import fetch_vulnerabilities
from scanpipe.pipes.vulnerablecode import filter_vulnerabilities
from scanpipe.pipes.vulnerablecode import get_affected_by_vulnerabilities
from scanpipe.pipes.vulnerablecode import get_all_results
from scanpipe.pipes.vulnerablecode import get_api_link
from scanpipe.pipes.vulnerablecode import get_packages_by_plain_purl
from scanpipe.pipes.vulnerablecode import get_plain_purl
from scanpipe.pipes.vulnerablecode import get_vulnerabilities_by_plain_purl
from scanpipe.pipes.vulnerablecode import request_json
from scanpipe.tests import make_package

API_URL = "https://vulnerablecode.example/api/v3"
PACKAGES_URL = f"{API_URL}/packages"


def make_response(response_data, status_code=200):
    """Return a requests Response with `response_data` as JSON content."""
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(response_data).encode()
    return response


def make_page(results, count=None, next_url=None):
    """Return a paginated VulnerableCode API response for `results`."""
    if count is None:
        count = len(results)
    return {"count": count, "next": next_url, "previous": None, "results": results}


def make_package_data(purl, advisory_uids):
    """Return a VulnerableCode package entry affected by `advisory_uids`."""
    affected_by = [
        {"advisory_uid": advisory_uid, "advisory_id": advisory_uid, "aliases": []}
        for advisory_uid in advisory_uids
    ]
    return {"purl": purl, "affected_by_vulnerabilities": affected_by}


search_test_api = partial(bulk_search_by_purl, api_url=API_URL)
get_test_api_affected_by = partial(get_affected_by_vulnerabilities, api_url=API_URL)


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
        mock_search_by_purl.return_value = response_json["results"]
        buffer = io.StringIO()

        package_data = response_json.get("results")[0]
        fetch_vulnerabilities(packages=[django_5_0], logger=buffer.write)
        django_5_0.refresh_from_db()
        self.assertEqual(30, len(package_data.get("affected_by_vulnerabilities")))
        self.assertEqual(
            package_data.get("affected_by_vulnerabilities"),
            django_5_0.affected_by_vulnerabilities,
        )
        self.assertEqual(
            "1 discovered packages updated with vulnerability data.", buffer.getvalue()
        )

        fetch_vulnerabilities(packages=[django_5_0], ignore_set={"PYSEC-2024-28"})
        django_5_0.refresh_from_db()
        self.assertEqual(29, len(django_5_0.affected_by_vulnerabilities))

    def test_scanpipe_pipes_vulnerablecode_filter_vulnerabilities(self):
        data = self.data / "vulnerablecode/django-5.0_package_data.json"
        response_json = json.loads(data.read_text())
        package_data = response_json.get("results")[0]
        vulnerability_data = package_data["affected_by_vulnerabilities"]
        self.assertEqual(30, len(vulnerability_data))

        vulnerability1 = vulnerability_data[0]
        self.assertEqual(
            "pypa/django/PYSEC-2024-56", vulnerability1.get("advisory_uid")
        )
        ignore_set = {vulnerability1.get("advisory_uid")}
        self.assertEqual(
            29, len(filter_vulnerabilities(vulnerability_data, ignore_set))
        )

        ignore_set = {vulnerability1.get("aliases")[0]}
        self.assertEqual(
            29, len(filter_vulnerabilities(vulnerability_data, ignore_set))
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

    def test_scanpipe_pipes_vulnerablecode_get_plain_purl(self):
        purl = "pkg:pypi/django@5.0?file_name=Django-5.0.tar.gz"
        self.assertEqual("pkg:pypi/django@5.0", get_plain_purl(purl))
        purl = "pkg:maven/org.apache/commons@1.0?classifier=sources#path/to"
        self.assertEqual("pkg:maven/org.apache/commons@1.0", get_plain_purl(purl))
        purl = "pkg:npm/express@4.18.2"
        self.assertEqual(purl, get_plain_purl(purl))

    def test_scanpipe_pipes_vulnerablecode_get_packages_by_plain_purl(self):
        package1 = make_package(self.project1, "pkg:deb/debian/adduser@3.118?arch=all")
        package2 = make_package(self.project1, "pkg:deb/debian/adduser@3.118?arch=x86")
        package3 = make_package(self.project1, "pkg:npm/express@4.18.2")
        package4 = DiscoveredPackage.objects.create(project=self.project1)

        packages_by_plain_purl = get_packages_by_plain_purl(
            [package1, package2, package3, package4]
        )
        expected = {
            "pkg:deb/debian/adduser@3.118": [package1, package2],
            "pkg:npm/express@4.18.2": [package3],
        }
        self.assertEqual(expected, packages_by_plain_purl)
        self.assertEqual({}, get_packages_by_plain_purl([]))

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    def test_scanpipe_pipes_vulnerablecode_request_json(self, mock_request):
        mock_request.return_value = make_response(make_page([]))
        response_data = request_json("POST", PACKAGES_URL, {"purls": []}, 10, API_URL)
        self.assertEqual(make_page([]), response_data)
        mock_request.assert_called_once_with(
            "POST", PACKAGES_URL, json={"purls": []}, timeout=10
        )

        mock_request.reset_mock()
        for url in [
            "https://other.example/api/v3/packages",
            "https://vulnerablecode.example.other.example/api/v3/packages",
            "https://vulnerablecode.example/api/v3evil/packages",
            "http://vulnerablecode.example/api/v3/packages",
        ]:
            with self.assertRaises(VulnerableCodeError, msg=url):
                request_json("GET", url, api_url=API_URL)
        mock_request.assert_not_called()

        mock_request.return_value = make_response({}, status_code=503)
        with self.assertRaises(requests.HTTPError):
            request_json("GET", PACKAGES_URL, api_url=API_URL)

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    def test_scanpipe_pipes_vulnerablecode_get_all_results(self, mock_request):
        next_url = f"{PACKAGES_URL}?page=2"
        mock_request.side_effect = [
            make_response(
                make_page(["result1", "result2"], count=3, next_url=next_url)
            ),
            make_response(make_page(["result3"], count=3)),
        ]
        all_results = get_all_results(
            "POST", PACKAGES_URL, {"purls": []}, None, API_URL
        )
        self.assertEqual(["result1", "result2", "result3"], all_results)
        expected_calls = [
            mock.call("POST", PACKAGES_URL, json={"purls": []}, timeout=None),
            mock.call("POST", next_url, json={"purls": []}, timeout=None),
        ]
        self.assertEqual(expected_calls, mock_request.call_args_list)

        mock_request.reset_mock()
        mock_request.side_effect = [
            make_response(make_page(["result1"], count=2)),
        ]
        with self.assertRaisesMessage(VulnerableCodeError, "1 results out of 2"):
            get_all_results("GET", PACKAGES_URL, api_url=API_URL)

        mock_request.reset_mock()
        mock_request.side_effect = [
            make_response(make_page(["result1"], count=2, next_url=next_url)),
            make_response(make_page([], count=2, next_url=next_url)),
            make_response(make_page([], count=2, next_url=next_url)),
        ]
        with self.assertRaises(VulnerableCodeError):
            get_all_results("GET", PACKAGES_URL, api_url=API_URL)
        self.assertEqual(3, mock_request.call_count)

        mock_request.reset_mock()
        mock_request.side_effect = [
            make_response(
                make_page(["result1"], count=2, next_url="https://other.example/")
            ),
        ]
        expected_message = "URL outside of the VulnerableCode API"
        with self.assertRaisesMessage(VulnerableCodeError, expected_message):
            get_all_results("GET", PACKAGES_URL, api_url=API_URL)
        self.assertEqual(1, mock_request.call_count)

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    def test_scanpipe_pipes_vulnerablecode_get_all_results_proxied_links(
        self, mock_request
    ):
        # A link built behind a proxy can use another scheme and host.
        proxied_next_url = "http://vulnerablecode:8000/api/v3/packages?page=2"
        mock_request.side_effect = [
            make_response(make_page(["result1"], count=2, next_url=proxied_next_url)),
            make_response(make_page(["result2"], count=2)),
        ]
        all_results = get_all_results("GET", PACKAGES_URL, api_url=API_URL)
        self.assertEqual(["result1", "result2"], all_results)
        next_request_url = mock_request.call_args_list[1].args[1]
        self.assertEqual(f"{PACKAGES_URL}?page=2", next_request_url)

    def test_scanpipe_pipes_vulnerablecode_get_api_link(self):
        link_url = "http://vulnerablecode:8000/api/v3/packages/1/advisories?page=3"
        expected = f"{PACKAGES_URL}/1/advisories?page=3"
        self.assertEqual(expected, get_api_link(link_url, API_URL))

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    def test_scanpipe_pipes_vulnerablecode_bulk_search_by_purl(self, mock_request):
        purls = [f"pkg:deb/debian/fixture-{index:03d}@1.0" for index in range(101)]
        package_entries = [make_package_data(purl, []) for purl in purls]
        next_url = f"{PACKAGES_URL}?page=2"
        mock_request.side_effect = [
            make_response(make_page(package_entries[:100], 101, next_url)),
            make_response(make_page(package_entries[100:], 101)),
        ]

        self.assertEqual(package_entries, bulk_search_by_purl(purls, api_url=API_URL))
        expected_data = {
            "purls": purls,
            "details": True,
            "reachability": True,
            "ignore_qualifiers_subpath": True,
        }
        expected_calls = [
            mock.call("POST", PACKAGES_URL, json=expected_data, timeout=None),
            mock.call("POST", next_url, json=expected_data, timeout=None),
        ]
        self.assertEqual(expected_calls, mock_request.call_args_list)

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    def test_scanpipe_pipes_vulnerablecode_get_affected_by_vulnerabilities(
        self, mock_request
    ):
        package_data = make_package_data("pkg:deb/debian/bash@5.0", ["ID-1"])
        affected_by = get_affected_by_vulnerabilities(package_data, api_url=API_URL)
        self.assertEqual(package_data["affected_by_vulnerabilities"], affected_by)
        package_data = make_package_data("pkg:deb/debian/bash@5.0", [])
        self.assertEqual([], get_test_api_affected_by(package_data))
        mock_request.assert_not_called()

        affected_by_url = f"{API_URL}/affected-by-advisories?purl=pkg%3Adeb"
        package_data = {
            "purl": "pkg:deb/debian/bash@5.0",
            "affected_by_vulnerabilities_url": affected_by_url,
        }
        advisories = [{"advisory_uid": "ID-1"}, {"advisory_uid": "ID-2"}]
        mock_request.return_value = make_response(make_page(advisories))
        self.assertEqual(advisories, get_test_api_affected_by(package_data))
        mock_request.assert_called_once_with(
            "GET", affected_by_url, json=None, timeout=None
        )

        with self.assertRaisesMessage(VulnerableCodeError, "pkg:deb/debian/bash@5.0"):
            get_test_api_affected_by({"purl": "pkg:deb/debian/bash@5.0"})

    @mock.patch("scanpipe.pipes.vulnerablecode.bulk_search_by_purl")
    def test_scanpipe_pipes_vulnerablecode_get_vulnerabilities_by_plain_purl(
        self, mock_search_by_purl
    ):
        mock_search_by_purl.return_value = [
            make_package_data("pkg:deb/debian/bash@5.0", ["ID-1"]),
            make_package_data("pkg:deb/debian/bash@5.0?arch=amd64", ["ID-1", "ID-2"]),
            make_package_data("pkg:npm/express@4.18.2", []),
        ]
        plain_purls = ["pkg:deb/debian/bash@5.0", "pkg:npm/express@4.18.2"]
        vulnerabilities = get_vulnerabilities_by_plain_purl(plain_purls, chunk_size=10)
        advisory_uids = {
            plain_purl: [vulnerability["advisory_uid"] for vulnerability in affected_by]
            for plain_purl, affected_by in vulnerabilities.items()
        }
        expected = {
            "pkg:deb/debian/bash@5.0": ["ID-1", "ID-2"],
            "pkg:npm/express@4.18.2": [],
        }
        self.assertEqual(expected, advisory_uids)

        mock_search_by_purl.return_value = [
            make_package_data("pkg:deb/debian/other@5.0", ["ID-1"]),
        ]
        with self.assertRaisesMessage(VulnerableCodeError, "pkg:deb/debian/other@5.0"):
            get_vulnerabilities_by_plain_purl(plain_purls, chunk_size=10)

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    @mock.patch(
        "scanpipe.pipes.vulnerablecode.bulk_search_by_purl", side_effect=search_test_api
    )
    def test_scanpipe_pipes_vulnerablecode_fetch_vulnerabilities_pagination(
        self, mock_search_by_purl, mock_request
    ):
        purls = [f"pkg:deb/debian/fixture-{index:03d}@1.0" for index in range(101)]
        packages = [make_package(self.project1, purl) for purl in purls]
        package_entries = [make_package_data(purl, []) for purl in purls[:100]]
        package_entries.append(make_package_data(purls[100], ["ID-1"]))
        next_url = f"{PACKAGES_URL}?page=2"
        mock_request.side_effect = [
            make_response(make_page(package_entries[:100], 101, next_url)),
            make_response(make_page(package_entries[100:], 101)),
        ]

        fetch_vulnerabilities(packages=packages)
        last_package = packages[100]
        last_package.refresh_from_db()
        affected_by = package_entries[100]["affected_by_vulnerabilities"]
        self.assertEqual(affected_by, last_package.affected_by_vulnerabilities)
        self.assertEqual(2, mock_request.call_count)

    @mock.patch(
        "scanpipe.pipes.vulnerablecode.get_affected_by_vulnerabilities",
        side_effect=get_test_api_affected_by,
    )
    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    @mock.patch("scanpipe.pipes.vulnerablecode.bulk_search_by_purl")
    def test_scanpipe_pipes_vulnerablecode_fetch_vulnerabilities_affected_by_url(
        self, mock_search_by_purl, mock_request, mock_get_affected_by
    ):
        package = make_package(self.project1, "pkg:deb/debian/linux@6.1")
        affected_by_url = f"{API_URL}/affected-by-advisories?purl=pkg%3Adeb"
        mock_search_by_purl.return_value = [
            {
                "purl": "pkg:deb/debian/linux@6.1",
                "affected_by_vulnerabilities_url": affected_by_url,
            }
        ]
        advisories = [{"advisory_uid": f"ID-{index}"} for index in range(101)]
        mock_request.side_effect = [
            make_response(
                make_page(advisories[:100], 101, f"{affected_by_url}&page=2")
            ),
            make_response(make_page(advisories[100:], 101)),
        ]

        fetch_vulnerabilities(packages=[package])
        package.refresh_from_db()
        self.assertEqual(advisories, package.affected_by_vulnerabilities)

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    @mock.patch(
        "scanpipe.pipes.vulnerablecode.bulk_search_by_purl", side_effect=search_test_api
    )
    def test_scanpipe_pipes_vulnerablecode_fetch_vulnerabilities_qualified_purls(
        self, mock_search_by_purl, mock_request
    ):
        pypi_sdist = "pkg:pypi/owned@1.0?file_name=owned-1.0.tar.gz"
        pypi_wheel = "pkg:pypi/owned@1.0?file_name=owned-1.0-py3-none-any.whl"
        deb = "pkg:deb/debian/bash@5.0?arch=amd64"
        maven = "pkg:maven/org.example/lib@1.0?classifier=sources"
        packages = [
            make_package(self.project1, purl)
            for purl in [pypi_sdist, pypi_wheel, deb, maven]
        ]
        mock_request.return_value = make_response(
            make_page(
                [
                    make_package_data("pkg:deb/debian/bash@5.0", ["ID-1"]),
                    make_package_data("pkg:deb/debian/bash@5.0?distro=bookworm", []),
                    make_package_data("pkg:maven/org.example/lib@1.0", ["ID-2"]),
                    make_package_data("pkg:pypi/owned@1.0", ["ID-3"]),
                ]
            )
        )

        fetch_vulnerabilities(packages=packages)
        stored_advisory_uids = []
        for package in packages:
            package.refresh_from_db()
            stored_advisory_uids.append(
                [
                    vulnerability["advisory_uid"]
                    for vulnerability in package.affected_by_vulnerabilities
                ]
            )
        self.assertEqual([["ID-3"], ["ID-3"], ["ID-1"], ["ID-2"]], stored_advisory_uids)

        request_data = mock_request.call_args.kwargs["json"]
        expected_purls = [
            "pkg:pypi/owned@1.0",
            "pkg:deb/debian/bash@5.0",
            "pkg:maven/org.example/lib@1.0",
        ]
        self.assertEqual(expected_purls, request_data["purls"])
        self.assertTrue(request_data["ignore_qualifiers_subpath"])

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    @mock.patch(
        "scanpipe.pipes.vulnerablecode.bulk_search_by_purl", side_effect=search_test_api
    )
    def test_scanpipe_pipes_vulnerablecode_fetch_vulnerabilities_lookup_failure(
        self, mock_search_by_purl, mock_request
    ):
        package1 = make_package(self.project1, "pkg:npm/first@1.0")
        package2 = make_package(self.project1, "pkg:npm/second@1.0")
        mock_request.side_effect = [
            make_response(
                make_page([make_package_data(package1.package_url, ["ID-1"])])
            ),
            make_response({}, status_code=503),
        ]

        with self.assertRaises(requests.HTTPError):
            fetch_vulnerabilities(packages=[package1, package2], chunk_size=1)
        package1.refresh_from_db()
        self.assertEqual([], package1.affected_by_vulnerabilities)

        mock_request.side_effect = [make_response(["not", "a", "page"])]
        with self.assertRaises(TypeError):
            fetch_vulnerabilities(packages=[package1])

    @mock.patch("scanpipe.pipes.vulnerablecode.session.request")
    @mock.patch(
        "scanpipe.pipes.vulnerablecode.bulk_search_by_purl", side_effect=search_test_api
    )
    def test_scanpipe_pipes_vulnerablecode_fetch_vulnerabilities_refresh(
        self, mock_search_by_purl, mock_request
    ):
        stale_vulnerabilities = [{"advisory_uid": "OLD-1"}]
        fixed = make_package(self.project1, "pkg:npm/fixed@1.0")
        ignored = make_package(self.project1, "pkg:npm/ignored@1.0")
        unknown = make_package(self.project1, "pkg:npm/unknown@1.0")
        packages = [fixed, ignored, unknown]
        for package in packages:
            package.update(affected_by_vulnerabilities=stale_vulnerabilities)

        mock_request.return_value = make_response(
            make_page(
                [
                    make_package_data("pkg:npm/fixed@1.0", []),
                    make_package_data("pkg:npm/ignored@1.0", ["ID-1"]),
                ]
            )
        )
        buffer = io.StringIO()
        fetch_vulnerabilities(packages, logger=buffer.write, ignore_set={"ID-1"})
        for package in packages:
            package.refresh_from_db()

        self.assertEqual([], fixed.affected_by_vulnerabilities)
        self.assertEqual([], ignored.affected_by_vulnerabilities)
        self.assertEqual(stale_vulnerabilities, unknown.affected_by_vulnerabilities)
        self.assertEqual(
            "2 discovered packages updated with vulnerability data.", buffer.getvalue()
        )

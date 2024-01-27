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
from collections import defaultdict
from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe.models import AbstractTaskFieldsModel
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import purldb
from scanpipe.tests import dependency_data2
from scanpipe.tests import dependency_data3
from scanpipe.tests import make_resource_file
from scanpipe.tests import package_data1


class ScanPipePurlDBTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_pipes_purldb_get_unique_resolved_purls(self):
        DiscoveredPackage.create_from_data(self.project1, package_data1)
        CodebaseResource.objects.create(
            project=self.project1, path="data.tar.gz-extract/Gemfile.lock"
        )
        DiscoveredDependency.create_from_data(self.project1, dependency_data2)

        expected = {"pkg:gem/appraisal@2.2.0"}
        result = purldb.get_unique_resolved_purls(self.project1)

        self.assertEqual(expected, result)

    def test_scanpipe_pipes_purldb_get_unique_unresolved_purls(self):
        DiscoveredPackage.create_from_data(self.project1, package_data1)
        CodebaseResource.objects.create(
            project=self.project1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        DiscoveredDependency.create_from_data(self.project1, dependency_data3)

        expected = {("pkg:pypi/dask", "vers:pypi/>=1.0")}
        result = purldb.get_unique_unresolved_purls(self.project1)

        self.assertEqual(expected, result)

    @mock.patch("scanpipe.pipes.purldb.request_post")
    @mock.patch("scanpipe.pipes.purldb.is_available")
    def test_scanpipe_pipes_purldb_feed_purldb(
        self, mock_is_available, mock_request_post
    ):
        mock_is_available.return_value = True

        packages = [("pkg:pypi/dask", "vers:pypi/>=1.0")]

        def mock_request_post_return(url, data, headers, timeout):
            return {
                "queued_packages_count": 1,
                "queued_packages": [],
                "unqueued_packages_count": 1,
                "unqueued_packages": [],
                "unsupported_packages_count": 0,
                "unsupported_packages": [],
            }

        mock_request_post.side_effect = mock_request_post_return

        buffer = io.StringIO()
        purldb.feed_purldb(
            packages=packages,
            chunk_size=10,
            logger=buffer.write,
        )

        expected_log = buffer.getvalue()
        self.assertIn(
            "Successfully queued 1 PURLs for indexing in PurlDB", expected_log
        )
        self.assertIn(
            "1 PURLs were already present in PurlDB index queue", expected_log
        )

    @mock.patch("scanpipe.pipes.purldb.request_post")
    @mock.patch("scanpipe.pipes.purldb.is_available")
    def test_scanpipe_pipes_purldb_send_project_json_to_matchcode(
        self, mock_is_available, mock_request_post
    ):
        mock_is_available.return_value = True

        def mock_request_post_return(url, files, timeout):
            request_post_response_loc = (
                self.data_location
                / "purldb"
                / "match_to_purldb"
                / "request_post_response.json"
            )
            with open(request_post_response_loc, "r") as f:
                return json.load(f)

        mock_request_post.side_effect = mock_request_post_return

        run_url = purldb.send_project_json_to_matchcode(self.project1)
        expected_run_url = (
            "http://192.168.1.12/api/runs/52b2930d-6e85-4b3e-ba3e-17dd9a618650/"
        )
        self.assertEqual(expected_run_url, run_url)

    @mock.patch("scanpipe.pipes.purldb.request_get")
    @mock.patch("scanpipe.pipes.purldb.is_available")
    def test_scanpipe_pipes_purldb_poll_until_success(
        self, mock_is_available, mock_request_get
    ):
        run_status = AbstractTaskFieldsModel.Status

        mock_is_available.return_value = True

        # Success
        run_url = "http://192.168.1.12/api/runs/52b2930d-6e85-4b3e-ba3e-17dd9a618650/"
        mock_request_get.side_effect = [
            {
                "url": run_url,
                "status": run_status.NOT_STARTED,
            },
            {
                "url": run_url,
                "status": run_status.QUEUED,
            },
            {
                "url": run_url,
                "status": run_status.RUNNING,
            },
            {
                "url": run_url,
                "status": run_status.SUCCESS,
            },
        ]
        return_value = purldb.poll_until_success(run_url)
        self.assertEqual(True, return_value)

        # Failure
        mock_request_get.side_effect = [
            {
                "url": run_url,
                "status": run_status.NOT_STARTED,
            },
            {
                "url": run_url,
                "status": run_status.QUEUED,
            },
            {
                "url": run_url,
                "status": run_status.RUNNING,
            },
            {
                "url": run_url,
                "status": run_status.FAILURE,
                "log": "failure message",
            },
        ]
        with self.assertRaises(Exception) as context:
            purldb.poll_until_success(run_url)
        self.assertTrue("failure message" in str(context.exception))

        # Stopped
        mock_request_get.side_effect = [
            {
                "url": run_url,
                "status": run_status.NOT_STARTED,
            },
            {
                "url": run_url,
                "status": run_status.QUEUED,
            },
            {
                "url": run_url,
                "status": run_status.RUNNING,
            },
            {
                "url": run_url,
                "status": run_status.STOPPED,
                "log": "stop message",
            },
        ]
        with self.assertRaises(Exception) as context:
            purldb.poll_until_success(run_url)
        self.assertTrue("stop message" in str(context.exception))

        # Stale
        mock_request_get.side_effect = [
            {
                "url": run_url,
                "status": run_status.NOT_STARTED,
            },
            {
                "url": run_url,
                "status": run_status.QUEUED,
            },
            {
                "url": run_url,
                "status": run_status.RUNNING,
            },
            {
                "url": run_url,
                "status": run_status.STALE,
                "log": "stale message",
            },
        ]
        with self.assertRaises(Exception) as context:
            purldb.poll_until_success(run_url)
        self.assertTrue("stale message" in str(context.exception))

    def test_scanpipe_pipes_purldb_map_match_results(self):
        request_post_response_loc = (
            self.data_location
            / "purldb"
            / "match_to_purldb"
            / "request_get_results_response.json"
        )
        with open(request_post_response_loc, "r") as f:
            match_results = json.load(f)

        resource_paths_by_package_uids = purldb.map_match_results(match_results)
        expected = defaultdict(list)
        expected_package_uid = (
            "pkg:maven/org.elasticsearch/elasticsearch-x-content@7.17.9"
            "?classifier=sources&uuid=a8814800-8120-4f50-ba4f-08c443ccda8e"
        )
        expected[expected_package_uid].append(
            "elasticsearch-x-content-7.17.9-sources.jar"
        )
        self.assertEqual(expected, resource_paths_by_package_uids)

    def test_scanpipe_pipes_purldb_create_packages_from_match_results(self):
        r1 = make_resource_file(
            self.project1,
            path="elasticsearch-x-content-7.17.9-sources.jar",
            sha1="30d21add57abe04beece3f28a079671dbc9043e4",
        )
        r2 = make_resource_file(
            self.project1,
            path="something-else.json",
            sha1="deadbeef",
        )

        request_get_results_response_loc = (
            self.data_location
            / "purldb"
            / "match_to_purldb"
            / "request_get_results_response.json"
        )
        with open(request_get_results_response_loc, "r") as f:
            match_results = json.load(f)

        self.assertEqual(0, self.project1.discoveredpackages.all().count())
        self.assertFalse(0, len(r1.for_packages))
        self.assertFalse(0, len(r2.for_packages))

        purldb.create_packages_from_match_results(self.project1, match_results)

        self.assertEqual(1, self.project1.discoveredpackages.all().count())
        package = self.project1.discoveredpackages.first()
        self.assertEqual([package.package_uid], r1.for_packages)
        # This resource should not have a Package match
        self.assertFalse(0, len(r2.for_packages))

    @mock.patch("scanpipe.pipes.purldb.request_get")
    @mock.patch("scanpipe.pipes.purldb.is_available")
    def test_scanpipe_pipes_purldb_get_match_results(
        self, mock_is_available, mock_request_get
    ):
        mock_is_available.return_value = True

        request_get_check_response_loc = (
            self.data_location
            / "purldb"
            / "match_to_purldb"
            / "request_get_check_response.json"
        )
        with open(request_get_check_response_loc, "r") as f:
            mock_request_get_check_return = json.load(f)

        request_get_results_response_loc = (
            self.data_location
            / "purldb"
            / "match_to_purldb"
            / "request_get_results_response.json"
        )
        with open(request_get_results_response_loc, "r") as f:
            mock_request_get_results_return = json.load(f)
        mock_request_get.side_effect = [
            mock_request_get_check_return,
            mock_request_get_results_return,
        ]

        run_url = "http://192.168.1.12/api/runs/52b2930d-6e85-4b3e-ba3e-17dd9a618650/"
        match_results = purldb.get_match_results(run_url)

        self.assertEqual(mock_request_get_results_return, match_results)

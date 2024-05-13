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
from collections import defaultdict
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from scanpipe.models import AbstractTaskFieldsModel
from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import matchcode
from scanpipe.pipes.input import copy_input
from scanpipe.tests import make_resource_file


class MatchCodePipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_pipes_matchcode_fingerprint_codebase_directories(self):
        fixtures = self.data_location / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        matchcode.fingerprint_codebase_directories(project)
        directory = project.codebaseresources.get(
            path="asgiref-3.3.0-py3-none-any.whl-extract"
        )
        expected_directory_fingerprints = {
            "directory_content": "0000000ef11d2819221282031466c11a367bba72",
            "directory_structure": "0000000e0e30a50b5eb8c495f880c087325e6062",
        }
        self.assertEqual(expected_directory_fingerprints, directory.extra_data)

    @mock.patch("scanpipe.pipes.matchcode.request_post")
    @mock.patch("scanpipe.pipes.matchcode.is_available")
    def test_scanpipe_pipes_matchcode_send_project_json_to_matchcode(
        self, mock_is_available, mock_request_post
    ):
        mock_is_available.return_value = True

        def mock_request_post_return(url, files, timeout):
            request_post_response_loc = (
                self.data_location
                / "matchcode"
                / "match_to_matchcode"
                / "request_post_response.json"
            )
            with open(request_post_response_loc, "r") as f:
                return json.load(f)

        mock_request_post.side_effect = mock_request_post_return

        run_url = matchcode.send_project_json_to_matchcode(self.project1)
        expected_run_url = (
            "http://192.168.1.12/api/runs/52b2930d-6e85-4b3e-ba3e-17dd9a618650/"
        )
        self.assertEqual(expected_run_url, run_url)

    @mock.patch("scanpipe.pipes.matchcode.request_get")
    @mock.patch("scanpipe.pipes.matchcode.is_available")
    def test_scanpipe_pipes_matchcode_get_run_url_status(
        self, mock_is_available, mock_request_get
    ):
        mock_is_available.return_value = True

        request_get_check_response_loc = (
            self.data_location
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_check_response.json"
        )
        with open(request_get_check_response_loc, "r") as f:
            mock_request_get_check_return = json.load(f)

        mock_request_get.side_effect = [
            mock_request_get_check_return,
        ]

        run_url = "http://192.168.1.12/api/runs/52b2930d-6e85-4b3e-ba3e-17dd9a618650/"
        status = matchcode.get_run_url_status(run_url)

        self.assertEqual("success", status)

    @mock.patch("scanpipe.pipes.matchcode.request_get")
    @mock.patch("scanpipe.pipes.matchcode.is_available")
    def test_scanpipe_pipes_matchcode_poll_run_url_status(
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
        return_value = matchcode.poll_run_url_status(run_url)
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
            {
                "url": run_url,
                "status": run_status.FAILURE,
                "log": "failure message",
            },
        ]
        with self.assertRaises(Exception) as context:
            matchcode.poll_run_url_status(run_url)
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
            {
                "url": run_url,
                "status": run_status.STOPPED,
                "log": "stop message",
            },
        ]
        with self.assertRaises(Exception) as context:
            matchcode.poll_run_url_status(run_url)
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
            {
                "url": run_url,
                "status": run_status.STALE,
                "log": "stale message",
            },
        ]
        with self.assertRaises(Exception) as context:
            matchcode.poll_run_url_status(run_url)
        self.assertTrue("stale message" in str(context.exception))

    def test_scanpipe_pipes_matchcode_map_match_results(self):
        request_post_response_loc = (
            self.data_location
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_results_response.json"
        )
        with open(request_post_response_loc, "r") as f:
            match_results = json.load(f)

        resource_paths_by_package_uids = matchcode.map_match_results(match_results)
        expected = defaultdict(list)
        expected_package_uid = (
            "pkg:maven/org.elasticsearch/elasticsearch-x-content@7.17.9"
            "?classifier=sources&uuid=a8814800-8120-4f50-ba4f-08c443ccda8e"
        )
        expected[expected_package_uid].append(
            "elasticsearch-x-content-7.17.9-sources.jar"
        )
        self.assertEqual(expected, resource_paths_by_package_uids)

    def test_scanpipe_pipes_matchcode_create_packages_from_match_results(self):
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
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_results_response.json"
        )
        with open(request_get_results_response_loc, "r") as f:
            match_results = json.load(f)

        self.assertEqual(0, self.project1.discoveredpackages.all().count())
        self.assertFalse(0, len(r1.for_packages))
        self.assertFalse(0, len(r2.for_packages))

        matchcode.create_packages_from_match_results(self.project1, match_results)

        self.assertEqual(1, self.project1.discoveredpackages.all().count())
        package = self.project1.discoveredpackages.first()
        self.assertEqual([package.package_uid], r1.for_packages)
        # This resource should not have a Package match
        self.assertFalse(0, len(r2.for_packages))

    @mock.patch("scanpipe.pipes.matchcode.request_get")
    @mock.patch("scanpipe.pipes.matchcode.is_available")
    def test_scanpipe_pipes_matchcode_get_match_results(
        self, mock_is_available, mock_request_get
    ):
        mock_is_available.return_value = True

        request_get_check_response_loc = (
            self.data_location
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_check_response.json"
        )
        with open(request_get_check_response_loc, "r") as f:
            mock_request_get_check_return = json.load(f)

        request_get_results_response_loc = (
            self.data_location
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_results_response.json"
        )
        with open(request_get_results_response_loc, "r") as f:
            mock_request_get_results_return = json.load(f)
        mock_request_get.side_effect = [
            mock_request_get_check_return,
            mock_request_get_results_return,
        ]

        run_url = "http://192.168.1.12/api/runs/52b2930d-6e85-4b3e-ba3e-17dd9a618650/"
        match_results = matchcode.get_match_results(run_url)

        self.assertEqual(mock_request_get_results_return, match_results)

    def test_scanpipe_pipes_matchcode_fingerprint_codebase_resources(self):
        copy_input(self.data_location / "notice.NOTICE", self.project1.codebase_path)
        codebase_resource1 = CodebaseResource.objects.create(
            project=self.project1, path="notice.NOTICE", is_text=True
        )

        # This resource should not have a fingerprint
        copy_input(self.data_location / "is-npm-1.0.0.tgz", self.project1.codebase_path)
        codebase_resource2 = CodebaseResource.objects.create(
            project=self.project1, path="is-npm-1.0.0.tgz"
        )

        matchcode.fingerprint_codebase_resources(self.project1)
        codebase_resource1.refresh_from_db()
        codebase_resource2.refresh_from_db()

        expected_extra_data = {"halo1": "000000b8ef420f7e84c8c74c691315f0a06ac4f0"}
        self.assertEqual(expected_extra_data, codebase_resource1.extra_data)
        self.assertFalse(codebase_resource2.extra_data)

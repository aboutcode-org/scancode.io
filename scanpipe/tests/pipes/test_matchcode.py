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
    data = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_pipes_matchcode_fingerprint_codebase_directories(self):
        fixtures = self.data / "asgiref" / "asgiref-3.3.0_fixtures.json"
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
                self.data
                / "matchcode"
                / "match_to_matchcode"
                / "request_post_response.json"
            )
            with open(request_post_response_loc) as f:
                return json.load(f)

        mock_request_post.side_effect = mock_request_post_return

        match_url, run_url = matchcode.send_project_json_to_matchcode(self.project1)
        expected_match_url = (
            "http://192.168.1.12/api/matching/65bf1e6d-6bff-4841-9c9b-db5cf25edfa7/"
        )
        expected_run_url = (
            "http://192.168.1.12/api/runs/52b2930d-6e85-4b3e-ba3e-17dd9a618650/"
        )
        self.assertEqual(expected_match_url, match_url)
        self.assertEqual(expected_run_url, run_url)

    @mock.patch("scanpipe.pipes.matchcode.request_post")
    def test_scanpipe_pipes_matchcode_send_project_json_to_matchcode_failed_request(
        self, mock_request_post
    ):
        mock_request_post.return_value = None
        with self.assertRaises(matchcode.MatchCodeIOException) as context:
            matchcode.send_project_json_to_matchcode(self.project1)
        self.assertEqual("Invalid response from MatchCode.io", str(context.exception))

    @mock.patch("scanpipe.pipes.matchcode.request_get")
    @mock.patch("scanpipe.pipes.matchcode.is_available")
    def test_scanpipe_pipes_matchcode_get_run_url_status(
        self, mock_is_available, mock_request_get
    ):
        mock_is_available.return_value = True

        request_get_check_response_loc = (
            self.data
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_check_response.json"
        )
        with open(request_get_check_response_loc) as f:
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
        return_value = matchcode.poll_run_url_status(run_url, sleep=0)
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
        with self.assertRaises(matchcode.MatchCodeIOException) as context:
            matchcode.poll_run_url_status(run_url, sleep=0)
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
        with self.assertRaises(matchcode.MatchCodeIOException) as context:
            matchcode.poll_run_url_status(run_url, sleep=0)
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
        with self.assertRaises(matchcode.MatchCodeIOException) as context:
            matchcode.poll_run_url_status(run_url, sleep=0)
        self.assertTrue("stale message" in str(context.exception))

    def test_scanpipe_pipes_matchcode_map_match_results(self):
        request_post_response_loc = (
            self.data
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_results_response.json"
        )
        with open(request_post_response_loc) as f:
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
            self.data
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_results_response.json"
        )
        with open(request_get_results_response_loc) as f:
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

    def test_scanpipe_pipes_matchcode_create_match_results_url(self):
        match_url = (
            "http://192.168.1.12/api/matching/65bf1e6d-6bff-4841-9c9b-db5cf25edfa7/"
        )
        expected_match_url = "http://192.168.1.12/api/matching/65bf1e6d-6bff-4841-9c9b-db5cf25edfa7/results/"
        self.assertEqual(
            expected_match_url, matchcode.create_match_results_url(match_url)
        )

    @mock.patch("scanpipe.pipes.matchcode.request_get")
    @mock.patch("scanpipe.pipes.matchcode.is_available")
    def test_scanpipe_pipes_matchcode_get_match_results(
        self, mock_is_available, mock_request_get
    ):
        mock_is_available.return_value = True
        request_get_results_response_loc = (
            self.data
            / "matchcode"
            / "match_to_matchcode"
            / "request_get_results_response.json"
        )
        with open(request_get_results_response_loc) as f:
            mock_request_get_results_return = json.load(f)
        mock_request_get.side_effect = [
            mock_request_get_results_return,
        ]

        match_url = (
            "http://192.168.1.12/api/matching/65bf1e6d-6bff-4841-9c9b-db5cf25edfa7/"
        )
        match_results = matchcode.get_match_results(match_url)
        self.assertEqual(mock_request_get_results_return, match_results)

    def test_scanpipe_pipes_matchcode_fingerprint_codebase_resources(self):
        copy_input(
            self.data / "aboutcode" / "notice.NOTICE", self.project1.codebase_path
        )
        codebase_resource1 = CodebaseResource.objects.create(
            project=self.project1, path="notice.NOTICE", is_text=True
        )

        # This resource should not have a fingerprint
        copy_input(
            self.data / "scancode" / "is-npm-1.0.0.tgz", self.project1.codebase_path
        )
        codebase_resource2 = CodebaseResource.objects.create(
            project=self.project1, path="is-npm-1.0.0.tgz"
        )

        matchcode.fingerprint_codebase_resources(self.project1)
        codebase_resource1.refresh_from_db()
        codebase_resource2.refresh_from_db()

        expected_extra_data = {
            "halo1": "000000bb07ba9a3efeafb3b1f182d1ce676466dc",
            "snippets": [
                {"position": 0, "snippet": "a222da2349af431e00eda7db2e3927c9"},
                {"position": 9, "snippet": "41afe78186e3ab44d03fc23f610fbf01"},
                {"position": 12, "snippet": "8b76e8aaec35ef10ca5028ed6fbc2f3e"},
                {"position": 27, "snippet": "de2c6a569b9b2bb8465bfee051198610"},
                {"position": 28, "snippet": "9d406cbede0f5656e9e206c48b2b9706"},
                {"position": 29, "snippet": "d45754ec18c24a4d598d8ad82606cbff"},
                {"position": 44, "snippet": "6b3f26c03647ea3b278b545d86bf05ea"},
                {"position": 49, "snippet": "c0bb0e522f0148fd64ddf024d3bd7011"},
                {"position": 63, "snippet": "3600ad4853cbcb1df467d53db5c16bd7"},
                {"position": 78, "snippet": "21a4946fda5c3fa0a8eaf926860f11ae"},
                {"position": 86, "snippet": "f810ec1f64235fcd2b25ad96415fc4ee"},
                {"position": 101, "snippet": "b534e5e3867ba340df1f6e525205e0aa"},
                {"position": 102, "snippet": "0ecde2653b775c17ab3ac657fc99cb1b"},
                {"position": 117, "snippet": "75a3cec7239416c7dde11c1142a0fe87"},
                {"position": 123, "snippet": "edaa60b3d6bceed9cfb1f0e9684d690e"},
                {"position": 138, "snippet": "f2de939f879b7ab7490a25e83e0ca0df"},
                {"position": 153, "snippet": "6a37eed93df6eab45335471ffdf45e4e"},
                {"position": 154, "snippet": "03eee824319f4a9d37e1f77791767978"},
                {"position": 159, "snippet": "8907fe2bac6b5ab7bd777d5f4dd38c89"},
                {"position": 163, "snippet": "b4191cd30ca5a2f8affdf89fa83eca55"},
                {"position": 174, "snippet": "4559ff1b65f8eb1117edc0572829698d"},
                {"position": 175, "snippet": "cca770f84ad46cbdcac4d27456ce6c00"},
            ],
        }
        self.assertEqual(expected_extra_data, codebase_resource1.extra_data)
        self.assertFalse(codebase_resource2.extra_data)

    def test_scanpipe_pipes_matchcode_fingerprint_stemmed_codebase_resources(self):
        # This resource should not have a fingerprint
        copy_input(
            self.data / "aboutcode" / "notice.NOTICE", self.project1.codebase_path
        )
        codebase_resource1 = CodebaseResource.objects.create(
            project=self.project1, path="notice.NOTICE", is_text=True
        )

        # This resource should not have a fingerprint
        copy_input(
            self.data / "scancode" / "is-npm-1.0.0.tgz", self.project1.codebase_path
        )
        codebase_resource2 = CodebaseResource.objects.create(
            project=self.project1, path="is-npm-1.0.0.tgz"
        )

        # This resource should have a fingerprint
        copy_input(
            self.data / "matchcode" / "fingerprinting" / "inherits.js",
            self.project1.codebase_path,
        )
        codebase_resource3 = CodebaseResource.objects.create(
            project=self.project1,
            path="inherits.js",
            is_text=True,
            programming_language="JavaScript",
        )

        matchcode.fingerprint_stemmed_codebase_resources(self.project1)
        codebase_resource1.refresh_from_db()
        codebase_resource2.refresh_from_db()
        codebase_resource3.refresh_from_db()

        expected_extra_data = {
            "stemmed_halo1": "000000240a64b6c8aae4625491a8aa77ffd9b2a6",
            "stemmed_snippets": [
                {"snippet": "8e5f6fead6d0469a9af967bd3b3c823c", "position": 0},
                {"snippet": "3b4fb17158ed94e2babd49970af94d06", "position": 2},
                {"snippet": "b0607c96667235727aa1e4212e907f7b", "position": 3},
                {"snippet": "65aecd343e17c78db5cfca34a8a4fa02", "position": 4},
                {"snippet": "89a7bf1c4ead7854f274e6f41b7654da", "position": 5},
                {"snippet": "8c38b55be87ffec2c0b91d6085f12e69", "position": 6},
                {"snippet": "5e0ddfbe6eeaa0bbe00f0a3bcb4183a8", "position": 7},
                {"snippet": "f8a7cabd43fb2d8a40a23d83217e3d8b", "position": 8},
                {"snippet": "fdc4910fe720d6b9f20196d306e7aedc", "position": 9},
                {"snippet": "7a5ee56ca82edc1c76e0b0b9322129dd", "position": 10},
                {"snippet": "6b93bb4ea1623dd6946a21f99418a3fa", "position": 11},
                {"snippet": "8f2a211b1a10cbd28fb8f1ad21dbf5fb", "position": 12},
                {"snippet": "c3c82df4de85b1c9dbf69b2b5a45935c", "position": 13},
                {"snippet": "216e662345dd2969bff90aefdae76672", "position": 14},
                {"snippet": "24d9e003c332e26e2cae1263d18e0ef6", "position": 15},
                {"snippet": "7210020de6bfe60b69ca8ec908845a15", "position": 17},
                {"snippet": "667f800b10c105c2418effd6035e6763", "position": 18},
                {"snippet": "c18caedb3daf59b210278b2b6d1d0db5", "position": 19},
                {"snippet": "a19fe989f63161a76526933a34593741", "position": 20},
                {"snippet": "f782389ac40b56bc81a7c92f40d87a83", "position": 21},
                {"snippet": "4ed61cd372dcc7d88c95d899271fd138", "position": 22},
                {"snippet": "e9c74c50192eb95bc4595254fc253427", "position": 23},
                {"snippet": "5a908af743b549f1f0ef8ab02c9053eb", "position": 24},
            ],
        }
        self.assertEqual(expected_extra_data, codebase_resource3.extra_data)
        self.assertFalse(codebase_resource1.extra_data)
        self.assertFalse(codebase_resource2.extra_data)

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

import unittest

from scanpipe.pipes.reachability_tools import ReachabilityPipeline
from scanpipe.pipes.reachability_tools import ReachabilityTool


class AwesomeReachabilityTool(ReachabilityTool):
    tool_name = "awesome_reachability"
    executable = "/awesome_reachability/tool"
    supported_languages = ("Python",)

    @classmethod
    def get_availability(cls):
        if not cls.executable:
            return "The awesome_reachability tool is not configured."

    @classmethod
    def run(cls, project, logger=None):
        return "awesome-output.json"

    @classmethod
    def parsed_output(cls, export_output_path, logger=None):
        return [{"symbol": "symbol_details"}]


class AwesomeReachability(ReachabilityPipeline):
    reachability_tool = AwesomeReachabilityTool

    def collect_resource_index(self):
        self.resource_indexes = {}

    def collect_and_match_resources(self):
        return {}


class ReachabilityToolsTest(unittest.TestCase):
    def test_tool_run(self):
        self.assertEqual(
            "awesome-output.json", AwesomeReachabilityTool.run(project=None)
        )

    def test_tool_parsed_output(self):
        self.assertEqual(
            [{"symbol": "symbol_details"}],
            AwesomeReachabilityTool.parsed_output(export_output_path="output.json"),
        )

    def test_tool_get_availability(self):
        self.assertIsNone(AwesomeReachabilityTool.get_availability())

        class UnavailableTool(AwesomeReachabilityTool):
            executable = None

        self.assertEqual(
            "The awesome_reachability tool is not configured.",
            UnavailableTool.get_availability(),
        )

    def test_pipeline_get_availability(self):
        self.assertIsNone(AwesomeReachability.get_availability())

        class NoToolPipeline(ReachabilityPipeline):
            pass

        self.assertIsNone(NoToolPipeline.get_availability())

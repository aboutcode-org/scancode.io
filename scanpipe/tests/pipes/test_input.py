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
from pathlib import Path

from django.test import TestCase

from scanpipe.pipes import input


class ScanPipeInputPipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_input_get_tool_name_from_scan_headers(self):
        tool_name = input.get_tool_name_from_scan_headers(scan_data={})
        self.assertIsNone(tool_name)

        tool_name = input.get_tool_name_from_scan_headers(scan_data={"headers": []})
        self.assertIsNone(tool_name)

        input_location = self.data_location / "asgiref-3.3.0_scanpipe_output.json"
        tool_name = input.get_tool_name_from_scan_headers(
            scan_data=json.loads(input_location.read_text())
        )
        self.assertEqual("scanpipe", tool_name)

        input_location = self.data_location / "asgiref-3.3.0_toolkit_scan.json"
        tool_name = input.get_tool_name_from_scan_headers(
            scan_data=json.loads(input_location.read_text())
        )
        self.assertEqual("scancode-toolkit", tool_name)

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

from django.test import TestCase

from scanpipe.pipes import pathmap


class ScanPipePathmapPipesTest(TestCase):
    def test_scanpipe_pipes_pathmap_get_matched_paths(self):
        paths_database = {
            "RouterStub.java": 1,
            "samples/screenshot.png": 2,
            "samples/JGroups/src/RouterStub.java": 3,
            "src/screenshot.png": 4,
        }

        index, id_by_segment = pathmap.build_index(paths_database)

        lookup_path = "src/RouterStub.java"
        matches = pathmap.get_matched_paths(lookup_path, index, id_by_segment)
        expected_length = 2
        expected_path_id = 3
        self.assertEqual([(expected_length, [expected_path_id])], list(matches))

        lookup_path = "samples/JGroups/src/File.ext"
        matches = pathmap.get_matched_paths(lookup_path, index, id_by_segment)
        self.assertEqual([], list(matches))

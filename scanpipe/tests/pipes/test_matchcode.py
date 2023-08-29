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

from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import matchcode


class MatchCodePipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

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

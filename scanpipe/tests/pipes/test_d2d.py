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

import tempfile

from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import d2d


class ScanPipeD2DPipesTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_d2d_get_inputs(self):
        with self.assertRaises(FileNotFoundError) as error:
            d2d.get_inputs(self.project1)
        self.assertEqual("from* archive not found.", str(error.exception))

        _, input_location = tempfile.mkstemp(prefix="from-")
        self.project1.copy_input_from(input_location)

        with self.assertRaises(FileNotFoundError) as error:
            d2d.get_inputs(self.project1)
        self.assertEqual("to* archive not found.", str(error.exception))

        _, input_location = tempfile.mkstemp(prefix="to-")
        self.project1.copy_input_from(input_location)

        self.assertEqual(2, len(d2d.get_inputs(self.project1)))

    def test_scanpipe_d2d_get_extracted_subpath(self):
        path = "not/an/extracted/path/"
        self.assertEqual(path, d2d.get_extracted_subpath(path))

        path = "a.jar-extract/subpath/file.ext"
        self.assertEqual("subpath/file.ext", d2d.get_extracted_subpath(path))

        path = "a.jar-extract/subpath/b.jar-extract/subpath/file.ext"
        self.assertEqual("subpath/file.ext", d2d.get_extracted_subpath(path))

    def test_scanpipe_d2d_get_best_checksum_matches_same_name(self):
        to_1 = CodebaseResource(name="package-1.0.ext", path="to/package-1.0.ext")
        to_2 = CodebaseResource(name="package-2.0.ext", path="to/package-2.0.ext")
        from_1 = CodebaseResource(name="package-1.0.ext", path="from/package-1.0.ext")
        from_2 = CodebaseResource(name="package-2.0.ext", path="from/package-2.0.ext")
        matches = [from_1, from_2]
        self.assertEqual([from_1], d2d.get_best_checksum_matches(to_1, matches))
        self.assertEqual([from_2], d2d.get_best_checksum_matches(to_2, matches))

    def test_scanpipe_d2d_get_best_checksum_matches_extracted_subpath(self):
        to_1 = CodebaseResource(path="to/jar-extract/a/package-1.0.ext")
        to_2 = CodebaseResource(path="to/jar-extract/a/package-2.0.ext")
        from_1 = CodebaseResource(path="from/src/a/package-1.0.ext")
        from_2 = CodebaseResource(path="from/src/a/package-2.0.ext")
        matches = [from_1, from_2]
        self.assertEqual([from_1], d2d.get_best_checksum_matches(to_1, matches))
        self.assertEqual([from_2], d2d.get_best_checksum_matches(to_2, matches))

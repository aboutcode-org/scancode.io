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

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import flag


class ScanPipeFlagPipesTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.resource1 = CodebaseResource.objects.create(
            project=self.project1,
            type=CodebaseResource.Type.DIRECTORY,
            path="dir/",
        )
        self.resource2 = CodebaseResource.objects.create(
            project=self.project1,
            type=CodebaseResource.Type.FILE,
            path="dir/filename.ext",
            name="filename.ext",
            extension=".ext",
        )

    def test_scanpipe_pipes_flag_flag_empty_codebase_resources(self):
        flag.flag_empty_codebase_resources(self.project1)
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.assertEqual("", self.resource1.status)
        self.assertEqual("ignored-empty-file", self.resource2.status)

    def test_scanpipe_pipes_flag_flag_ignored_directories(self):
        flag.flag_ignored_directories(self.project1)
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.assertEqual("ignored-directory", self.resource1.status)
        self.assertEqual("", self.resource2.status)

    def test_scanpipe_pipes_flag_flag_ignored_filenames(self):
        flag.flag_ignored_filenames(self.project1, filenames=[self.resource2.name])
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.assertEqual("", self.resource1.status)
        self.assertEqual("ignored-filename", self.resource2.status)

    def test_scanpipe_pipes_flag_flag_ignored_extensions(self):
        flag.flag_ignored_extensions(
            self.project1, extensions=[self.resource2.extension]
        )
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.assertEqual("", self.resource1.status)
        self.assertEqual("ignored-extension", self.resource2.status)

    def test_scanpipe_pipes_flag_flag_ignored_paths(self):
        flag.flag_ignored_paths(self.project1, paths=["dir/"])
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.assertEqual("ignored-path", self.resource1.status)
        self.assertEqual("ignored-path", self.resource2.status)

    def test_scanpipe_pipes_flag_tag_not_analyzed_codebase_resources(self):
        resource1 = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )
        resource2 = CodebaseResource.objects.create(
            project=self.project1,
            path="filename1.ext",
            status=flag.SCANNED,
        )
        flag.tag_not_analyzed_codebase_resources(self.project1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("not-analyzed", resource1.status)
        self.assertEqual("scanned", resource2.status)

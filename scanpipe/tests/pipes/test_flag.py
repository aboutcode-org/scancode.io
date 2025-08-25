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

from scanpipe import pipes
from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import flag
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_file


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
        self.resource3 = CodebaseResource.objects.create(
            project=self.project1,
            type=CodebaseResource.Type.DIRECTORY,
            path="dir/subpath/file.zip",
        )

    def test_scanpipe_pipes_flag_flag_empty_files(self):
        updated = flag.flag_empty_files(self.project1)
        self.assertEqual(1, updated)
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.assertEqual("", self.resource1.status)
        self.assertEqual("ignored-empty-file", self.resource2.status)

    def test_scanpipe_pipes_flag_flag_ignored_directories(self):
        updated = flag.flag_ignored_directories(self.project1)
        self.assertEqual(2, updated)
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.resource3.refresh_from_db()
        self.assertEqual("ignored-directory", self.resource1.status)
        self.assertEqual("", self.resource2.status)
        self.assertEqual("ignored-directory", self.resource3.status)

    def test_scanpipe_pipes_flag_flag_ignored_patterns(self):
        patterns = ["*.ext", "dir/*"]
        updated = flag.flag_ignored_patterns(
            self.project1.codebaseresources.no_status(), patterns
        )

        self.assertEqual(3, updated)
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.resource3.refresh_from_db()
        self.assertEqual("ignored-pattern", self.resource1.status)
        self.assertEqual("ignored-pattern", self.resource2.status)
        self.assertEqual("ignored-pattern", self.resource3.status)

        make_resource_file(self.project1, "policies.yml")
        make_resource_file(self.project1, "path/policies.yml")
        make_resource_file(self.project1, "path/deeper/policies.yml")
        make_resource_file(self.project1, "path/other-policies.yml")
        updated = flag.flag_ignored_patterns(
            self.project1.codebaseresources.no_status(),
            flag.DEFAULT_IGNORED_PATTERNS,
        )
        self.assertEqual(3, updated)

        project2 = make_project()
        make_resource_file(project2, "a.cdx.json.zip-extract")
        r1 = make_resource_file(project2, "a.cdx.json.zip-extract/__MACOSX")
        r2 = make_resource_file(
            project2, "a.cdx.json.zip-extract/__MACOSX/._a.cdx.json"
        )
        make_resource_file(project2, "a.cdx.json.zip-extract/a.cdx.json")
        updated = flag.flag_ignored_patterns(
            project2.codebaseresources.no_status(), flag.DEFAULT_IGNORED_PATTERNS
        )
        self.assertEqual(2, updated)
        ignored_qs = project2.codebaseresources.status(flag.IGNORED_PATTERN)
        self.assertEqual(2, ignored_qs.count())
        self.assertIn(r1, ignored_qs)
        self.assertIn(r2, ignored_qs)

    def test_scanpipe_pipes_flag_flag_not_analyzed_codebase_resources(self):
        resource1 = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )
        resource2 = CodebaseResource.objects.create(
            project=self.project1,
            path="filename1.ext",
            status=flag.SCANNED,
        )
        updated = flag.flag_not_analyzed_codebase_resources(self.project1)
        self.assertEqual(4, updated)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("not-analyzed", resource1.status)
        self.assertEqual("scanned", resource2.status)

    def test_scanpipe_pipes_flag_flag_mapped_resources(self):
        pipes.make_relation(
            from_resource=self.resource1,
            to_resource=self.resource2,
            map_type="type",
        )
        updated = flag.flag_mapped_resources(self.project1)
        self.assertEqual(2, updated)
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.assertEqual("mapped", self.resource1.status)
        self.assertEqual("mapped", self.resource2.status)

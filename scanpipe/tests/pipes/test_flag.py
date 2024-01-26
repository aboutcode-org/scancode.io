#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.test import TestCase

from scanpipe import pipes
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
        updated = flag.flag_ignored_patterns(self.project1, patterns)

        self.assertEqual(3, updated)
        self.resource1.refresh_from_db()
        self.resource2.refresh_from_db()
        self.resource3.refresh_from_db()
        self.assertEqual("ignored-pattern", self.resource1.status)
        self.assertEqual("ignored-pattern", self.resource2.status)
        self.assertEqual("ignored-pattern", self.resource3.status)

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

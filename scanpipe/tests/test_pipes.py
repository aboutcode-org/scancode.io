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
from unittest import mock

from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import filename_now
from scanpipe.pipes import outputs
from scanpipe.pipes import strip_root
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1


class ScanPipePipesTest(TestCase):
    def test_scanpipe_pipes_strip_root(self):
        input_paths = [
            "/root/dir/file",
            "/root/dir/file/",
            "//root/dir/file",
            "//root/dir/file/",
            "root/dir/file",
            "root/dir/file/",
        ]
        expected = "dir/file"

        for path in input_paths:
            self.assertEqual(expected, strip_root(path))
            self.assertEqual(expected, strip_root(Path(path)))

    def test_scanpipe_pipes_outputs_queryset_to_csv(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        DiscoveredPackage.create_for_resource(
            package_data1,
            codebase_resource,
        )

        queryset = project1.discoveredpackages.all()
        fieldnames = ["purl", "name", "version"]
        output_file = outputs.queryset_to_csv(project1, queryset, fieldnames)

        expected = [
            "purl,name,version\n",
            "pkg:deb/debian/adduser@3.118?arch=all,adduser,3.118\n",
        ]
        with output_file.open() as f:
            self.assertEqual(expected, f.readlines())

        queryset = project1.codebaseresources.all()
        fieldnames = ["for_packages", "path"]
        output_file = outputs.queryset_to_csv(project1, queryset, fieldnames)

        expected = [
            "for_packages,path\n",
            "['pkg:deb/debian/adduser@3.118?arch=all'],filename.ext\n",
        ]
        with output_file.open() as f:
            self.assertEqual(expected, f.readlines())

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_pipes_outputs_to_csv(self):
        project1 = Project.objects.create(name="Analysis")
        outputs.to_csv(project=project1)
        expected = [
            "codebaseresource-2010-10-10-10-10-10.csv",
            "discoveredpackage-2010-10-10-10-10-10.csv",
        ]
        self.assertEqual(sorted(expected), sorted(project1.output_root))

    def test_scanpipe_pipes_outputs_to_json(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        DiscoveredPackage.create_for_resource(
            package_data1,
            codebase_resource,
        )

        output_file = outputs.to_json(project=project1)
        self.assertEqual([output_file.name], project1.output_root)

        with output_file.open() as f:
            results = json.loads(f.read())

        expected = ["files", "headers", "packages"]
        self.assertEqual(expected, sorted(results.keys()))

        self.assertEqual(1, len(results["headers"]))
        self.assertEqual(1, len(results["files"]))
        self.assertEqual(1, len(results["packages"]))

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_pipes_filename_now(self):
        self.assertEqual("2010-10-10-10-10-10", filename_now())

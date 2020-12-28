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

import collections
import json
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import codebase
from scanpipe.pipes import filename_now
from scanpipe.pipes import outputs
from scanpipe.pipes import scancode
from scanpipe.pipes import strip_root
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1


class ScanPipePipesTest(TestCase):
    data_location = Path(__file__).parent / "data"

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

    def test_scanpipe_pipes_outputs_queryset_to_csv_file(self):
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

        output_file_path = project1.get_output_file_path("packages", "csv")
        with output_file_path.open("w") as output_file:
            outputs.queryset_to_csv_file(queryset, fieldnames, output_file)

        expected = [
            "purl,name,version\n",
            "pkg:deb/debian/adduser@3.118?arch=all,adduser,3.118\n",
        ]
        with output_file_path.open() as f:
            self.assertEqual(expected, f.readlines())

        queryset = project1.codebaseresources.all()
        fieldnames = ["for_packages", "path"]
        output_file_path = project1.get_output_file_path("resources", "csv")
        with output_file_path.open("w") as output_file:
            outputs.queryset_to_csv_file(queryset, fieldnames, output_file)

        expected = [
            "for_packages,path\n",
            "['pkg:deb/debian/adduser@3.118?arch=all'],filename.ext\n",
        ]
        with output_file_path.open() as f:
            self.assertEqual(expected, f.readlines())

    def test_scanpipe_pipes_outputs_queryset_to_csv_stream(self):
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

        output_file = project1.get_output_file_path("packages", "csv")
        with output_file.open("w") as output_stream:
            generator = outputs.queryset_to_csv_stream(
                queryset, fieldnames, output_stream
            )
            collections.deque(generator, maxlen=0)  # Exhaust the generator

        expected = [
            "purl,name,version\n",
            "pkg:deb/debian/adduser@3.118?arch=all,adduser,3.118\n",
        ]
        with output_file.open() as f:
            self.assertEqual(expected, f.readlines())

        queryset = project1.codebaseresources.all()
        fieldnames = ["for_packages", "path"]
        output_file = project1.get_output_file_path("resources", "csv")
        with output_file.open("w") as output_stream:
            generator = outputs.queryset_to_csv_stream(
                queryset, fieldnames, output_stream
            )
            collections.deque(generator, maxlen=0)  # Exhaust the generator

        outputs.queryset_to_csv_stream(queryset, fieldnames, output_file)

        expected = [
            "for_packages,path\n",
            "['pkg:deb/debian/adduser@3.118?arch=all'],filename.ext\n",
        ]
        with output_file.open() as f:
            self.assertEqual(expected, f.readlines())

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_pipes_outputs_to_csv(self):
        project1 = Project.objects.create(name="Analysis")
        output_files = outputs.to_csv(project=project1)
        expected = [
            "codebaseresource-2010-10-10-10-10-10.csv",
            "discoveredpackage-2010-10-10-10-10-10.csv",
        ]
        self.assertEqual(sorted(expected), sorted(project1.output_root))
        self.assertEqual(sorted(expected), sorted([f.name for f in output_files]))

    def test_scanpipe_pipes_outputs_to_json(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        DiscoveredPackage.create_for_resource(package_data1, codebase_resource)

        output_file = outputs.to_json(project=project1)
        self.assertEqual([output_file.name], project1.output_root)

        with output_file.open() as f:
            results = json.loads(f.read())

        expected = ["files", "headers", "packages"]
        self.assertEqual(expected, sorted(results.keys()))

        self.assertEqual(1, len(results["headers"]))
        self.assertEqual(1, len(results["files"]))
        self.assertEqual(1, len(results["packages"]))

    def test_scanpipe_pipes_outputs_to_xlsx(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        DiscoveredPackage.create_for_resource(package_data1, codebase_resource)

        output_file = outputs.to_xlsx(project=project1)
        self.assertEqual([output_file.name], project1.output_root)

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_pipes_filename_now(self):
        self.assertEqual("2010-10-10-10-10-10", filename_now())

    def test_scanpipe_pipes_scancode_virtual_codebase(self):
        project = Project.objects.create(name="asgiref")
        input_location = self.data_location / "asgiref-3.3.0_scan.json"
        virtual_codebase = scancode.get_virtual_codebase(project, input_location)
        self.assertEqual(19, len(virtual_codebase.resources.keys()))

        scancode.create_codebase_resources(project, virtual_codebase)
        scancode.create_discovered_packages(project, virtual_codebase)

        self.assertEqual(19, CodebaseResource.objects.count())
        self.assertEqual(1, DiscoveredPackage.objects.count())

        # The functions can be called again and existing objects are skipped
        scancode.create_codebase_resources(project, virtual_codebase)
        scancode.create_discovered_packages(project, virtual_codebase)
        self.assertEqual(19, CodebaseResource.objects.count())
        self.assertEqual(1, DiscoveredPackage.objects.count())

    def test_scanpipe_pipes_scancode_run_extractcode(self):
        project = Project.objects.create(name="name with space")
        exitcode, output = scancode.run_extractcode(str(project.codebase_path))
        self.assertEqual(0, exitcode)
        self.assertIn("Extracting done.", output)

    def test_scanpipe_pipes_scancode_run_scancode(self):
        project = Project.objects.create(name="name with space")
        exitcode, output = scancode.run_scancode(
            location=str(project.codebase_path),
            output_file=str(project.get_output_file_path("scancode", "json")),
            options=["--info"],
        )
        self.assertEqual(0, exitcode)
        self.assertIn("Scanning done.", output)

    def test_scanpipe_pipes_codebase_get_tree(self):
        fixtures = self.data_location / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        scan_results = self.data_location / "asgiref-3.3.0_scan.json"
        virtual_codebase = scancode.get_virtual_codebase(project, scan_results)
        project_codebase = codebase.ProjectCodebase(project)

        fields = ["name", "path"]
        virtual_tree = codebase.get_tree(
            virtual_codebase.root, fields, codebase=virtual_codebase
        )
        project_tree = codebase.get_tree(project_codebase.root, fields)

        with open(self.data_location / "asgiref-3.3.0_tree.json") as f:
            expected = json.loads(f.read())

        self.assertEqual(expected, project_tree)
        self.assertEqual(expected, virtual_tree)

    def test_scanpipe_pipes_codebase_project_codebase_class_no_resources(self):
        project = Project.objects.create(name="project")

        project_codebase = codebase.ProjectCodebase(project)
        with self.assertRaises(AttributeError):
            project_codebase.root

        self.assertEqual([], list(project_codebase.resources))
        self.assertEqual([], list(project_codebase.walk()))
        with self.assertRaises(AttributeError):
            project_codebase.get_tree()

    def test_scanpipe_pipes_codebase_project_codebase_class_with_resources(self):
        fixtures = self.data_location / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})

        project = Project.objects.get(name="asgiref")
        project_codebase = codebase.ProjectCodebase(project)

        expected_root = project.codebaseresources.get(path="codebase")
        self.assertTrue(isinstance(project_codebase.root, CodebaseResource))
        self.assertEqual(expected_root, project_codebase.root)

        self.assertEqual(19, len(project_codebase.resources))
        self.assertEqual(expected_root, project_codebase.resources[0])

        walk_gen = project_codebase.walk()
        self.assertEqual(expected_root, next(walk_gen))
        expected = "codebase/asgiref-3.3.0-py3-none-any.whl"
        self.assertEqual(expected, next(walk_gen).path)

        tree = project_codebase.get_tree()
        with open(self.data_location / "asgiref-3.3.0_tree.json") as f:
            expected = json.loads(f.read())

        self.assertEqual(expected, tree)

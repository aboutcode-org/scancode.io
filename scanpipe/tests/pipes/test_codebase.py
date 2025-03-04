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
import sys
from pathlib import Path
from unittest import skipIf

from django.core.management import call_command
from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import codebase
from scanpipe.pipes import scancode


class ScanPipeCodebasePipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_codebase_get_codebase_tree(self):
        def _replace_path(virtual_tree_children):
            """
            Given a list `virtual_tree_children` of mappings, remove instances
            of "virtual_root/" from the paths of mappings and their children,
            recursively.
            """
            for res in virtual_tree_children:
                path = res["path"]
                path = path.replace("virtual_root/", "")
                res["path"] = path
                _replace_path(res.get("children", []))

        fixtures = self.data / "asgiref" / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        scan_results = self.data / "asgiref" / "asgiref-3.3.0_scanpipe_output.json"
        virtual_codebase = scancode.get_virtual_codebase(project, scan_results)
        project_codebase = codebase.ProjectCodebase(project)

        fields = ["name", "path"]

        virtual_tree = codebase.get_codebase_tree(virtual_codebase, fields)
        project_tree = codebase.get_codebase_tree(project_codebase, fields)

        with open(self.data / "asgiref" / "asgiref-3.3.0_tree.json") as f:
            expected = json.loads(f.read())

        self.assertEqual(expected, project_tree)

        virtual_tree_children = virtual_tree["children"][0]["children"]
        _replace_path(virtual_tree_children)

        self.assertEqual(expected["children"], virtual_tree_children)

    def test_scanpipe_pipes_codebase_project_codebase_class_no_resources(self):
        project = Project.objects.create(name="project")
        project_codebase = codebase.ProjectCodebase(project)

        self.assertEqual([], list(project_codebase.root_resources))
        self.assertEqual([], list(project_codebase.resources))
        self.assertEqual([], list(project_codebase.walk()))
        self.assertEqual(dict(children=[]), project_codebase.get_tree())

    def test_scanpipe_pipes_codebase_project_codebase_class_with_resources(self):
        fixtures = self.data / "asgiref" / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})

        project = Project.objects.get(name="asgiref")
        project_codebase = codebase.ProjectCodebase(project)

        expected_root_resources = project.codebaseresources.exclude(path__contains="/")
        expected_root_resources = list(expected_root_resources)
        self.assertEqual(expected_root_resources, list(project_codebase.root_resources))

        self.assertEqual(18, len(project_codebase.resources))

        walk_gen = project_codebase.walk()
        self.assertEqual(next(iter(expected_root_resources)), next(walk_gen))
        expected = "asgiref-3.3.0-py3-none-any.whl-extract"
        self.assertEqual(expected, next(walk_gen).path)

        tree = project_codebase.get_tree()
        with open(self.data / "asgiref" / "asgiref-3.3.0_tree.json") as f:
            expected = json.loads(f.read())

        self.assertEqual(expected, tree)

    @skipIf(sys.platform != "linux", "Ordering differs on macOS.")
    def test_scanpipe_pipes_codebase_project_codebase_class_walk(self):
        fixtures = self.data / "asgiref" / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})

        project = Project.objects.get(name="asgiref")
        project_codebase = codebase.ProjectCodebase(project)

        topdown_paths = list(r.path for r in project_codebase.walk(topdown=True))
        expected_topdown_paths = [
            "asgiref-3.3.0-py3-none-any.whl",
            "asgiref-3.3.0-py3-none-any.whl-extract",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/current_thread_executor.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/local.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/server.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/wsgi.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/LICENSE",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/METADATA",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/RECORD",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/"
            "top_level.txt",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/WHEEL",
        ]
        self.assertEqual(expected_topdown_paths, topdown_paths)

        bottom_up_paths = list(r.path for r in project_codebase.walk(topdown=False))
        expected_bottom_up_paths = [
            "asgiref-3.3.0-py3-none-any.whl",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/current_thread_executor.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/local.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/server.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/wsgi.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/LICENSE",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/METADATA",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/RECORD",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/"
            "top_level.txt",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/WHEEL",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info",
            "asgiref-3.3.0-py3-none-any.whl-extract",
        ]
        self.assertEqual(expected_bottom_up_paths, bottom_up_paths)

    def test_scanpipe_pipes_codebase_get_basic_virtual_codebase(self):
        fixtures = self.data / "asgiref" / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")
        resources = project.codebaseresources.all()
        virtual_codebase = codebase.get_basic_virtual_codebase(resources)
        topdown_paths = list(r.path for r in virtual_codebase.walk(topdown=True))
        expected_topdown_paths = [
            "virtual_root",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/__init__.py",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/compatibility.py",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/current_thread_executor.py",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/local.py",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/server.py",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/sync.py",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/testing.py",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/timeout.py",
            "virtual_root/asgiref-3.3.0-py3-none-any.whl-extract/asgiref/wsgi.py",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/LICENSE",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/METADATA",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/RECORD",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/"
            "top_level.txt",
            "virtual_root/"
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/WHEEL",
        ]
        self.assertEqual(expected_topdown_paths, topdown_paths)

        # Check to see that the few fields are populated
        resource = virtual_codebase.get_resource(
            "virtual_root/asgiref-3.3.0-py3-none-any.whl"
        )
        self.assertEqual("c03f67211a311b13d1294ac8af7cb139ee34c4f9", resource.sha1)
        self.assertEqual(19948, resource.size)
        self.assertEqual(True, resource.is_file)

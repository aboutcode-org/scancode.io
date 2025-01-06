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

from django.core.management import call_command
from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import Project
from scanpipe.pipes import input
from scanpipe.pipes import output


class ScanPipeInputPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_input_get_tool_name_from_scan_headers(self):
        tool_name = input.get_tool_name_from_scan_headers(scan_data={})
        self.assertIsNone(tool_name)

        tool_name = input.get_tool_name_from_scan_headers(scan_data={"headers": []})
        self.assertIsNone(tool_name)

        input_location = self.data / "asgiref" / "asgiref-3.3.0_scanpipe_output.json"
        tool_name = input.get_tool_name_from_scan_headers(
            scan_data=json.loads(input_location.read_text())
        )
        self.assertEqual("scanpipe", tool_name)

        input_location = self.data / "asgiref" / "asgiref-3.3.0_toolkit_scan.json"
        tool_name = input.get_tool_name_from_scan_headers(
            scan_data=json.loads(input_location.read_text())
        )
        self.assertEqual("scancode-toolkit", tool_name)

    def test_scanpipe_pipes_input_is_archive(self):
        input_location = self.data / "aboutcode" / "notice.NOTICE"
        self.assertFalse(input.is_archive(input_location))

        input_location = self.data / "scancode" / "archive.zip"
        self.assertTrue(input.is_archive(input_location))

    def test_scanpipe_pipes_scancode_load_inventory_from_toolkit_scan(self):
        project = Project.objects.create(name="Analysis")
        input_location = self.data / "asgiref" / "asgiref-3.3.0_toolkit_scan.json"
        input.load_inventory_from_toolkit_scan(project, input_location)
        self.assertEqual(18, project.codebaseresources.count())
        self.assertEqual(2, project.discoveredpackages.count())
        self.assertEqual(4, project.discovereddependencies.count())

    def test_scanpipe_pipes_scancode_load_inventory_from_scanpipe(self):
        project = Project.objects.create(name="1")
        input_location = self.data / "asgiref" / "asgiref-3.3.0_scanpipe_output.json"
        scan_data = json.loads(input_location.read_text())
        input.load_inventory_from_scanpipe(project, scan_data)
        self.assertEqual(18, project.codebaseresources.count())
        self.assertEqual(2, project.discoveredpackages.count())
        self.assertEqual(4, project.discovereddependencies.count())

        # Load again to ensure there is no duplication
        input.load_inventory_from_scanpipe(project, scan_data)
        self.assertEqual(18, project.codebaseresources.count())
        self.assertEqual(2, project.discoveredpackages.count())
        self.assertEqual(4, project.discovereddependencies.count())

        # Using the JSON output of project1 to load into project2
        project2 = Project.objects.create(name="2")
        output_file = output.to_json(project=project)
        scan_data = json.loads(output_file.read_text())
        input.load_inventory_from_scanpipe(project2, scan_data)
        self.assertEqual(18, project2.codebaseresources.count())
        self.assertEqual(2, project2.discoveredpackages.count())
        self.assertEqual(4, project2.discovereddependencies.count())

    def test_scanpipe_pipes_scancode_load_inventory_from_scanpipe_with_relations(self):
        project = Project.objects.create(name="1")
        input_location = self.data / "d2d" / "flume-ng-node-d2d-input.json"
        scan_data = json.loads(input_location.read_text())
        input.load_inventory_from_scanpipe(project, scan_data)
        self.assertEqual(57, project.codebaseresources.count())
        self.assertEqual(1, project.discoveredpackages.count())
        self.assertEqual(0, project.discovereddependencies.count())
        self.assertEqual(18, project.codebaserelations.count())

        # Load again to ensure there is no duplication
        input.load_inventory_from_scanpipe(project, scan_data)
        self.assertEqual(57, project.codebaseresources.count())
        self.assertEqual(18, project.codebaserelations.count())

    def test_scanpipe_pipes_scancode_load_inventory_extra_data(self):
        project = Project.objects.create(name="1")
        input_location = self.data / "asgiref" / "asgiref-3.3.0_scanpipe_output.json"
        scan_data = json.loads(input_location.read_text())
        extra_data = {"key": "value"}
        scan_data["headers"][0]["extra_data"] = extra_data

        input.load_inventory_from_scanpipe(project, scan_data)
        project.refresh_from_db()
        self.assertEqual(extra_data, project.extra_data)

        project.extra_data = {}
        project.save()
        input.load_inventory_from_scanpipe(
            project, scan_data, extra_data_prefix="file.ext"
        )
        project.refresh_from_db()
        self.assertEqual({"file.ext": extra_data}, project.extra_data)

    def test_scanpipe_pipes_input_load_inventory_from_xlsx(self):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "outputs" / "asgiref-3.6.0-output.xlsx"
        input.load_inventory_from_xlsx(project1, input_location)
        self.assertEqual(20, project1.codebaseresources.count())
        self.assertEqual(2, project1.discoveredpackages.count())
        self.assertEqual(8, project1.discovereddependencies.count())
        self.assertEqual(0, project1.codebaserelations.count())

    def test_scanpipe_pipes_input_load_inventory_from_xlsx_layers_sheet(self):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "outputs" / "docker_ghcr.io_kyverno_sbom.xlsx"
        input.load_inventory_from_xlsx(project1, input_location)
        project1.refresh_from_db()
        expected_location = (
            self.data / "outputs" / "docker_ghcr.io_kyverno_sbom_expected.json"
        )
        expected = json.loads(expected_location.read_text())
        self.assertEqual(expected, project1.extra_data)

        project1.extra_data = {}
        project1.save()
        input.load_inventory_from_xlsx(
            project1, input_location, extra_data_prefix="file.ext"
        )
        project1.refresh_from_db()
        self.assertEqual({"file.ext": expected}, project1.extra_data)

    def test_scanpipe_pipes_input_load_inventory_from_project_xlsx_output(self):
        fixtures = self.data / "asgiref" / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project1 = Project.objects.get(name="asgiref")
        xlsx_output = output.to_xlsx(project1)
        self.assertEqual(18, project1.codebaseresources.count())
        self.assertEqual(2, project1.discoveredpackages.count())
        self.assertEqual(4, project1.discovereddependencies.count())
        self.assertEqual(0, project1.codebaserelations.count())

        project2 = Project.objects.create(name="project2")
        input.load_inventory_from_xlsx(project2, xlsx_output)
        self.assertEqual(18, project2.codebaseresources.count())
        self.assertEqual(2, project2.discoveredpackages.count())
        self.assertEqual(4, project2.discovereddependencies.count())
        self.assertEqual(0, project2.codebaserelations.count())

    def test_scanpipe_pipes_input_clean_xlsx_data_to_model_data_resource(self):
        xlsx_data = {"field_does_not_exist": "value", "path": None}
        results = input.clean_xlsx_data_to_model_data(CodebaseResource, xlsx_data)
        self.assertEqual({}, results)

        xlsx_data = {
            "path": "asgiref-3.6.0.dist-info/LICENSE",
            "name": "LICENSE",
            "tag": None,
            "size": "1552",
            "md5": "f09eb47206614a4954c51db8a94840fa",
            "copyrights": "Copyright 1\nCopyright 2",
            "holders": "Django Software Foundation",
            "for_packages": "pkg:pypi/package@1.0\npkg:pypi/package@2.0",
        }

        results = input.clean_xlsx_data_to_model_data(CodebaseResource, xlsx_data)
        expected = {
            "path": "asgiref-3.6.0.dist-info/LICENSE",
            "name": "LICENSE",
            "size": "1552",
            "md5": "f09eb47206614a4954c51db8a94840fa",
            "copyrights": [{"copyright": "Copyright 1"}, {"copyright": "Copyright 2"}],
            "holders": [{"holder": "Django Software Foundation"}],
            "for_packages": ["pkg:pypi/package@1.0", "pkg:pypi/package@2.0"],
        }
        self.assertEqual(expected, results)

    def test_scanpipe_pipes_input_clean_xlsx_data_to_model_data_dependency(self):
        xlsx_data = {"field_does_not_exist": "value", "path": None}
        results = input.clean_xlsx_data_to_model_data(DiscoveredDependency, xlsx_data)
        self.assertEqual({}, results)

        xlsx_data = {
            "purl": "pkg:pypi/typing-extensions",
            "extracted_requirement": 'typing-extensions; python_version < "3.8"',
            "scope": "install",
            "is_runtime": "True",
            "is_optional": None,
            "is_pinned": None,
            "dependency_uid": "pkg:pypi/typing-extensions?uuid=57a6f83a-1763",
            "for_package_uid": "pkg:pypi/asgiref@3.6.0?uuid=0aa676d0-240c-4838",
            "datafile_path": "asgiref-3.6.0.dist-info/METADATA",
            "datasource_id": "pypi_wheel_metadata",
            "package_type": "pypi",
            "xlsx_errors": None,
        }

        results = input.clean_xlsx_data_to_model_data(DiscoveredDependency, xlsx_data)
        expected = {
            "purl": "pkg:pypi/typing-extensions",
            "extracted_requirement": 'typing-extensions; python_version < "3.8"',
            "scope": "install",
            "is_runtime": "True",
            "dependency_uid": "pkg:pypi/typing-extensions?uuid=57a6f83a-1763",
            "for_package_uid": "pkg:pypi/asgiref@3.6.0?uuid=0aa676d0-240c-4838",
            "datafile_path": "asgiref-3.6.0.dist-info/METADATA",
            "datasource_id": "pypi_wheel_metadata",
        }
        self.assertEqual(expected, results)

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
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

import xlsxwriter
from lxml import etree

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.pipes import output
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1


class ScanPipeOutputPipesTest(TestCase):
    data_path = Path(__file__).parent / "data"

    def assertResultsEqual(self, expected_file, results, regen=False):
        """
        Set `regen` to True to regenerate the expected results.
        """
        if regen:
            expected_file.write_text(results)

        expected_data = expected_file.read_text()
        self.assertEqual(expected_data, results)

    def test_scanpipe_pipes_outputs_queryset_to_csv_file(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        codebase_resource.create_and_add_package(package_data1)

        queryset = project1.discoveredpackages.all()
        fieldnames = ["purl", "name", "version"]

        output_file_path = project1.get_output_file_path("packages", "csv")
        with output_file_path.open("w") as output_file:
            output.queryset_to_csv_file(queryset, fieldnames, output_file)

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
            output.queryset_to_csv_file(queryset, fieldnames, output_file)

        package_uid = "pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b"
        expected = [
            "for_packages,path\n",
            f"['{package_uid}'],filename.ext\n",
        ]
        with output_file_path.open() as f:
            self.assertEqual(expected, f.readlines())

    def test_scanpipe_pipes_outputs_queryset_to_csv_stream(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        codebase_resource.create_and_add_package(package_data1)

        queryset = project1.discoveredpackages.all()
        fieldnames = ["purl", "name", "version"]

        output_file = project1.get_output_file_path("packages", "csv")
        with output_file.open("w") as output_stream:
            generator = output.queryset_to_csv_stream(
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
            generator = output.queryset_to_csv_stream(
                queryset, fieldnames, output_stream
            )
            collections.deque(generator, maxlen=0)  # Exhaust the generator

        output.queryset_to_csv_stream(queryset, fieldnames, output_file)
        package_uid = "pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b"
        expected = [
            "for_packages,path\n",
            f"['{package_uid}'],filename.ext\n",
        ]
        with output_file.open() as f:
            self.assertEqual(expected, f.readlines())

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_pipes_outputs_to_csv(self):
        fixtures = self.data_path / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        with self.assertNumQueries(7):
            output_files = output.to_csv(project=project)

        csv_files = [
            "codebaseresource-2010-10-10-10-10-10.csv",
            "discovereddependency-2010-10-10-10-10-10.csv",
            "discoveredpackage-2010-10-10-10-10-10.csv",
            "projecterror-2010-10-10-10-10-10.csv",
        ]

        for csv_file in csv_files:
            self.assertIn(csv_file, project.output_root)
            self.assertIn(csv_file, [f.name for f in output_files])

    def test_scanpipe_pipes_outputs_to_json(self):
        fixtures = self.data_path / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        output_file = output.to_json(project=project)
        self.assertIn(output_file.name, project.output_root)

        with output_file.open() as f:
            results = json.loads(f.read())

        expected = ["dependencies", "files", "headers", "packages"]
        self.assertEqual(expected, sorted(results.keys()))

        self.assertEqual(1, len(results["headers"]))
        self.assertEqual(18, len(results["files"]))
        self.assertEqual(2, len(results["packages"]))
        self.assertEqual(4, len(results["dependencies"]))

        self.assertIn("compliance_alert", results["files"][0])

        # Make sure the output can be generated even if the work_directory was wiped
        shutil.rmtree(project.work_directory)
        with self.assertNumQueries(7):
            output_file = output.to_json(project=project)
        self.assertIn(output_file.name, project.output_root)

    def test_scanpipe_pipes_outputs_to_xlsx(self):
        fixtures = self.data_path / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})

        project = Project.objects.get(name="asgiref")
        ProjectError.objects.create(
            project=project, model="Model", details={}, message="Error"
        )

        output_file = output.to_xlsx(project=project)
        self.assertIn(output_file.name, project.output_root)

        # Make sure the output can be generated even if the work_directory was wiped
        shutil.rmtree(project.work_directory)
        with self.assertNumQueries(7):
            output_file = output.to_xlsx(project=project)
        self.assertIn(output_file.name, project.output_root)

    def test_scanpipe_pipes_outputs_to_cyclonedx(self, regen=False):
        fixtures = self.data_path / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})

        project = Project.objects.get(name="asgiref")

        with mock.patch("cyclonedx.model.bom.uuid4") as mock_uuid4:
            with mock.patch("cyclonedx.model.bom.datetime") as mock_datetime:
                mock_uuid4.return_value = "b74fe5df-e965-415e-ba65-f38421a0695d"
                mock_datetime.now = lambda tz: ""
                output_file = output.to_cyclonedx(project=project)

        self.assertIn(output_file.name, project.output_root)

        # Patch the tool version
        results_json = json.loads(output_file.read_text())
        results_json["metadata"]["tools"][0]["version"] = "31.0.0"
        results = json.dumps(results_json, indent=2)

        expected_location = self.data_path / "cyclonedx/asgiref-3.3.0.bom.json"
        if regen:
            expected_location.write_text(results)

        self.assertJSONEqual(results, expected_location.read_text())

    def test_scanpipe_pipes_outputs_to_spdx(self):
        fixtures = self.data_path / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        output_file = output.to_spdx(project=project)
        self.assertIn(output_file.name, project.output_root)

        # Patch the `created` date and tool version
        results_json = json.loads(output_file.read_text())
        results_json["creationInfo"]["created"] = "2000-01-01T01:02:03Z"
        results_json["creationInfo"]["creators"] = ["Tool: ScanCode.io-31.0.0"]
        # Files ordering is system dependent, excluded for now
        results_json["files"] = []
        results = json.dumps(results_json, indent=2)

        expected_file = self.data_path / "asgiref-3.3.0.spdx.json"
        self.assertResultsEqual(expected_file, results, regen=False)

        # Make sure the output can be generated even if the work_directory was wiped
        shutil.rmtree(project.work_directory)
        with self.assertNumQueries(8):
            output_file = output.to_spdx(project=project)
        self.assertIn(output_file.name, project.output_root)


class ScanPipeXLSXOutputPipesTest(TestCase):
    def test__add_xlsx_worksheet_does_truncates_long_strings_over_max_len(self):
        # This test verifies that we do not truncate long text silently

        test_dir = Path(tempfile.mkdtemp(prefix="scancode-io-test"))

        # The max length that Excel supports is 32,767 char per cell.
        # and 253 linefeed. This does not seem to be an absolute science
        # though.
        len_32760_string = "f" * 32760
        len_10_string = "0123456789"

        values = get_cell_texts(
            original_text=len_32760_string + len_10_string,
            test_dir=test_dir,
            workbook_name="long-text",
        )

        expected = [
            None,
            None,
            "foo",
            None,
            "xlsx_errors",
            None,
            "fffffffffffffffffffffffffffffffffffffffffff0123456",
            None,
            "32767 length to fit in an XLSL cell maximum length",
        ]

        for r, x in zip(values, expected):
            if r != x:
                self.assertEqual(r[-50:], x)

    def test__add_xlsx_worksheet_does_not_munge_long_strings_of_over_1024_lines(self):
        # This test verifies that we do not truncate long text silently

        test_dir = Path(tempfile.mkdtemp(prefix="scancode-io-test"))

        len_1025_lines = "\r\n".join(str(i) for i in range(1025)) + "abcd"

        values = get_cell_texts(
            original_text=len_1025_lines,
            test_dir=test_dir,
            workbook_name="long-text",
        )
        expected = [
            None,
            None,
            "foo",
            None,
            "xlsx_errors",
            None,
            "5\n1016\n1017\n1018\n1019\n1020\n1021\n1022\n1023\n1024abcd",
            None,
            "The value of: foo has been truncated from: 65476 to 32767 length "
            "to fit in an XLSL cell maximum length",
        ]

        for r, x in zip(values, expected):
            if r != x:
                self.assertEqual(r[-50:], x)

    def test__adapt_value_for_xlsx_does_adapt(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="foo",
            value="some simple value",
        )
        self.assertEqual(result, "some simple value")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_to_string(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="foo",
            value=12.4,
        )
        self.assertEqual(result, "12.4")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_crlf_to_lf(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="foo",
            value="some \r\nsimple \r\nvalue\r\n",
        )
        self.assertEqual(result, "some \nsimple \nvalue\n")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_license_expressions(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="license_expressions", value=["mit", "mit", "gpl-2.0"]
        )
        self.assertEqual(result, "mit AND gpl-2.0")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_description_and_keeps_only_5_lines(self):
        twenty_lines = "\r\n".join(str(i) for i in range(20))

        result, error = output._adapt_value_for_xlsx(
            fieldname="description", value=twenty_lines
        )
        self.assertEqual(result, "0\n1\n2\n3\n4")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_copyrights(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="copyrights",
            value=[{"copyright": "bar"}, {"copyright": "foo"}, {"copyright": "bar"}],
        )
        self.assertEqual(result, "bar\nfoo")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_authors(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="authors",
            value=[{"author": "bar"}, {"author": "foo"}, {"author": "bar"}],
        )
        self.assertEqual(result, "bar\nfoo")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_holders(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="holders",
            value=[{"holder": "bar"}, {"holder": "foo"}, {"holder": "bar"}],
        )
        self.assertEqual(result, "bar\nfoo")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_emails(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="emails", value=[{"email": "foo@bar.com"}]
        )
        self.assertEqual(result, "foo@bar.com")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_urls(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="urls", value=[{"url": "http://bar.com"}]
        )
        self.assertEqual(result, "http://bar.com")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_dicts(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="somename", value={"value1": "bar", "value2": "foo"}
        )
        self.assertEqual(result, "value1: bar\nvalue2: foo\n")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_lists(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="somename", value=["value1", "bar", "value2", "foo"]
        )
        self.assertEqual(result, "value1\nbar\nvalue2\nfoo")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_tuples_and_removes_dueps(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="somename", value=["value1", "bar", "value1", "foo"]
        )
        self.assertEqual(result, "value1\nbar\nfoo")
        self.assertEqual(error, None)


def get_cell_texts(original_text, test_dir, workbook_name):
    """
    Create a workbook with a worksheet with a cell with ``original_text``
    and then extract, read and return the actual texts as a list.
    """

    class Row:
        """
        A mock Row with a single attribute storing a long string
        """

        def __init__(self, foo):
            self.foo = foo

    rows = [Row(original_text)]

    output_file = test_dir / workbook_name
    with xlsxwriter.Workbook(str(output_file)) as workbook:
        output._add_xlsx_worksheet(
            workbook=workbook,
            worksheet_name="packages",
            rows=rows,
            fields=["foo"],
        )

    extract_dir = test_dir / "extracted"
    shutil.unpack_archive(
        filename=output_file,
        extract_dir=extract_dir,
        format="zip",
    )

    # This XML doc contains the strings stored in cells and has this shape:
    # <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    # <sst     xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    #      count="2" uniqueCount="2">
    #   <si><t>foo</t></si>
    #   <si><t>f0123456789</t></si>
    # </sst>

    shared_strings = extract_dir / "xl" / "sharedStrings.xml"
    sstet = etree.parse(str(shared_strings))
    # in our special case the text we care is the last element of the XML

    return [t.text for t in sstet.getroot().iter()]

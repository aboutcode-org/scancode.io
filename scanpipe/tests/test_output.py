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

import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

import xlsxwriter
from lxml import etree

from scanpipe.pipes import output


class ScanPipeOutputTest(TestCase):
    data_location = Path(__file__).parent / "data"

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
            value=[{"value": "bar"}, {"value": "foo"}, {"value": "bar"}],
        )
        self.assertEqual(result, "bar\nfoo")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_authors(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="authors",
            value=[{"value": "bar"}, {"value": "foo"}, {"value": "bar"}],
        )
        self.assertEqual(result, "bar\nfoo")
        self.assertEqual(error, None)

    def test__adapt_value_for_xlsx_does_adapt_holders(self):
        result, error = output._adapt_value_for_xlsx(
            fieldname="holders",
            value=[{"value": "bar"}, {"value": "foo"}, {"value": "bar"}],
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

    print("shared_strings:", shared_strings)
    return [t.text for t in sstet.getroot().iter()]

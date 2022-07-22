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

import csv
import json

from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder

import saneyaml
import xlsxwriter
from license_expression import ordered_unique
from packagedcode.utils import combine_expressions

from scancodeio import SCAN_NOTICE
from scancodeio import __version__ as scancodeio_version

scanpipe_app = apps.get_app_config("scanpipe")


def queryset_to_csv_file(queryset, fieldnames, output_file):
    """
    Outputs csv content generated from the provided `queryset` objects to the
    `output_file`.
    The fields to be included as columns and their order are controlled by the
    `fieldnames` list.
    """
    writer = csv.DictWriter(output_file, fieldnames)
    writer.writeheader()

    for record in queryset.iterator():
        row = {field: getattr(record, field) for field in fieldnames}
        writer.writerow(row)


def queryset_to_csv_stream(queryset, fieldnames, output_stream):
    """
    Outputs csv content generated from the provided `queryset` objects to the
    `output_stream`.
    The fields to be included as columns and their order are controlled by the
    `fieldnames` list.
    """
    writer = csv.DictWriter(output_stream, fieldnames)
    # Not using writer.writeheader() since this method do not "return" the
    # value while writer.writerow() does.
    header = dict(zip(fieldnames, fieldnames))
    yield writer.writerow(header)

    for record in queryset.iterator():
        row = {field: getattr(record, field) for field in fieldnames}
        yield writer.writerow(row)


def to_csv(project):
    """
    Generates output for the provided `project` in csv format.
    Since the csv format does not support multiple tabs, one file is created
    per object type.
    The output files are created in the `project` output/ directory.
    Returns a list of paths of the generated output files.
    """
    from scanpipe.api.serializers import get_serializer_fields

    querysets = [
        project.discoveredpackages.all(),
        project.codebaseresources.without_symlinks(),
    ]

    output_files = []
    for queryset in querysets:
        model_class = queryset.model
        fieldnames = get_serializer_fields(model_class)

        model_name = model_class._meta.model_name
        output_filename = project.get_output_file_path(f"{model_name}", "csv")

        with output_filename.open("w") as output_file:
            queryset_to_csv_file(queryset, fieldnames, output_file)

        output_files.append(output_filename)

    return output_files


class JSONResultsGenerator:
    """
    Returns the `project` JSON results as a Python generator.
    Use this class to stream the results from the database to the client browser
    without having to load everything in memory first.

    Note that the Django Serializer class can output to a stream but can't be
    sent directly to a StreamingHttpResponse.
    The results would have to be streamed to a file first, then iterated by the
    StreamingHttpResponse, which do not work great in a HTTP request context as
    the request can timeout while the file is generated.

    This class re-use Serializers from the API to avoid code duplication.
    Those imports need to be kept internal to this class to prevent circular import
    issues.
    """

    def __init__(self, project):
        self.project = project

    def __iter__(self):
        yield "{\n"
        yield from self.serialize(label="headers", generator=self.get_headers)
        yield from self.serialize(label="packages", generator=self.get_packages)
        yield from self.serialize(label="dependencies", generator=self.get_dependencies)
        yield from self.serialize(label="files", generator=self.get_files, latest=True)
        yield "}"

    def serialize(self, label, generator, latest=False):
        yield f'"{label}": [\n'

        prefix = ",\n"
        first = True

        for entry in generator(self.project):
            if first:
                first = False
            else:
                entry = prefix + entry
            yield entry

        yield "]\n" if latest else "],\n"

    @staticmethod
    def encode(data):
        return json.dumps(data, indent=2, cls=DjangoJSONEncoder)

    def get_headers(self, project):
        from scanpipe.api.serializers import RunSerializer

        runs = project.runs.all()
        runs = RunSerializer(runs, many=True, exclude_fields=("url", "project"))

        headers = {
            "tool_name": "scanpipe",
            "tool_version": scancodeio_version,
            "notice": SCAN_NOTICE,
            "uuid": project.uuid,
            "created_date": project.created_date,
            "input_sources": project.input_sources_list,
            "runs": runs.data,
            "extra_data": project.extra_data,
        }
        yield self.encode(headers)

    def get_packages(self, project):
        from scanpipe.api.serializers import DiscoveredPackageSerializer

        packages = project.discoveredpackages.all().order_by(
            "type",
            "namespace",
            "name",
            "version",
        )

        for obj in packages.iterator():
            yield self.encode(DiscoveredPackageSerializer(obj).data)

    def get_dependencies(self, project):
        from scanpipe.api.serializers import DiscoveredDependencySerializer

        dependencies = project.discovereddependencys.all().order_by(
            "purl",
        )

        for obj in dependencies.iterator():
            yield self.encode(DiscoveredDependencySerializer(obj).data)

    def get_files(self, project):
        from scanpipe.api.serializers import CodebaseResourceSerializer

        resources = project.codebaseresources.without_symlinks()

        for obj in resources.iterator():
            yield self.encode(CodebaseResourceSerializer(obj).data)


def to_json(project):
    """
    Generates output for the provided `project` in JSON format.
    The output file is created in the `project` output/ directory.
    Returns the path of the generated output file.
    """
    results_generator = JSONResultsGenerator(project)
    output_file = project.get_output_file_path("results", "json")

    with output_file.open("w") as file:
        for chunk in results_generator:
            file.write(chunk)

    return output_file


def _queryset_to_xlsx_worksheet(queryset, workbook, exclude_fields=()):
    """
    Adds a new worksheet to the ``workbook`` ``xlsxwriter.Workbook`` using the
    ``queryset``. The ``queryset`` "model_name" is used as a name for the
    "worksheet".
    Exclude fields listed in the ``exclude_fields`` sequence of field names.

    Adds an extra trailing "xlsx_errors" column with conversion error messages if
    any. Returns a number of conversion errors.
    """

    from scanpipe.api.serializers import get_serializer_fields

    model_class = queryset.model
    model_name = model_class._meta.verbose_name_plural.title()

    fields = get_serializer_fields(model_class)
    exclude_fields = exclude_fields or []
    fields = [field for field in fields if field not in exclude_fields]

    return _add_xlsx_worksheet(
        workbook=workbook,
        worksheet_name=model_name,
        rows=queryset,
        fields=fields,
    )


def _add_xlsx_worksheet(workbook, worksheet_name, rows, fields):
    """
    Adds a new ``worksheet_name`` worksheet to the ``workbook``
    ``xlsxwriter.Workbook``. Write the iterable of ``rows`` objects using their
    attributes listed in the ``fields`` sequence of field names.
    Adds an "xlsx_errors" column with conversion error messages if any.
    Returns a number of conversion errors.
    """
    worksheet = workbook.add_worksheet(worksheet_name)
    worksheet.set_default_row(height=14)

    header = list(fields) + ["xlsx_errors"]
    worksheet.write_row(row=0, col=0, data=header)

    errors_count = 0
    errors_col_index = len(fields) - 1  # rows and cols are zero-indexed

    for row_index, record in enumerate(rows, start=1):
        row_errors = []
        for col_index, field in enumerate(fields):
            value = getattr(record, field)

            if not value:
                continue

            value, error = _adapt_value_for_xlsx(field, value)

            if error:
                row_errors.append(error)

            if value:
                worksheet.write_string(row_index, col_index, str(value))

        if row_errors:
            errors_count += len(row_errors)
            row_errors = "\n".join(row_errors)
            worksheet.write_string(row_index, errors_col_index, row_errors)

    return errors_count


# Some scan attributes such as "copyrights" are list of dicts.
#
#  'authors': [{'end_line': 7, 'start_line': 7, 'value': 'John Doe'}],
#  'copyrights': [{'end_line': 5, 'start_line': 5, 'value': 'Copyright (c) nexB Inc.'}],
#  'emails': [{'email': 'joe@foobar.com', 'end_line': 1, 'start_line': 1}],
#  'holders': [{'end_line': 5, 'start_line': 5, 'value': 'nexB Inc.'}],
#  'urls': [{'end_line': 3, 'start_line': 3, 'url': 'https://foobar.com/'}]
#
# We therefore use a mapping to find which key to use in these mappings until
# this is fixed updated in scancode-toolkit with these:
# https://github.com/nexB/scancode-toolkit/pull/2381
# https://github.com/nexB/scancode-toolkit/issues/2350
mappings_key_by_fieldname = {
    "copyrights": "copyright",
    "holders": "holder",
    "authors": "author",
    "emails": "email",
    "urls": "url",
}


def _adapt_value_for_xlsx(fieldname, value, maximum_length=32767, _adapt=True):
    """
    Returns two tuples of:
    (``value`` adapted for use in an XLSX cell, error message or None)

    Convert the value to a string and perform these adaptations:
    - Keep only unique values in lists, preserving ordering.
    - Truncate the "description" field to the first five lines.
    - Truncate any field too long to fit in an XLSX cell and report error.
    - Create a combined license expression for expressions
    - Normalize line endings
    - Truncate the value to a ``maximum_length`` supported by XLSX.

    Does nothing if "_adapt" is False (used for tests).
    """
    error = None
    if not _adapt:
        return value, error

    if not value:
        return "", error

    if fieldname == "description":
        max_description_lines = 5
        value = "\n".join(value.splitlines(False)[:max_description_lines])

    if fieldname == "license_expressions":
        value = combine_expressions(value)

    # we only get this key in each dict of a list for some fields
    mapping_key = mappings_key_by_fieldname.get(fieldname)
    if mapping_key:
        value = [mapping[mapping_key] for mapping in value]

    # convert these to text lines, remove duplicates
    if isinstance(value, (list, tuple)):
        value = (str(v) for v in value if v)
        value = ordered_unique(value)
        value = "\n".join(value)

    # convert these to YAML which is the most readable dump format
    if isinstance(value, dict):
        value = saneyaml.dump(value)

    value = str(value)

    # XLSX does not like CRLF
    value = value.replace("\r\n", "\n")

    # XLSX does not like long values
    len_val = len(value)
    if len_val > maximum_length:
        error = (
            f"The value of: {fieldname} has been truncated from: {len_val} "
            f"to {maximum_length} length to fit in an XLSL cell maximum length"
        )
        value = value[:maximum_length]

    return value, error


def to_xlsx(project):
    """
    Generates output for the provided ``project`` in XLSX format.
    The output file is created in the ``project`` "output/" directory.
    Return the path of the generated output file.

    Note that the XLSX worksheets contain each an extra "xlxs_errors" column
    with possible error messages for a row when converting the data to XLSX
    exceed the limits of what can be stored in a cell.
    """
    output_file = project.get_output_file_path("results", "xlsx")
    exclude_fields = ["licenses", "extra_data", "declared_license"]

    if not scanpipe_app.policies_enabled:
        exclude_fields.append("compliance_alert")

    querysets = [
        project.discoveredpackages.all(),
        project.codebaseresources.without_symlinks(),
        project.projecterrors.all(),
    ]

    with xlsxwriter.Workbook(output_file) as workbook:
        for queryset in querysets:
            _queryset_to_xlsx_worksheet(queryset, workbook, exclude_fields)

    return output_file

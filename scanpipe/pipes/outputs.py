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

from django.core.serializers.json import DjangoJSONEncoder

import xlsxwriter
from license_expression import ordered_unique
from packagedcode.utils import combine_expressions

from scancodeio import SCAN_NOTICE
from scancodeio import __version__ as scancodeio_version
from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import RunSerializer
from scanpipe.api.serializers import get_serializer_fields


def queryset_to_csv_file(queryset, fieldnames, output_file):
    """
    Output csv content generated from the provided `queryset` objects to the
    `output_file`.
    The fields to include as columns and their order are controlled by the
    `fieldnames` list.
    """
    writer = csv.DictWriter(output_file, fieldnames)
    writer.writeheader()

    for record in queryset.iterator():
        row = {field: getattr(record, field) for field in fieldnames}
        writer.writerow(row)


def queryset_to_csv_stream(queryset, fieldnames, output_stream):
    """
    Output csv content generated from the provided `queryset` objects to the
    `output_stream`.
    The fields to include as columns and their order are controlled by the
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
    Generate results output for the provided `project` as csv format.
    Since the csv format does not support multiple tabs, one file is created
    per object type.
    The output files are created in the `project` output/ directory.
    Return the list of path of the generated output files.
    """
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
    Return the `project` JSON results as a Python generator.
    Use this class to stream the results from the database to the client browser
    without having to load everything in memory first.

    Note that the Django Serializer class can output to a stream but cannot be
    sent directly to a StreamingHttpResponse.
    The results would have to be streamed to a file first, then iterated by the
    StreamingHttpResponse, which do not work great in a HTTP request context as
    the request can timeout while the file is generated.
    """

    def __init__(self, project):
        self.project = project

    def __iter__(self):
        yield "{\n"
        yield from self.serialize(label="headers", generator=self.get_headers)
        yield from self.serialize(label="packages", generator=self.get_packages)
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
        runs = project.runs.all()
        runs = RunSerializer(runs, many=True, exclude_fields=("url", "project"))

        headers = {
            "tool_name": "scanpipe",
            "tool_version": scancodeio_version,
            "notice": SCAN_NOTICE,
            "uuid": project.uuid,
            "created_date": project.created_date,
            "input_files": project.input_files,
            "runs": runs.data,
            "extra_data": project.extra_data,
        }
        yield self.encode(headers)

    def get_packages(self, project):
        packages = project.discoveredpackages.all()

        for obj in packages.iterator():
            yield self.encode(DiscoveredPackageSerializer(obj).data)

    def get_files(self, project):
        resources = project.codebaseresources.without_symlinks()

        for obj in resources.iterator():
            yield self.encode(CodebaseResourceSerializer(obj).data)


def to_json(project):
    """
    Generate results output for the provided `project` as JSON format.
    The output file is created in the `project` output/ directory.
    Return the path of the generated output file.
    """
    results_generator = JSONResultsGenerator(project)
    output_file = project.get_output_file_path("results", "json")

    with output_file.open("w") as file:
        for chunk in results_generator:
            file.write(chunk)

    return output_file


def _queryset_to_xlsx_worksheet(queryset, workbook, exclude_fields=None):
    multivalues_separator = "\n"

    model_class = queryset.model
    model_name = model_class._meta.model_name

    fieldnames = get_serializer_fields(model_class)
    exclude_fields = exclude_fields or []
    fieldnames = [field for field in fieldnames if field not in exclude_fields]

    worksheet = workbook.add_worksheet(model_name)
    worksheet.write_row(row=0, col=0, data=fieldnames)

    for row_index, record in enumerate(queryset.iterator(), start=1):
        for col_index, field in enumerate(fieldnames):
            value = getattr(record, field)
            if not value:
                continue
            elif field == "license_expressions":
                value = combine_expressions(value)
            elif isinstance(value, list):
                value = [
                    list(entry.values())[0] if isinstance(entry, dict) else str(entry)
                    for entry in value
                ]
                value = multivalues_separator.join(ordered_unique(value))
            elif isinstance(value, dict):
                value = json.dumps(value) if value else ""

            worksheet.write_string(row_index, col_index, str(value))


def to_xlsx(project):
    """
    Generate results output for the provided `project` as XLSX format.
    The output file is created in the `project` output/ directory.
    Return the path of the generated output file.
    """
    output_file = project.get_output_file_path("results", "xlsx")
    exclude_fields = ["licenses", "extra_data", "declared_license"]

    querysets = [
        project.discoveredpackages.all(),
        project.codebaseresources.without_symlinks(),
    ]

    with xlsxwriter.Workbook(output_file) as workbook:
        for queryset in querysets:
            _queryset_to_xlsx_worksheet(queryset, workbook, exclude_fields)

    return output_file

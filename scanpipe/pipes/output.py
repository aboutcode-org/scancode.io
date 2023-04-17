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
import re

from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder

import saneyaml
import xlsxwriter
from cyclonedx import output as cyclonedx_output
from cyclonedx.model import bom as cyclonedx_bom
from cyclonedx.model import component as cyclonedx_component
from license_expression import Licensing
from license_expression import ordered_unique
from licensedcode.cache import build_spdx_license_expression
from licensedcode.cache import get_licenses_by_spdx_key
from packagedcode.utils import combine_expressions
from scancode_config import __version__ as scancode_toolkit_version

from scancodeio import SCAN_NOTICE
from scancodeio import __version__ as scancodeio_version
from scanpipe.pipes import docker
from scanpipe.pipes import spdx

scanpipe_app = apps.get_app_config("scanpipe")


def safe_filename(filename):
    """Convert the provided `filename` to a safe filename."""
    return re.sub("[^A-Za-z0-9.-]+", "_", filename).lower()


def get_queryset(project, model_name):
    """Return a consistent QuerySet for all supported outputs (json, xlsx, csv, ...)"""
    querysets = {
        "discoveredpackage": (
            project.discoveredpackages.all().order_by(
                "type",
                "namespace",
                "name",
                "version",
            )
        ),
        "discovereddependency": (
            project.discovereddependencies.all()
            .prefetch_for_serializer()
            .order_by(
                "type",
                "namespace",
                "name",
                "version",
                "datasource_id",
            )
        ),
        "codebaseresource": (
            project.codebaseresources.without_symlinks().prefetch_for_serializer()
        ),
        "projecterror": project.projecterrors.all(),
    }
    return querysets.get(model_name)


def queryset_to_csv_file(queryset, fieldnames, output_file):
    """
    Output csv content generated from the provided `queryset` objects to the
    `output_file`.
    The fields to be included as columns and their order are controlled by the
    `fieldnames` list.
    """
    writer = csv.DictWriter(output_file, fieldnames)
    writer.writeheader()

    for record in queryset.iterator(chunk_size=2000):
        row = {field: getattr(record, field) for field in fieldnames}
        writer.writerow(row)


def queryset_to_csv_stream(queryset, fieldnames, output_stream):
    """
    Output csv content generated from the provided `queryset` objects to the
    `output_stream`.
    The fields to be included as columns and their order are controlled by the
    `fieldnames` list.
    """
    writer = csv.DictWriter(output_stream, fieldnames)
    # Not using writer.writeheader() since this method do not "return" the
    # value while writer.writerow() does.
    header = dict(zip(fieldnames, fieldnames))
    yield writer.writerow(header)

    for record in queryset.iterator(chunk_size=2000):
        row = {field: getattr(record, field) for field in fieldnames}
        yield writer.writerow(row)


def to_csv(project):
    """
    Generate output for the provided `project` in csv format.
    Since the csv format does not support multiple tabs, one file is created
    per object type.
    The output files are created in the `project` output/ directory.
    Return a list of paths of the generated output files.
    """
    from scanpipe.api.serializers import get_serializer_fields

    model_names = [
        "discoveredpackage",
        "discovereddependency",
        "codebaseresource",
        "projecterror",
    ]

    output_files = []

    for model_name in model_names:
        queryset = get_queryset(project, model_name)
        model_class = queryset.model
        fieldnames = get_serializer_fields(model_class)
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

        other_tools = [f"pkg:pypi/scancode-toolkit@{scancode_toolkit_version}"]

        headers = {
            "tool_name": "scanpipe",
            "tool_version": scancodeio_version,
            "other_tools": other_tools,
            "notice": SCAN_NOTICE,
            "uuid": project.uuid,
            "created_date": project.created_date,
            "input_sources": project.input_sources_list,
            "runs": runs.data,
            "extra_data": project.extra_data,
        }
        yield self.encode(headers)

    def encode_queryset(self, project, model_name, serializer):
        queryset = get_queryset(project, model_name)
        for obj in queryset.iterator(chunk_size=2000):
            yield self.encode(serializer(obj).data)

    def get_packages(self, project):
        from scanpipe.api.serializers import DiscoveredPackageSerializer

        yield from self.encode_queryset(
            project, "discoveredpackage", DiscoveredPackageSerializer
        )

    def get_dependencies(self, project):
        from scanpipe.api.serializers import DiscoveredDependencySerializer

        yield from self.encode_queryset(
            project, "discovereddependency", DiscoveredDependencySerializer
        )

    def get_files(self, project):
        from scanpipe.api.serializers import CodebaseResourceSerializer

        yield from self.encode_queryset(
            project, "codebaseresource", CodebaseResourceSerializer
        )


def to_json(project):
    """
    Generate output for the provided `project` in JSON format.
    The output file is created in the `project` output/ directory.
    Return the path of the generated output file.
    """
    results_generator = JSONResultsGenerator(project)
    output_file = project.get_output_file_path("results", "json")

    with output_file.open("w") as file:
        for chunk in results_generator:
            file.write(chunk)

    return output_file


model_name_to_worksheet_name = {
    "discoveredpackage": "PACKAGES",
    "discovereddependency": "DEPENDENCIES",
    "codebaseresource": "RESOURCES",
    "projecterror": "ERRORS",
}


def queryset_to_xlsx_worksheet(queryset, workbook, exclude_fields=()):
    """
    Add a new worksheet to the ``workbook`` ``xlsxwriter.Workbook`` using the
    ``queryset``. The ``queryset`` "model_name" is used as a name for the
    "worksheet".
    Exclude fields listed in the ``exclude_fields`` sequence of field names.

    Add an extra trailing "xlsx_errors" column with conversion error messages if
    any. Return a number of conversion errors.
    """
    from scanpipe.api.serializers import get_serializer_fields

    model_class = queryset.model
    model_name = model_class._meta.model_name
    worksheet_name = model_name_to_worksheet_name.get(model_name)

    fields = get_serializer_fields(model_class)
    exclude_fields = exclude_fields or []
    fields = [field for field in fields if field not in exclude_fields]

    return _add_xlsx_worksheet(
        workbook=workbook,
        worksheet_name=worksheet_name,
        rows=queryset,
        fields=fields,
    )


def _add_xlsx_worksheet(workbook, worksheet_name, rows, fields):
    """
    Add a new ``worksheet_name`` worksheet to the ``workbook``
    ``xlsxwriter.Workbook``. Write the iterable of ``rows`` objects using their
    attributes listed in the ``fields`` sequence of field names.
    Add a "xlsx_errors" column with conversion error messages if any.
    Return a number of conversion errors.
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
    Return two tuples of:
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
    Generate output for the provided ``project`` in XLSX format.
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

    model_names = [
        "discoveredpackage",
        "discovereddependency",
        "codebaseresource",
        "projecterror",
    ]

    with xlsxwriter.Workbook(output_file) as workbook:
        for model_name in model_names:
            queryset = get_queryset(project, model_name)
            queryset_to_xlsx_worksheet(queryset, workbook, exclude_fields)

        if layers_data := docker.get_layers_data(project):
            _add_xlsx_worksheet(workbook, "LAYERS", layers_data, docker.layer_fields)

    return output_file


def _get_spdx_extracted_licenses(license_expressions):
    """
    Generate and return the SPDX `extracted_licenses` from provided
    `license_expressions` list of expressions.
    """
    licensing = Licensing()
    license_index = get_licenses_by_spdx_key()
    urls_fields = [
        "faq_url",
        "homepage_url",
        "osi_url",
        "ignorable_urls",
        "other_urls",
        "text_urls",
    ]
    spdx_license_refs = set()
    extracted_licenses = []

    for expression in license_expressions:
        spdx_expression = build_spdx_license_expression(expression)
        license_keys = licensing.license_keys(spdx_expression)
        spdx_license_refs.update(
            [key for key in license_keys if key.startswith("LicenseRef")]
        )

    for license_ref in spdx_license_refs:
        license = license_index.get(license_ref.lower())

        see_alsos = []
        for field_name in urls_fields:
            value = getattr(license, field_name)
            if isinstance(value, list):
                see_alsos.extend(value)
            elif value:
                see_alsos.append(value)

        extracted_licenses.append(
            spdx.ExtractedLicensingInfo(
                license_id=license.spdx_license_key,
                extracted_text=license.text or " ",
                name=license.name,
                see_alsos=see_alsos,
            )
        )

    return extracted_licenses


def to_spdx(project):
    """
    Generate output for the provided ``project`` in SPDX document format.
    The output file is created in the ``project`` "output/" directory.
    Return the path of the generated output file.
    """
    output_file = project.get_output_file_path("results", "spdx.json")

    discovereddependencies_qs = get_queryset(project, "discovereddependency")
    spdx_packages = [
        *get_queryset(project, "discoveredpackage"),
        *discovereddependencies_qs,
    ]

    packages_as_spdx = []
    license_expressions = []
    for spdx_package in spdx_packages:
        packages_as_spdx.append(spdx_package.as_spdx())
        if license_expression := getattr(spdx_package, "license_expression", None):
            license_expressions.append(license_expression)

    relationships = [
        spdx.Relationship(
            spdx_id=dep.spdx_id,
            related_spdx_id=dep.for_package.spdx_id,
            relationship="DEPENDENCY_OF",
        )
        for dep in discovereddependencies_qs
        if dep.for_package
    ]

    files_as_spdx = [
        resource.as_spdx()
        for resource in get_queryset(project, "codebaseresource").files()
    ]

    document = spdx.Document(
        name=f"scancodeio_{project.name}",
        namespace=f"https://scancode.io/spdxdocs/{project.uuid}",
        creation_info=spdx.CreationInfo(tool=f"ScanCode.io-{scancodeio_version}"),
        packages=packages_as_spdx,
        files=files_as_spdx,
        extracted_licenses=_get_spdx_extracted_licenses(license_expressions),
        relationships=relationships,
        comment=SCAN_NOTICE,
    )

    with output_file.open("w") as file:
        file.write(document.as_json())

    return output_file


def get_cyclonedx_bom(project):
    """
    Return a CycloneDX `Bom` object filled with provided `project` data.
    See https://cyclonedx.org/use-cases/#dependency-graph
    """
    components = [
        *get_queryset(project, "discoveredpackage"),
    ]

    cyclonedx_components = [component.as_cyclonedx() for component in components]

    bom = cyclonedx_bom.Bom(components=cyclonedx_components)

    project_as_cyclonedx = cyclonedx_component.Component(
        name=project.name,
        bom_ref=str(project.uuid),
    )

    project_as_cyclonedx.dependencies.update(
        [component.bom_ref for component in cyclonedx_components]
    )

    bom.metadata = cyclonedx_bom.BomMetaData(
        component=project_as_cyclonedx,
        tools=[
            cyclonedx_bom.Tool(
                name="ScanCode.io",
                version=scancodeio_version,
            )
        ],
        properties=[
            cyclonedx_bom.Property(
                name="notice",
                value=SCAN_NOTICE,
            )
        ],
    )

    return bom


def to_cyclonedx(project):
    """
    Generate output for the provided ``project`` in CycloneDX BOM format.
    The output file is created in the ``project`` "output/" directory.
    Return the path of the generated output file.
    """
    output_file = project.get_output_file_path("results", "bom.json")

    cyclonedx_bom = get_cyclonedx_bom(project)

    outputter = cyclonedx_output.get_instance(
        bom=cyclonedx_bom,
        output_format=cyclonedx_output.OutputFormat.JSON,
    )

    bom_json = outputter.output_as_string()
    with output_file.open("w") as file:
        file.write(bom_json)

    return output_file

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

from scancodeio import SCAN_NOTICE
from scancodeio import __version__ as scancodeio_version
from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import RunSerializer


def queryset_to_csv(project, queryset, fieldnames):
    """
    Create a csv file from the provided `queryset`.
    The fields to include as columns and their order are controlled by the
    `fieldnames` list.
    The output file is created in the `project` output/ directory.
    """
    model_name = queryset.model._meta.model_name
    filename = f"{project.name}_{model_name}.csv"
    output_file = project.output_path / filename

    with open(output_file, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames)
        writer.writeheader()
        for record in queryset.iterator():
            record_dict = {field: getattr(record, field) for field in fieldnames}
            writer.writerow(record_dict)

    return output_file


def to_csv(project):
    """
    Generate results output for the provided `project` as csv format.
    Since the csv format does not support multiple tabs, one file is created
    per object type.
    The output files are created in the `project` output directory.
    """
    data_sources = [
        (project.discoveredpackages.all(), DiscoveredPackageSerializer),
        (project.codebaseresources.without_symlinks(), CodebaseResourceSerializer),
    ]

    for queryset, serializer in data_sources:
        fieldnames = list(serializer().get_fields().keys())
        queryset_to_csv(project, queryset, fieldnames)


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
        resources = resources.prefetch_related("discovered_packages")

        for obj in resources.iterator():
            yield self.encode(CodebaseResourceSerializer(obj).data)


def to_json(project):
    """
    Generate results output for the provided `project` as JSON format.
    The output file is created in the `project` output/ directory.
    """
    results_generator = JSONResultsGenerator(project)
    output_file = project.output_path / "results.json"

    with output_file.open("w") as file:
        for chunk in results_generator:
            file.write(chunk)

    return output_file

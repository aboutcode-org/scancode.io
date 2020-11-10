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

from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer


def queryset_to_csv(project, queryset, fieldnames):
    """
    Create a csv file from the provided `queryset`.
    The fields to include as columns and their order are controlled by the
    `fieldnames` list.
    The output file is created in the `project` output directory.
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
    """
    data_sources = [
        (project.discoveredpackages.all(), DiscoveredPackageSerializer),
        (project.codebaseresources.without_symlinks(), CodebaseResourceSerializer),
    ]

    for queryset, serializer in data_sources:
        fieldnames = list(serializer().get_fields().keys())
        queryset_to_csv(project, queryset, fieldnames)

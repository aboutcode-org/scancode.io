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

from io import StringIO
import json

from commoncode.resource import VirtualCodebase
from matchcode_toolkit.fingerprinting import compute_directory_fingerprints

from scanpipe.pipes.output import JSONResultsGenerator


def _get_virtual_codebase_from_project(project):
    """
    Return the codebase from `project` as a VirtualCodebase
    """
    # Collect project JSON results into a buffer
    buf = StringIO()
    results_generator = JSONResultsGenerator(project)
    for chunk in results_generator:
        buf.write(chunk)

    # Rewind buffer, load contents as JSON, and return as VirtualCodebase
    buf.seek(0)
    json_scan = json.load(buf)
    return VirtualCodebase(location=json_scan)


def fingerprint_codebase_directories(project):
    """
    Compute directory fingerprints for matching purposes
    """
    # Load project into a VirtualCodebase and compute directory fingerprints in
    # memory
    virtual_codebase = _get_virtual_codebase_from_project(project)
    compute_directory_fingerprints(virtual_codebase)

    # Bulk update Directories with new fingerprints.
    # Code adapted from
    # scanpipe.migrations.0031_scancode_toolkit_v32_data_updates
    queryset = project.codebaseresources.directories()
    object_count = queryset.count()
    print(f"\nUpdating directory fingerprints for {object_count:,} directories.")
    chunk_size = 2000
    iterator = queryset.iterator(chunk_size=chunk_size)

    unsaved_objects = []
    for index, resource in enumerate(iterator, start=1):
        vc_path = f"virtual_root/{resource.path}"
        vc_resource = virtual_codebase.get_resource(vc_path)

        extra_data_keys = [
            "directory_content",
            "directory_structure",
        ]
        for key in extra_data_keys:
            value = vc_resource.extra_data.get(key)
            resource.extra_data[key] = value

        unsaved_objects.append(resource)

        if not (index % chunk_size) and unsaved_objects:
            print(f"  {index:,} / {object_count:,} directories processed")

    print("Updating directory DB objects...")
    project.codebaseresources.bulk_update(
        objs=unsaved_objects,
        fields=["extra_data"],
        batch_size=1000,
    )

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

from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints

from scanpipe.pipes import codebase


def save_directory_fingerprints(project, virtual_codebase, to_codebase_only=False):
    """
    Save directory fingerprints from directory Resources in `virtual_codebase`
    to the directory CodebaseResources from `project` that have the same path.

    If `to_codebase_only` is True, then we are only saving the directory
    fingerprints for directories from the to/ codebase of a d2d project.
    """

    # Bulk update Directories with new fingerprints.
    # Code adapted from
    # scanpipe.migrations.0031_scancode_toolkit_v32_data_updates
    queryset = project.codebaseresources.directories()
    if to_codebase_only:
        queryset = queryset.to_codebase()

    object_count = queryset.count()
    print(f"\nUpdating directory fingerprints for {object_count:,} directories.")
    chunk_size = 2000
    iterator = queryset.iterator(chunk_size=chunk_size)

    unsaved_objects = []
    has_virtual_codebase_prefix = virtual_codebase.root.path == "virtual_codebase"
    for index, directory in enumerate(iterator, start=1):
        if has_virtual_codebase_prefix:
            vc_path = f"virtual_codebase/{directory.path}"
        else:
            vc_path = directory.path

        vc_directory = virtual_codebase.get_resource(vc_path)
        if not vc_directory:
            # Generally, `virtual_codebase` should contain the Resources and
            # Directories that we care to create fingerprints for.
            # If `directory` is not in `virtual_codebase`, we can skip it.
            continue

        extra_data_keys = [
            "directory_content",
            "directory_structure",
        ]
        for key in extra_data_keys:
            value = vc_directory.extra_data.get(key, "")
            directory.extra_data[key] = value

        unsaved_objects.append(directory)

        if not (index % chunk_size) and unsaved_objects:
            print(f"  {index:,} / {object_count:,} directories processed")

    print("Updating directory DB objects...")
    project.codebaseresources.bulk_update(
        objs=unsaved_objects,
        fields=["extra_data"],
        batch_size=1000,
    )


def fingerprint_codebase_directories(project, to_codebase_only=False):
    """
    Compute directory fingerprints for the directories of the to/ codebase from
    `project`.

    These directory fingerprints are used for matching purposes on matchcode.
    """
    resources = project.codebaseresources.all()
    if to_codebase_only:
        resources = resources.to_codebase()
    virtual_codebase = codebase.get_basic_virtual_codebase(resources)
    virtual_codebase = compute_codebase_directory_fingerprints(virtual_codebase)
    save_directory_fingerprints(project, virtual_codebase, to_codebase_only=to_codebase_only)

#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import logging

from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints

from scanpipe.pipes import codebase

logger = logging.getLogger(__name__)


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
    logger.info(f"\nUpdating directory fingerprints for {object_count:,} directories.")
    chunk_size = 2000
    iterator = queryset.iterator(chunk_size=chunk_size)

    unsaved_objects = []
    has_virtual_root_prefix = virtual_codebase.root.path == "virtual_root"
    for index, directory in enumerate(iterator, start=1):
        if has_virtual_root_prefix:
            vc_path = f"virtual_root/{directory.path}"
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
            logger.info(f"  {index:,} / {object_count:,} directories processed")

    logger.info("Updating directory DB objects...")
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
    save_directory_fingerprints(
        project, virtual_codebase, to_codebase_only=to_codebase_only
    )

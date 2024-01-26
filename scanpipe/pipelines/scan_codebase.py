#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_inputs


class ScanCodebase(Pipeline):
    """
    Scan a codebase with ScanCode-toolkit.

    If the codebase consists of several packages and dependencies, it will try to
    resolve and scan those too.

    Input files are copied to the project's codebase/ directory and are extracted
    in place before running the scan.
    Alternatively, the code can be manually copied to the project codebase/
    directory.
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.scan_for_files,
        )

    def copy_inputs_to_codebase_directory(self):
        """
        Copy input files to the project's codebase/ directory.
        The code can also be copied there prior to running the Pipeline.
        """
        copy_inputs(self.project.inputs(), self.project.codebase_path)

    def extract_archives(self):
        """Extract archives with extractcode."""
        extract_errors = scancode.extract_archives(
            location=self.project.codebase_path,
            recurse=self.env.get("extract_recursively", True),
        )

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        pipes.collect_and_create_codebase_resources(self.project)

    def scan_for_application_packages(self):
        """Scan unknown resources for packages information."""
        scancode.scan_for_application_packages(self.project, progress_logger=self.log)

    def scan_for_files(self):
        """Scan unknown resources for copyrights, licenses, emails, and urls."""
        scancode.scan_for_files(self.project, progress_logger=self.log)

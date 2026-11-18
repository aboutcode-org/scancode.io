# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import yara
from scanpipe.pipes.input import copy_inputs


class ScanAndMatchWithYara(Pipeline):
    """Scan a codebase and identify packages using YARA rules."""

    download_inputs = True
    results_url = "/project/{slug}/packages/"

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.match_resources_by_yara_rules,
        )

    def copy_inputs_to_codebase_directory(self):
        """Copy inputs to the project codebase directory."""
        copy_inputs(self.project.inputs("*"), self.project.codebase_path)

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        pipes.collect_and_create_codebase_resources(self.project)

    def match_resources_by_yara_rules(self):
        """Match codebase files to packages using YARA pattern rules."""
        yara.match_resources_by_yara(self.project, logger=self.log)

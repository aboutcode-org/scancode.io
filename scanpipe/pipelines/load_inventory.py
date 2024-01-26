#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import json

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import input


class LoadInventory(Pipeline):
    """
    Load JSON/XLSX inventory files generated with ScanCode-toolkit or ScanCode.io.

    Supported format are ScanCode-toolkit JSON scan results, ScanCode.io JSON output,
    and ScanCode.io XLSX output.

    An inventory is composed of packages, dependencies, resources, and relations.
    """

    supported_extensions = [".json", ".xlsx"]

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.build_inventory_from_scans,
        )

    def get_inputs(self):
        """Locate all the supported input files from the project's input/ directory."""
        self.input_paths = self.project.inputs(extensions=self.supported_extensions)

    def build_inventory_from_scans(self):
        """
        Process JSON scan results files to populate packages, dependencies, and
        resources.
        """
        for input_path in self.input_paths:
            if input_path.suffix.endswith(".xlsx"):
                input.load_inventory_from_xlsx(self.project, input_path)
                continue

            scan_data = json.loads(input_path.read_text())
            tool_name = input.get_tool_name_from_scan_headers(scan_data)

            if tool_name == "scancode-toolkit":
                input.load_inventory_from_toolkit_scan(self.project, input_path)
            elif tool_name == "scanpipe":
                input.load_inventory_from_scanpipe(self.project, scan_data)
            else:
                raise Exception(f"Input not supported: {str(input_path)} ")

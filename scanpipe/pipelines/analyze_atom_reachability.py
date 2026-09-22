# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import json
import subprocess
from os import environ

from scanpipe.pipes import atom
from scanpipe.pipes import run_command_safely
from scanpipe.pipes.reachability_tools import ReachabilityPipeline
from scanpipe.pipes.reachability_tools import ReachabilityTool

ATOM_EXECUTABLE = environ.get("ATOM_EXECUTABLE")


class AtomTool(ReachabilityTool):
    tool_name = "atom"
    executable = ATOM_EXECUTABLE
    supported_languages = ("Python", "Java")
    atom_language = "python"

    @classmethod
    def get_availability(cls):
        if not cls.executable:
            return "atom is not configured. Set the ATOM_EXECUTABLE environment variable."

    @classmethod
    def get_target_path(cls, project):
        target_path = project.codebase_path
        if target_path:
            return target_path
        resource = project.codebaseresources.filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=cls.supported_languages,
        ).first()
        if not resource:
            raise ValueError("No codebase resources found for this project.")
        return resource.location_path

    @classmethod
    def run(cls, project, logger=None):
        """Run the atom ``usages`` command and return the slices file path."""
        target_path = cls.get_target_path(project)
        manifest_path = project.get_output_file_path("atom_reachability", "json")
        prefix = f"{manifest_path.stem}.{cls.atom_language}"
        slice_path = manifest_path.with_name(f"{prefix}.usages.slices.json")
        atom_path = manifest_path.with_name(f"{prefix}.atom")

        command_args = [
            cls.executable, "usages",
            "-l", cls.atom_language,
            "-o", str(atom_path),
            "-s", str(slice_path),
            str(target_path),
        ]

        logger(f"Running atom usages on {target_path} ...")
        try:
            run_command_safely(command_args=command_args)
        except subprocess.SubprocessError as error:
            logger(f"atom usages failed: {error!r}")
            return None
        return slice_path

    @classmethod
    def parsed_output(cls, export_output_path, logger=None):
        """Load and return the ``usages`` slices file."""
        if not export_output_path:
            return {}
        try:
            with open(export_output_path) as slice_file:
                return json.load(slice_file)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            if logger:
                logger(f"Skipping atom usages slices: {error!r}")
            return {}


class AtomReachability(ReachabilityPipeline):
    """
    Determine the reachability of vulnerabilities using the atom tool.

    Note: You must run the ``find_vulnerabilities`` pipeline before running
    this pipeline.

    atom is run once to generate a ``usages`` slice of the project codebase.
    The vulnerable and fixed symbols of each patch are matched against that
    slice with dot-boundary suffix matching:

    - REACHABLE: the symbol has a call site in the code
    - NOT_REACHABLE: the symbol is absent
    - UNKNOWN: the symbol is defined in the code

    Results are stored in the ``extra_data`` of the matching resources under
    the ``symbols_reachability`` key.
    """

    reachability_tool = AtomTool

    @classmethod
    def get_availability(cls):
        return cls.reachability_tool.get_availability()

    def get_candidate_resources(self):
        """Collect candidate resources for this pipeline."""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=self.reachability_tool.supported_languages,
        )

    def collect_resource_index(self):
        """Generate the atom usages slice and load it."""
        self.resource_indexes_path = self.reachability_tool.run(
            project=self.project, logger=self.log
        )
        self.resource_indexes = self.reachability_tool.parsed_output(
            export_output_path=self.resource_indexes_path, logger=self.log
        )

    def collect_and_match_resources(self):
        """Match patch symbols against the atom usages slice."""
        atom.collect_and_match_resources(
            tool_name=self.reachability_tool.tool_name,
            patches=self.patches,
            patch_symbols=self.patch_symbols,
            resource_indexes=self.resource_indexes,
            candidate_resources=self.candidate_resources,
            logger=self.log,
        )
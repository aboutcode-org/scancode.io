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
import subprocess
from os import environ

from scanpipe.pipes import cpg
from scanpipe.pipes import run_command_safely
from scanpipe.pipes.reachability_tools import ReachabilityPipeline
from scanpipe.pipes.reachability_tools import ReachabilityTool

CPG_NEO4J_EXECUTABLE = environ.get("CPG_NEO4J_EXECUTABLE")
CPG_NEO4J_HOST = environ.get("CPG_NEO4J_HOST", "localhost")
CPG_NEO4J_PORT = environ.get("CPG_NEO4J_PORT", "7687")
CPG_NEO4J_USER = environ.get("CPG_NEO4J_USER", "neo4j")
CPG_NEO4J_PASSWORD = environ.get("CPG_NEO4J_PASSWORD", "password")


class CPGTool(ReachabilityTool):
    """Reachability analysis tool based on a Code Property Graph (CPG)"""

    tool_name = "cpg_tool"
    executable = CPG_NEO4J_EXECUTABLE
    supported_languages = ("Python", "Java", "JavaScript", "C++")

    @classmethod
    def get_availability(cls):
        if not cls.executable:
            return "CPG is not configured."

    @classmethod
    def run(cls, project, logger=None):
        """Run the CPG client on the codebase and return the exported JSON Path."""
        target_path = project.codebase_path
        if not target_path:
            resources = project.codebaseresources.all()
            if not resources:
                raise ValueError("No codebase resources found for this project.")
            target_path = resources[0].location_path

        export_json_path = project.get_output_file_path("cpg_reachability", "json")
        command_args = [
            CPG_NEO4J_EXECUTABLE,
            "--host",
            CPG_NEO4J_HOST,
            "--port",
            CPG_NEO4J_PORT,
            "--user",
            CPG_NEO4J_USER,
            "--password",
            CPG_NEO4J_PASSWORD,
            "--export-json",
            str(export_json_path),
            "--top-level",
            str(target_path),
            str(target_path),
        ]

        logger(f"Generating CPG JSON for {target_path} ...")
        try:
            run_command_safely(command_args=command_args)
            logger("CPG resource_index pipeline completed successfully")
            return export_json_path
        except subprocess.SubprocessError as error:
            raise RuntimeError(f"CPG client failure: {error!r}")
        except FileNotFoundError:
            raise FileNotFoundError(
                "CPG not found. Please ensure CPG is correctly configured."
            )


class CPGReachability(ReachabilityPipeline):
    """
    Determine the reachability of vulnerabilities using a Code Property
    Graph (CPG) tool.

    Note: You must run the ``find_vulnerabilities`` pipeline before running
    this pipeline.

    The project codebase is exported once as a CPG JSON graph. The vulnerable
    and fixed symbols of each patch are matched against that graph, and a
    symbol is reachable when it can be reached from a codebase entry point
    following the evaluation order (EOG) of the graph. Results are stored in
    the ``extra_data`` of the matching resources under the
    ``symbols_reachability`` key, and a summary report is generated for each
    vulnerability advisory.
    """

    reachability_tool = CPGTool

    @classmethod
    def get_availability(cls):
        if not CPG_NEO4J_EXECUTABLE:
            return "CPG is not configured."

    def get_candidate_resources(self):
        """Collect candidate resources your pipeline needs."""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=self.reachability_tool.supported_languages,
        )

    def collect_resource_index(self):
        """Collect resources symbols for each resource"""
        self.resource_indexes_path = self.reachability_tool.run(
            project=self.project, logger=self.log
        )

    def collect_and_match_resources(self):
        """Match resource symbols against patch symbols."""
        cpg.match_patches_to_resources(
            tool_name=self.reachability_tool.tool_name,
            patches=self.patches,
            patch_symbols=self.patch_symbols,
            candidate_resources=self.candidate_resources,
            logger=self.log,
        )

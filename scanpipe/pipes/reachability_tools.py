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

from abc import ABC

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import reachability


class ReachabilityTool(ABC):
    """
    Base class for the analysis tools used by ReachabilityPipeline.
    Uses:
        Subclasses must implement ``get_availability`` and ``run``.
        They may optionally implement ``parsed_output`` to parse the
        tool's output file, if applicable.
    """

    tool_name = ""
    executable = None
    supported_languages = ()

    @classmethod
    def get_availability(cls):
        """Return None if this tool is available, or a reason string if not."""
        return NotImplementedError

    @classmethod
    def run(cls, project, logger=None):
        """
        Run the analysis tool on the given project and return its output path
        or store the results directly in an external system.
        you can use this function in collect_resource_index
        function to create the resuorce index graph
        """
        raise NotImplementedError

    @classmethod
    def parsed_output(
        cls,
        export_output_path,
        logger=None,
    ):
        """
        Parse and return the analysis results from the output file.

        Override this method if the tool generates an output file that
        requires parsing, such as a JSON file.
        """
        raise NotImplementedError


class ReachabilityPipeline(Pipeline):
    """
    Base pipeline for the vulnerability reachability analysis
    Uses:
       Subclasses must implement ``collect_resource_index``
       and ``collect_and_match_resources`` and define
       the ``reachability_tool`` attribute.
    """

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=symbol_reachability"
    reachability_tool = None

    @classmethod
    def steps(cls):
        return (
            cls.get_vulnerabilities_patches,
            cls.get_candidate_resources,
            cls.collect_resource_index,
            cls.collect_patch_symbols,
            cls.collect_and_match_resources,
            cls.generate_advisory_reachability_report,
            cls.apply_reachability_to_packages_and_dependencies,
        )

    @classmethod
    def get_availability(cls):
        """Return None if this pipeline is available, or a reason string if not."""
        if cls.reachability_tool:
            return cls.reachability_tool.get_availability()
        return None

    def get_vulnerabilities_patches(self):
        """Get unique patch for all vulnerabilities."""
        self.patches = reachability.get_vulnerabilities_patches(
            package_vulnerabilities=self.project.package_vulnerabilities,
            dependency_vulnerabilities=self.project.dependency_vulnerabilities,
        )

    def get_candidate_resources(self):
        """Collect candidate resources your pipeline needs."""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=self.reachability_tool.supported_languages,
        )

    def collect_resource_index(self):
        """
        Collect the resource index, the symbol index of the project resources,
        possibly by running ``self.reachability_tool.run`` on the project. The
        tool generates its analysis of the codebase, typically as a large JSON
        output file, which is then parsed with
        ``self.reachability_tool.parsed_output``; tools that store their
        results directly skip the parsing.

        Return the resource index as a dict or JSON, or store it in
        ``self.resource_indexes``. If the tool does not generate a
        resource index, return None.
        """
        raise NotImplementedError

    def collect_patch_symbols(self):
        """Collect patch symbols for all related commits."""
        self.patch_symbols = reachability.collect_patch_symbols(
            patches=self.patches, logger=self.log
        )

    def collect_and_match_resources(self):
        """
        Match resource symbols against patch symbols,
        and save one reachability report per matching resource.

        Each report is stored in the resource ``extra_data`` under
        the ``symbols_reachability`` key, with the following structure::

            {
                "tool_name": "<tool_name>",
                "patch": {"vcs_url": ..., "commit_hash": ...},
                "advisory_uids": [...],
                "tool_details": [
                    {
                        "symbol_name": ...,
                        "is_defined": ...,
                        ...
                        "reachable_from": [...],
                    },
                ],
                "is_reachable": "yes" | "unknown" | "no",
            }

        Implementations must save reports with
        ``save_resource_reachability_report`` so that re-running the pipeline
        replaces the previous report for the same (vcs_url, commit_hash,
        tool_name)
        """
        raise NotImplementedError

    def generate_advisory_reachability_report(self):
        """Generate a reachability report summarizing status by advisory."""
        self.advisories_reachability_report = (
            reachability.generate_advisory_reachability_report(
                project=self.project,
                patches=self.patches,
                candidate_resources=self.candidate_resources,
            )
        )

    def apply_reachability_to_packages_and_dependencies(self):
        """
        Save reachability results by updating DiscoveredPackage and
        DiscoveredDependency records with the computed reachability data
        in their affected_by_vulnerabilities JSON field.
        """
        reachability.apply_reachability_to_packages_and_dependencies(
            project=self.project, advisory_report=self.advisories_reachability_report
        )

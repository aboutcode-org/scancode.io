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
import tempfile

from git import Repo

from scanpipe.pipelines import Pipeline
from scanpipe.pipes.reachability import PatchAnalyzer
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import ResourceAnalyzer
from scanpipe.pipes.reachability import ResourcePatchMatcher
from scanpipe.pipes.reachability import add_reachability_report
from scanpipe.pipes.reachability import classify_reachability
from scanpipe.pipes.reachability import normalize_text


class SymbolReachability(Pipeline):
    """
    Patch reachability analysis for given vulnerability patches.

    For every patch we clone the git repository and extract
    the vulnerable and fixed symbols from the patch commit.

    These symbols are then matched against the project's codebase resources to
    determine if the vulnerable code is actually present and reachable.

    The analysis checks if vulnerable symbols are defined, imported, called, or
    exactly match a fingerprint within the project files. The results, including
    tool_details and a reachability status (REACHABLE, UNKNOWN, or
    NOT_REACHABLE), are stored in the `extra_data` of the matching resources
    under the `symbols_reachability` key.

    Finally, a summary report is generated for each vulnerability
    advisory and saved as a JSON output file.
    """

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/resources/?extra_data=symbol_reachability"

    @classmethod
    def steps(cls):
        return (
            cls.get_vulnerabilities_patches,
            cls.collect_resource_index,
            cls.collect_patch_symbols,
            cls.collect_and_match_resources,
            cls.generate_advisory_reachability_report,
        )

    def get_vulnerabilities_patches(self):
        """Get unique patch for all vulnerabilities."""
        patches = {}
        for vulnerability in (
            self.project.package_vulnerabilities
            + self.project.dependency_vulnerabilities
        ):
            advisory_uid = vulnerability.get("advisory_uid")
            for patch in vulnerability.get("fixed_in_patches", []):
                vcs_url = patch.get("vcs_url")
                commit_hash = patch.get("commit_hash")

                p_key = (vcs_url, commit_hash)
                if p_key not in patches:
                    patches[p_key] = {
                        "vcs_url": vcs_url,
                        "commit_hash": commit_hash,
                        "advisory_uids": [],
                    }

                if advisory_uid and advisory_uid not in patches[p_key]["advisory_uids"]:
                    patches[p_key]["advisory_uids"].append(advisory_uid)

        self.patches = list(patches.values())

    def collect_resource_index(self):
        """Collect resources symbols for each resource exactly once."""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False, is_archive=False, is_media=False
        )
        self.resource_indexes = {}
        for resource in self.candidate_resources:
            resource_language = resource.programming_language

            file_content = normalize_text(resource.file_content)
            if not file_content:
                continue

            resource_analyzer = ResourceAnalyzer(
                resource_text=file_content, language=resource_language
            )

            resource_index = resource_analyzer.build_index()
            if resource_index:
                self.resource_indexes[resource.path] = resource_index

    def collect_patch_symbols(self):
        """
        For each unique repo: clone it once, collect patch symbols for all
        related commits, then remove the local clone before moving on
        """
        self.patch_symbols = {}
        patches_by_repo = {}
        for patch in self.patches:
            vcs_url = patch.get("vcs_url")
            patches_by_repo.setdefault(vcs_url, []).append(patch)

        for vcs_url, repo_patches in patches_by_repo.items():
            with tempfile.TemporaryDirectory(
                prefix="symbol-reachability-"
            ) as repo_path:
                try:
                    repo = Repo.clone_from(vcs_url, repo_path)
                except Exception as e:
                    raise Exception(f"Failed to clone repository {vcs_url}: {e!r}")

                try:
                    for patch in repo_patches:
                        commit_hash = patch.get("commit_hash")
                        patch_analyzer = PatchAnalyzer(
                            repo=repo, commit_hash=commit_hash
                        )
                        self.patch_symbols[commit_hash] = (
                            patch_analyzer.collect_patch_symbols()
                        )
                except Exception as e:
                    raise Exception(
                        f"Failed to collect patch symbols "
                        f"for {vcs_url}, patch: {repo_patches}: {e!r}"
                    )

    def collect_and_match_resources(self):
        """Match resource symbols against patch symbols."""
        for patch in self.patches:
            vcs_url = patch.get("vcs_url")
            commit_hash = patch.get("commit_hash")
            advisory_uids = patch.get("advisory_uids", [])

            patch_symbols_by_language = self.patch_symbols.get(commit_hash, {})
            if not patch_symbols_by_language:
                continue

            for resource in self.candidate_resources:
                resource_index = self.resource_indexes.get(resource.path)
                if not resource_index:
                    continue

                patch_symbols = patch_symbols_by_language.get(
                    resource.programming_language
                )
                if not patch_symbols:
                    continue

                vulnerable_symbols = patch_symbols.get("vulnerable", {})
                fixed_symbols = patch_symbols.get("fixed", {})

                matcher = ResourcePatchMatcher(resource_index=resource_index)
                vuln_details = matcher.match(vulnerable_symbols)
                fixed_details = matcher.match(fixed_symbols)

                if not any([vuln_details, fixed_details]):
                    continue

                report = {
                    "patch": {
                        "vcs_url": vcs_url,
                        "commit_hash": commit_hash,
                    },
                    "advisory_uids": advisory_uids,
                    "tool_details": list(vuln_details.values()),
                    "fixed_symbols": sorted(fixed_details.keys()),
                    "vulnerable_symbols": sorted(vuln_details.keys()),
                    "is_reachable": classify_reachability(vuln_details).value,
                }

                add_reachability_report(
                    resource=resource,
                    commit_hash=commit_hash,
                    vcs_url=vcs_url,
                    new_report=report,
                )

    def generate_advisory_reachability_report(self):
        """
        Generate reachability report keyed by advisory_uid.

        Each advisory contains its overall reachability status
        and the reachability results collected from all resources
        and associated patches.

        The overall reachability status is determined using the following
        priority order: REACHABLE > UNKNOWN > NOT_REACHABLE

        This means that an advisory is considered reachable if it is reachable
        through at least one resource or patch. If no reachable result exists,
        but at least one result is unknown, the advisory status is UNKNOWN.
        Otherwise, it is NOT_REACHABLE.
        """
        status_priority = {
            ReachabilityStatus.REACHABLE.value: 3,
            ReachabilityStatus.UNKNOWN.value: 2,
            ReachabilityStatus.NOT_REACHABLE.value: 1,
        }

        advisory_reachability_report = {
            "purl": self.project.purl,
            "advisories": [],
        }

        advisory_map = {}
        for patch in self.patches:
            for adv_uid in patch.get("advisory_uids", []):
                if adv_uid not in advisory_map:
                    adv_data = {
                        "advisory_uid": adv_uid,
                        "is_reachable": ReachabilityStatus.NOT_REACHABLE.value,
                        "details": [],
                    }
                    advisory_map[adv_uid] = adv_data
                    advisory_reachability_report["advisories"].append(adv_data)

        for resource in self.candidate_resources:
            for report in resource.extra_data.get("symbols_reachability", []):
                advisory_uids = report.get("advisory_uids", [])
                is_reachable = report.get("is_reachable")
                patch = report.get("patch", {})

                for adv_uid in advisory_uids:
                    if adv_uid not in advisory_map:
                        adv_data = {
                            "advisory_uid": adv_uid,
                            "is_reachable": ReachabilityStatus.NOT_REACHABLE.value,
                            "details": [],
                        }
                        advisory_map[adv_uid] = adv_data
                        advisory_reachability_report["advisories"].append(adv_data)

                    tool_details = {
                        "resource_path": resource.path,
                        "patch": patch,
                        "is_reachable": is_reachable,
                        "tool_details": report.get("tool_details", []),
                        "vulnerable_symbols": report.get("vulnerable_symbols", []),
                        "fixed_symbols": report.get("fixed_symbols", []),
                    }

                    advisory_map[adv_uid]["details"].append(tool_details)

                    current_status = advisory_map[adv_uid]["is_reachable"]
                    if status_priority.get(is_reachable, 0) > status_priority.get(
                        current_status, 0
                    ):
                        advisory_map[adv_uid]["is_reachable"] = is_reachable

        reachability_output_path = self.project.get_output_file_path(
            "reachability", "json"
        )

        with open(reachability_output_path, "w") as f:
            json.dump(advisory_reachability_report, f, indent=2)

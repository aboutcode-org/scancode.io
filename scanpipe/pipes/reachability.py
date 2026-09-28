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

import difflib
import json
import shutil
import tempfile
from enum import Enum
from pathlib import Path

from git import Repo
from git.diff import NULL_TREE
from typecode import get_type

from aboutcode.pipeline import LoopProgress
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.pipes.symbols import TS_QUERIES
from scanpipe.pipes.symbols import SymbolExtractor
from scanpipe.pipes.symbols import create_sha256_fingerprint
from scanpipe.pipes.symbols import is_supported_language


class ReachabilityStatus(str, Enum):
    REACHABLE = "yes"
    UNKNOWN = "unknown"
    NOT_REACHABLE = "no"


def normalize_text(content):
    """Normalize content (bytes) into a UTF-8 decoded string."""
    if content is None:
        return ""

    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)


def detect_language_with_scancode(file_path, content):
    """Detect the programming language of the text"""
    content = normalize_text(content)

    if not content:
        return None

    tmp_dir = tempfile.mkdtemp(prefix="patch-lang-")

    try:
        location = Path(tmp_dir) / Path(file_path).name
        location.write_text(content, encoding="utf-8", errors="replace")

        info = get_type(location)
        return info.programming_language or None

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class PatchAnalyzer:
    def __init__(self, repo, commit_hash):
        self.repo = repo
        self.commit = repo.commit(commit_hash)
        self.parent_commit = self.commit.parents[0] if self.commit.parents else None

    def get_changed_files(self):
        """
        Retrieve all files changed by the commit along with their
        vulnerable and fixed contents.

        For each changed file, a dictionary entry is created with two
        keys:

        - vulnerable_text: The file content before the commit (empty
          string for newly added files).
        - fixed_text: The file content after the commit (empty string
          for deleted files).

        """
        diffs = (
            self.parent_commit.diff(self.commit, create_patch=False)
            if self.parent_commit
            else self.commit.diff(NULL_TREE, create_patch=False)
        )

        files = {}
        for diff in diffs:
            change_type = diff.change_type
            old_path = diff.a_path if change_type in ("D", "M", "R") else None
            new_path = diff.b_path if change_type in ("A", "M", "R") else None
            path_key = new_path or old_path

            if not path_key:
                continue

            entry = files.setdefault(
                path_key, {"vulnerable_text": "", "fixed_text": ""}
            )

            if old_path and self.parent_commit:
                entry["vulnerable_text"] = (
                    (self.parent_commit.tree / old_path)
                    .data_stream.read()
                    .decode("utf-8", errors="replace")
                )

            if new_path:
                entry["fixed_text"] = (
                    (self.commit.tree / new_path)
                    .data_stream.read()
                    .decode("utf-8", errors="replace")
                )

        return files

    def get_commit_diff_text(self):
        """Get the diff text, falling back to an empty tree if no parent exists."""
        base = self.parent_commit.hexsha if self.parent_commit else NULL_TREE
        return self.repo.git.diff(base, self.commit.hexsha, unified=3)

    @classmethod
    def compute_changed_lines(cls, vulnerable_text, fixed_text):
        """Return the removed and added line numbers between two file contents."""
        matcher = difflib.SequenceMatcher(
            a=vulnerable_text.splitlines(),
            b=fixed_text.splitlines(),
            autojunk=False,  # otherwise difflib ignores lines that repeat often
        )

        removed_lines = []
        added_lines = []
        for tag, vuln_start, vuln_end, fixed_start, fixed_end in matcher.get_opcodes():
            if tag == "equal":
                continue
            # opcodes are 0-based and end-exclusive, line numbers are 1-based
            removed_lines.extend(range(vuln_start + 1, vuln_end + 1))
            added_lines.extend(range(fixed_start + 1, fixed_end + 1))

        return removed_lines, added_lines

    @classmethod
    def diff_changed_symbols(cls, vuln_meta, fixed_meta):
        """
        Compare the vulnerable and fixed symbol metadata and return the
        symbols that are unique to each side (i.e., whose body text
        differs between the two versions).

        A symbol key is considered "vulnerable-only" if its body text
        does not match the corresponding symbol in fixed_meta, and
        vice versa.
        """
        vuln_only = {
            key: metadata
            for key, metadata in vuln_meta.items()
            if fixed_meta.get(key, {}).get("text") != metadata["text"]
        }
        fixed_only = {
            key: metadata
            for key, metadata in fixed_meta.items()
            if vuln_meta.get(key, {}).get("text") != metadata["text"]
        }
        return vuln_only, fixed_only

    def collect_patch_symbols(self):
        """
        Collect all changed symbols across every file modified by the
        commit, grouped by programming language.

        For each changed file, the analyzer:
        - Retrieves the vulnerable and fixed file contents.
        - Computes which lines were removed and added.
        - Extracts symbols that intersect those changed lines using
           Tree-sitter parsing SymbolExtractor
        - Diffs the extracted symbols to find those whose body text
           actually changed.
        - Buckets the results by programming language.
        """
        by_language = {}
        changed_files = self.get_changed_files()

        for file_path, texts in changed_files.items():
            vulnerable_text = texts["vulnerable_text"]
            fixed_text = texts["fixed_text"]
            removed_lines, added_lines = self.compute_changed_lines(
                vulnerable_text, fixed_text
            )

            vuln_meta, fixed_meta, language = self.analyze(
                vulnerable_text=vulnerable_text,
                fixed_text=fixed_text,
                removed_lines=removed_lines,
                added_lines=added_lines,
                file_path=file_path,
            )

            if not language or not (vuln_meta or fixed_meta):
                continue

            language_bucket = by_language.setdefault(
                language, {"vulnerable": {}, "fixed": {}}
            )

            language_bucket["vulnerable"].update(
                {f"{file_path}::{key}": metadata for key, metadata in vuln_meta.items()}
            )
            language_bucket["fixed"].update(
                {
                    f"{file_path}::{key}": metadata
                    for key, metadata in fixed_meta.items()
                }
            )

        return by_language

    @classmethod
    def build_symbol_metadata(cls, nodes, extractor):
        """
        Build metadata dictionaries for a list of Tree-sitter AST nodes
        representing changed symbols.

        For each node, the qualified name, body text, SHA-256 fingerprint,
        and start/end line numbers are extracted and stored in a
        dictionary keyed by the qualified name. If duplicate qualified
        names are encountered, a numeric suffix is appended to disambiguate.
        """
        if not nodes or not extractor:
            return {}

        index = extractor.extract_definitions_index()

        metadata = {}
        name_counts = {}
        for node in nodes:
            qualified_name = extractor._build_qualified_name(node, index)
            if not qualified_name:
                continue

            body_text = node.text.decode("utf-8", errors="replace")
            fingerprints = create_sha256_fingerprint(body_text)

            count = name_counts[qualified_name] = name_counts.get(qualified_name, 0) + 1
            key = qualified_name if count == 1 else f"{qualified_name}#{count}"

            metadata[key] = {
                "qualified_name": qualified_name,
                "text": body_text,
                "fingerprint": fingerprints,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "node_type": node.type,
            }
        return metadata

    @classmethod
    def analyze(
        cls, vulnerable_text, fixed_text, removed_lines, added_lines, file_path
    ):
        """
        Analyze the vulnerable and fixed versions of a single file to
        extract changed symbols.

        The method performs the following steps:

        - Detects the programming language of the file (using the
          fixed version first, falling back to the vulnerable version).
        - Verifies the language is supported by Tree-sitter queries.
        - Parses both versions into ASTs using Tree-sitter.
        - Extracts symbols whose line ranges intersect the removed
          lines (vulnerable side) or added lines (fixed side).
        - Builds metadata for each set of changed symbols.
        - Diffs the two metadata sets to find symbols whose body text
          actually changed between versions.

        """
        vulnerable_text = normalize_text(vulnerable_text)
        fixed_text = normalize_text(fixed_text)

        language = detect_language_with_scancode(
            file_path, fixed_text
        ) or detect_language_with_scancode(file_path, vulnerable_text)

        if not is_supported_language(language):
            return {}, {}, language

        lang_query = TS_QUERIES[language]()

        vuln_tree, _ = (
            lang_query.parse_code_to_ast(code_text=vulnerable_text)
            if vulnerable_text
            else (None, None)
        )
        fixed_tree, _ = (
            lang_query.parse_code_to_ast(code_text=fixed_text)
            if fixed_text
            else (None, None)
        )

        if vuln_tree is None and fixed_tree is None:
            return {}, {}, language

        vuln_meta_all = {}
        fixed_meta_all = {}

        if vuln_tree:
            vuln_extractor = SymbolExtractor(
                lang_query=lang_query, root_node=vuln_tree.root_node
            )
            vuln_nodes = vuln_extractor.extract_changed_symbols(
                changed_lines=removed_lines
            )
            vuln_meta_all = cls.build_symbol_metadata(
                nodes=vuln_nodes, extractor=vuln_extractor
            )

        if fixed_tree:
            fixed_extractor = SymbolExtractor(
                lang_query=lang_query, root_node=fixed_tree.root_node
            )
            fixed_nodes = fixed_extractor.extract_changed_symbols(
                changed_lines=added_lines
            )
            fixed_meta_all = cls.build_symbol_metadata(
                nodes=fixed_nodes, extractor=fixed_extractor
            )

        vuln_meta, fixed_meta = cls.diff_changed_symbols(
            vuln_meta=vuln_meta_all, fixed_meta=fixed_meta_all
        )
        return vuln_meta, fixed_meta, language


def classify_reachability(tool_details):
    """
    Classify the reachability status of a vulnerability based on the
    collected tool_details from ResourcePatchMatcher.
    """
    if not tool_details:
        return ReachabilityStatus.NOT_REACHABLE

    status = ReachabilityStatus.NOT_REACHABLE
    for item in tool_details.values():
        is_called = bool(item.get("is_called"))
        has_path = bool(item.get("reachable_from"))
        is_defined = bool(item.get("is_defined"))
        is_imported = bool(item.get("is_imported"))
        is_exact = bool(item.get("is_exact"))

        if is_exact or (is_imported and (is_called or has_path)):
            return ReachabilityStatus.REACHABLE

        if (is_imported or is_defined) and not is_exact:
            status = ReachabilityStatus.UNKNOWN

    return status


class ResourceAnalyzer:
    def __init__(self, resource_text, language):
        self.resource_text = normalize_text(resource_text)
        self.language = language

    def process_node(
        self, node, extractor, definitions_index, definitions, fingerprints
    ):
        """
        Process a single AST node to extract its qualified name, add it
        to the definitions set, compute its fingerprint, and add the
        fingerprint to the fingerprints set.
        """
        qualified_name = extractor._build_qualified_name(node, definitions_index)
        if not qualified_name:
            return None

        definitions.add(qualified_name)
        body_text = node.text.decode("utf-8", errors="replace")
        fingerprint = create_sha256_fingerprint(body_text)

        if fingerprint:
            fingerprints.add(fingerprint)

        return qualified_name

    def build_index(self):
        """
        Build the full symbol index for the resource by parsing it
        with Tree-sitter and extracting all definitions, fingerprints,
        imports, and the reverse call graph.

        The method iterates over all functions, classes, and constants
        in the resource's AST. For functions, it also extracts call
        expressions to populate the callers_of reverse call graph.
        """
        if not is_supported_language(self.language) or not self.resource_text:
            return None

        lang_query = TS_QUERIES[self.language]()
        tree, _ = lang_query.parse_code_to_ast(self.resource_text)

        if tree is None:
            return None

        extractor = SymbolExtractor(lang_query=lang_query, root_node=tree.root_node)
        definitions_index = extractor.extract_definitions_index()
        imports_map = extractor.extract_imports()
        separator = extractor.syntax_config.get("separator", ".")

        definitions = set()
        fingerprints = set()
        callers_of = {}  # callee_name -> set of caller_qualified_names

        for node, _ in lang_query.get_functions(tree.root_node):
            self.process_node(
                node, extractor, definitions_index, definitions, fingerprints
            )

        for node, _ in lang_query.get_classes(tree.root_node):
            self.process_node(
                node, extractor, definitions_index, definitions, fingerprints
            )

        for node, _ in lang_query.get_constants(tree.root_node):
            self.process_node(
                node, extractor, definitions_index, definitions, fingerprints
            )

        for receiver_node, callee_node in lang_query.get_calls(tree.root_node):
            callee_name = callee_node.text.decode("utf-8", errors="replace")
            if not callee_name:
                continue

            caller_name = None
            curr = callee_node
            while curr is not None:
                def_info = definitions_index.get(curr.id)
                if def_info and def_info.get("qualified_name"):
                    caller_name = def_info["qualified_name"]
                    break
                curr = curr.parent

            callers_of.setdefault(callee_name, set()).add(caller_name)

        return {
            "definitions": definitions,
            "fingerprints": fingerprints,
            "imports": imports_map,
            "callers_of": callers_of,
            "separator": separator,
        }


class ResourcePatchMatcher:
    def __init__(self, resource_index):
        self.resource_index = resource_index
        self.definitions = resource_index.get("definitions", set())
        self.fingerprints = resource_index.get("fingerprints", set())
        self.imports = resource_index.get("imports", {})
        self.callers_of = resource_index.get("callers_of", {})
        self.separator = resource_index.get("separator", ".")
        self.wildcard_modules = self.imports.get("*", [])

    def _matches_first_component(
        self, qualified_name, abs_path, local_name, import_call_names
    ):
        """
        Check if the first component of qualified_name
        matches the end of abs_path.
        """
        first_component = qualified_name.split(self.separator, 1)[0]
        if first_component != qualified_name and (
            abs_path.endswith(self.separator + first_component)
            or abs_path == first_component
        ):
            remaining = qualified_name[len(first_component) :]
            import_call_names.add(f"{local_name}{remaining}")
            return True
        return False

    def _matches_wildcard(self, qualified_name):
        """Check if the qualified_name is covered by a wildcard import."""
        return any(
            qualified_name == mod or qualified_name.startswith(mod + self.separator)
            for mod in self.wildcard_modules
        )

    def _get_import_info(self, qualified_name):
        """Check if qualified_name is imported and return possible call names."""
        import_call_names = set()
        imported = False

        for local_name, abs_path in self.imports.items():
            if local_name == "*":
                continue

            if qualified_name in (local_name, abs_path):
                imported = True
                import_call_names.add(local_name)
            elif qualified_name.startswith(local_name + self.separator):
                imported = True
                import_call_names.add(qualified_name)
            elif qualified_name.startswith(abs_path + self.separator):
                imported = True
                remaining = qualified_name[len(abs_path) :]
                import_call_names.add(f"{local_name}{remaining}")
            elif abs_path.endswith(self.separator + qualified_name):
                imported = True
                import_call_names.add(local_name)
            elif self._matches_first_component(
                qualified_name, abs_path, local_name, import_call_names
            ):
                imported = True

        if not imported and self._matches_wildcard(qualified_name):
            return True, import_call_names

        return imported, import_call_names

    def match(self, patch_symbols_metadata):
        """
        Match a set of patch symbols against the resource index and
        return tool_details for each matched symbol.
        """
        if not patch_symbols_metadata or not self.resource_index:
            return {}

        matched = {}
        for metadata in patch_symbols_metadata.values():
            qualified_name = metadata["qualified_name"]
            fingerprint = metadata["fingerprint"]
            defined = qualified_name in self.definitions
            is_exact = bool(
                fingerprint
                and fingerprint in self.fingerprints
                and qualified_name in self.definitions
            )
            short_name = (
                qualified_name.rsplit(self.separator, 1)[-1]
                if self.separator in qualified_name
                else qualified_name
            )

            imported, import_call_names = self._get_import_info(qualified_name)

            possible_call_names = {qualified_name}
            if imported or defined:
                possible_call_names.add(short_name)
            possible_call_names.update(import_call_names)

            callers = set()
            for call_name in possible_call_names:
                callers.update(self.callers_of.get(call_name, set()))

            called = bool(callers) and (
                imported or defined or bool(self.wildcard_modules)
            )
            if called and not imported and not defined and self.wildcard_modules:
                imported = True

            if not (defined or is_exact or called or imported):
                continue

            entry = matched.setdefault(
                qualified_name,
                {
                    "symbol_name": qualified_name,
                    "is_called": False,
                    "is_defined": False,
                    "is_imported": False,
                    "is_exact": False,
                    "reachable_from": [],
                },
            )

            entry["is_defined"] = entry["is_defined"] or defined
            entry["is_imported"] = entry["is_imported"] or imported
            entry["is_exact"] = entry["is_exact"] or is_exact
            entry["is_called"] = entry["is_called"] or called
            if called:
                entry["reachable_from"] = sorted([c for c in callers if c is not None])

        return matched


def save_resource_reachability_report(resource, commit_hash, vcs_url, new_report):
    """
    Save a reachability report for commit_hash and vcs_url.
    If duplicates exist, replace the old report with the new one.
    """
    cleaned_reports = []
    replaced = False

    old_reports = resource.extra_data.get("symbols_reachability", [])
    for old_report in old_reports:
        patch_info = old_report.get("patch", {})
        old_commit_hash = patch_info.get("commit_hash")
        old_vcs_url = patch_info.get("vcs_url")

        if old_commit_hash == commit_hash and old_vcs_url == vcs_url:
            if not replaced:
                cleaned_reports.append(new_report)
                replaced = True
            # Skip old duplicate
        else:
            cleaned_reports.append(old_report)

    if not replaced:
        cleaned_reports.append(new_report)

    resource.update_extra_data({"symbols_reachability": cleaned_reports})


def get_vulnerabilities_patches(package_vulnerabilities, dependency_vulnerabilities):
    """Get unique patch for all vulnerabilities."""
    patches = {}
    for vulnerability in package_vulnerabilities + dependency_vulnerabilities:
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

    return list(patches.values())


def collect_resource_index(candidate_resources, logger=None):
    """Collect resources symbols for each resource"""
    resource_indexes = {}
    resources_count = len(candidate_resources)
    progress = LoopProgress(resources_count, logger)
    for resource in progress.iter(candidate_resources):
        resource_language = resource.programming_language

        file_content = normalize_text(resource.file_content)
        if not file_content:
            continue

        resource_analyzer = ResourceAnalyzer(
            resource_text=file_content, language=resource_language
        )

        resource_index = resource_analyzer.build_index()
        if resource_index:
            resource_indexes[resource.path] = resource_index

    return resource_indexes


def collect_patch_symbols(patches, logger=None):
    """
    For each unique repo clone it once,
    collect patch symbols for all related commits
    """
    patch_symbols = {}
    patches_by_repo = {}
    for patch in patches:
        vcs_url = patch.get("vcs_url")
        patches_by_repo.setdefault(vcs_url, []).append(patch)

    repo_count = len(patches_by_repo)
    repo_progress = LoopProgress(repo_count, logger)
    for vcs_url, repo_patches in repo_progress.iter(patches_by_repo.items()):
        with tempfile.TemporaryDirectory(prefix="symbol-reachability-") as repo_path:
            try:
                repo = Repo.clone_from(vcs_url, repo_path)
            except Exception as e:
                raise Exception(f"Failed to clone repository {vcs_url}: {e!r}")

            try:
                for patch in repo_patches:
                    commit_hash = patch.get("commit_hash")
                    patch_analyzer = PatchAnalyzer(repo=repo, commit_hash=commit_hash)
                    patch_symbols[commit_hash] = patch_analyzer.collect_patch_symbols()
            except Exception as e:
                raise Exception(
                    f"Failed to collect patch symbols "
                    f"for {vcs_url}, patch: {repo_patches}: {e!r}"
                )

    return patch_symbols


def match_patches_to_resources(
    patches, patch_symbols, candidate_resources, resource_indexes, logger=None
):
    """Match resource symbols against patch symbols."""
    patches_count = len(patches)
    patch_progress = LoopProgress(patches_count, logger=logger)
    for patch in patch_progress.iter(patches):
        vcs_url = patch.get("vcs_url")
        commit_hash = patch.get("commit_hash")
        advisory_uids = patch.get("advisory_uids", [])

        patch_symbols_by_language = patch_symbols.get(commit_hash, {})
        if not patch_symbols_by_language:
            continue

        for resource in candidate_resources:
            resource_index = resource_indexes.get(resource.path)
            if not resource_index:
                continue

            lang_patch_symbols = patch_symbols_by_language.get(
                resource.programming_language
            )
            if not lang_patch_symbols:
                continue

            vulnerable_symbols = lang_patch_symbols.get("vulnerable", {})
            fixed_symbols = lang_patch_symbols.get("fixed", {})

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

            save_resource_reachability_report(
                resource=resource,
                commit_hash=commit_hash,
                vcs_url=vcs_url,
                new_report=report,
            )


def generate_advisory_reachability_report(project, patches, candidate_resources):
    """
    Generate a reachability report summarizing status by advisory.

    Each advisory contains its overall reachability status
    and the reachability results collected from all resources
    and associated patches.

    The overall reachability status is determined using the following
    priority order: REACHABLE: "yes" > UNKNOWN: "unknown" > NOT_REACHABLE: "no"

    This means that an advisory is considered reachable if it is reachable
    through at least one resource or patch. If no reachable result exists,
    but at least one result is UNKNOWN, the advisory status is UNKNOWN.
    Otherwise, it is NOT_REACHABLE.
    """
    status_priority = {
        ReachabilityStatus.REACHABLE.value: 3,
        ReachabilityStatus.UNKNOWN.value: 2,
        ReachabilityStatus.NOT_REACHABLE.value: 1,
    }

    advisories_reachability_report = {
        "purl": project.purl,
        "advisories": [],
    }

    advisory_map = {}
    for patch in patches:
        for adv_uid in patch.get("advisory_uids", []):
            if adv_uid not in advisory_map:
                adv_data = {
                    "advisory_uid": adv_uid,
                    "is_reachable": ReachabilityStatus.NOT_REACHABLE.value,
                    "details": [],
                }
                advisory_map[adv_uid] = adv_data
                advisories_reachability_report["advisories"].append(adv_data)

    for resource in candidate_resources:
        for report in resource.extra_data.get("symbols_reachability", []):
            advisory_uids = report.get("advisory_uids", [])
            is_reachable = (
                report.get("is_reachable") or ReachabilityStatus.NOT_REACHABLE.value
            )
            patch = report.get("patch", {})

            for adv_uid in advisory_uids:
                if adv_uid not in advisory_map:
                    adv_data = {
                        "advisory_uid": adv_uid,
                        "is_reachable": ReachabilityStatus.NOT_REACHABLE.value,
                        "details": [],
                    }
                    advisory_map[adv_uid] = adv_data
                    advisories_reachability_report["advisories"].append(adv_data)

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

    reachability_output_path = project.get_output_file_path("reachability", "json")

    with open(reachability_output_path, "w") as f:
        json.dump(advisories_reachability_report, f, indent=2)

    return advisories_reachability_report


def inject_reachability_data(vulns, advisory_map):
    """
    Inject reachability data into a list of vulnerabilities.
    Returns True if any vulnerability was updated, False otherwise.
    """
    updated = False
    for vuln in vulns:
        adv_uid = vuln.get("advisory_uid")
        if adv_uid in advisory_map:
            adv_data = advisory_map[adv_uid]
            vuln["is_reachable"] = adv_data.get("is_reachable", "unknown")
            vuln["reachability_analysis"] = adv_data.get("details", [])
            updated = True

    return updated


def apply_reachability_to_packages_and_dependencies(project, advisory_report):
    """
    Update DiscoveredPackage and DiscoveredDependency records by injecting the
    computed reachability data into their affected_by_vulnerabilities JSON field.
    """
    advisories = advisory_report.get("advisories", [])
    if not advisories:
        return

    advisory_map = {adv["advisory_uid"]: adv for adv in advisories}
    targets = (
        (project.discoveredpackages.all(), DiscoveredPackage),
        (project.discovereddependencies.all(), DiscoveredDependency),
    )

    for queryset, model in targets:
        unsaved = [
            item
            for item in queryset
            if inject_reachability_data(
                item.affected_by_vulnerabilities or [], advisory_map
            )
        ]
        if unsaved:
            model.objects.bulk_update(
                objs=unsaved,
                fields=["affected_by_vulnerabilities"],
                batch_size=10,
            )

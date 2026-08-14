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
import shutil
import tempfile
from enum import Enum
from pathlib import Path

from git import Repo
from git.diff import NULL_TREE
from scancode.api import get_file_info

from scanpipe.pipes.symbols import TS_QUERIES
from scanpipe.pipes.symbols import SymbolExtractor
from scanpipe.pipes.symbols import create_sha256_fingerprint
from scanpipe.pipes.symbols import is_supported_language


class ReachabilityStatus(str, Enum):
    REACHABLE = "YES"
    UNKNOWN = "UNKNOWN"
    NOT_REACHABLE = "NO"


def normalize_text(content):
    """Normalize content (bytes) into a UTF-8 decoded string."""
    if content is None:
        return ""

    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)


def detect_language_with_scancode(file_path, content):
    """
    Detect the programming language of the text
    content using get_file_info function
    """
    content = normalize_text(content)

    if not content:
        return None

    tmp_dir = tempfile.mkdtemp(prefix="patch-lang-")

    try:
        target = Path(tmp_dir) / Path(file_path).name
        target.write_text(content, encoding="utf-8", errors="replace")

        info = get_file_info(location=str(target)) or {}
        return info.get("programming_language") or None

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class PatchAnalyzer:
    def __init__(self, repo: Repo, commit_hash):
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


def classify_reachability(evidence):
    """
    Classify the reachability status of a vulnerability based on the
    collected evidence from :class:`ResourcePatchMatcher`.
    """
    if not evidence:
        return ReachabilityStatus.NOT_REACHABLE

    status = ReachabilityStatus.NOT_REACHABLE
    for item in evidence.values():
        is_called = bool(item.get("called"))
        has_path = bool(item.get("reachable_from"))
        is_defined = bool(item.get("defined"))
        is_imported = bool(item.get("imported"))
        is_exact = bool(item.get("fingerprint"))

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
            qualified_name = self.process_node(
                node, extractor, definitions_index, definitions, fingerprints
            )
            if qualified_name:
                for _, callee_name in extractor.extract_calls(node):
                    callers_of.setdefault(callee_name, set()).add(qualified_name)

        for node, _ in lang_query.get_classes(tree.root_node):
            self.process_node(
                node, extractor, definitions_index, definitions, fingerprints
            )

        for node, _ in lang_query.get_constants(tree.root_node):
            self.process_node(
                node, extractor, definitions_index, definitions, fingerprints
            )

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

    def match(self, patch_symbols_metadata):
        """
        Match a set of patch symbols against the resource index and
        return evidence for each matched symbol.

        For each symbol in patch_symbols_metadata, the method
        checks whether it is defined, imported, called, or has an
        exact fingerprint match in the resource. If at least one of
        these conditions is true, an evidence entry is created.
        """
        if not patch_symbols_metadata or not self.resource_index:
            return {}

        matched = {}
        for metadata in patch_symbols_metadata.values():
            qualified_name = metadata["qualified_name"]
            fingerprint = metadata["fingerprint"]

            short_name = (
                qualified_name.rsplit(self.separator, 1)[-1]
                if self.separator in qualified_name
                else qualified_name
            )

            defined = qualified_name in self.definitions
            fingerprint_hit = bool(fingerprint and fingerprint in self.fingerprints)

            imported = (
                qualified_name in self.imports
                or qualified_name in self.imports.values()
            )

            callers = set()
            callers.update(self.callers_of.get(short_name, set()))
            callers.update(self.callers_of.get(qualified_name, set()))
            called = bool(callers)

            if not (defined or fingerprint_hit or called or imported):
                continue

            entry = matched.setdefault(
                qualified_name,
                {
                    "symbol_name": qualified_name,
                    "called": False,
                    "defined": False,
                    "imported": False,
                    "fingerprint": None,
                    "reachable_from": [],
                },
            )

            if defined:
                entry["defined"] = True
            if imported:
                entry["imported"] = True
            if called:
                entry["called"] = True
                entry["reachable_from"] = sorted(callers)

            if fingerprint_hit:
                entry["fingerprint"] = fingerprint

        return matched


def add_reachability_report(resource, commit_hash, vcs_url, new_report):
    """
    Add a reachability report for commit_hash and vcs_url.
    If duplicates exist, replace the old report with the new one.
    """
    cleaned_reports = []
    replaced = False

    old_reports = resource.extra_data.get("symbols_reachability", [])
    for old_report in old_reports:
        actual_report = old_report.get("symbols_reachability", old_report)

        patch_info = actual_report.get("patch", {})
        old_commit_hash = patch_info.get("commit_hash")
        old_vcs_url = patch_info.get("vcs_url")

        if old_commit_hash == commit_hash and old_vcs_url == vcs_url:
            if not replaced:
                cleaned_reports.append(new_report)
                replaced = True
            # Skip old duplicate
        else:
            cleaned_reports.append(actual_report)

    if not replaced:
        cleaned_reports.append(new_report)

    resource.update_extra_data({"symbols_reachability": cleaned_reports})

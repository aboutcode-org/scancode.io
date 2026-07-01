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

import os
import shutil
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

from git import Repo
from git.diff import NULL_TREE
from scancode.api import get_file_info
from unidiff import PatchSet

from scanpipe.pipes.symbols import TS_QUERIES
from scanpipe.pipes.symbols import SymbolExtractor
from scanpipe.pipes.symbols import create_sha256_fingerprint
from scanpipe.pipes.symbols import is_supported_language


class ReachabilityStatus(str, Enum):
    REACHABLE = "REACHABLE"
    POTENTIALLY_REACHABLE = "POTENTIALLY_REACHABLE"
    NOT_REACHABLE = "NOT_REACHABLE"


def normalize_text(content):
    if content is None:
        return ""

    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)


def detect_language_with_scancode(file_path, content):
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


class GitRepositoryContext:
    def __init__(self, vcs_url: str):
        self.vcs_url = vcs_url
        self.repo_path = None
        self._repo = None

    def __enter__(self) -> "GitRepositoryContext":
        self.repo_path = tempfile.mkdtemp(prefix="symbol-reachability-")
        try:
            self._repo = Repo.clone_from(self.vcs_url, self.repo_path)
            return self
        except Exception as exc:
            self._cleanup()
            raise ValueError(f"Failed to clone/checkout {self.vcs_url}") from exc

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    @property
    def repo(self) -> Repo:
        return self._repo

    def _cleanup(self):
        if self.repo_path and os.path.exists(self.repo_path):
            shutil.rmtree(self.repo_path, ignore_errors=True)


class PatchAnalyzer:
    EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8b8e6f9b79b4d2b"

    def __init__(self, repo: Repo, commit_hash: str):
        self.repo = repo
        self.commit = repo.commit(commit_hash)
        self.parent_commit = self.commit.parents[0] if self.commit.parents else None

    def get_changed_files(self):
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
        base = self.parent_commit.hexsha if self.parent_commit else self.EMPTY_TREE_SHA
        return self.repo.git.diff(base, self.commit.hexsha, unified=3)

    @classmethod
    def diff_changed_symbols(cls, vuln_meta, fixed_meta):
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

    @classmethod
    def parse_diff_lines(cls, diff_text):
        diff_map = {}
        if not diff_text:
            return diff_map

        for patched_file in PatchSet.from_string(diff_text):
            removed = []
            added = []

            for hunk in patched_file:
                hunk_removed = [
                    line.source_line_no
                    for line in hunk
                    if line.is_removed and line.source_line_no
                ]
                hunk_added = [
                    line.target_line_no
                    for line in hunk
                    if line.is_added and line.target_line_no
                ]

                if hunk_added and not hunk_removed:
                    anchor = max(hunk.source_start, 1)
                    hunk_removed = [anchor]

                if hunk_removed and not hunk_added:
                    anchor = max(hunk.target_start, 1)
                    hunk_added = [anchor]

                removed.extend(hunk_removed)
                added.extend(hunk_added)

            candidates = {
                patched_file.path,
                (patched_file.source_file or "").removeprefix("a/"),
                (patched_file.target_file or "").removeprefix("b/"),
            }

            for candidate in candidates:
                if candidate:
                    diff_map[candidate] = (removed, added)

        return diff_map

    def collect_patch_symbols(self):
        diff_text = self.get_commit_diff_text()
        changed_files = self.get_changed_files()
        diff_line_map = self.parse_diff_lines(diff_text=diff_text)

        by_language = {}
        for file_path, texts in changed_files.items():
            vulnerable_text = texts["vulnerable_text"]
            fixed_text = texts["fixed_text"]
            removed_lines, added_lines = diff_line_map.get(file_path, ([], []))

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
    def build_symbol_metadata(
        cls, nodes, extractor: SymbolExtractor, index: dict = None
    ):
        if not nodes or not extractor:
            return {}

        if index is None:
            index = extractor.extract_definitions_index()

        metadata = {}
        for node in nodes:
            qualified_name = extractor._build_qualified_name(node, index)
            if not qualified_name:
                continue

            body_text = node.text.decode("utf-8", errors="replace")
            fingerprints = create_sha256_fingerprint(body_text)

            key = qualified_name
            suffix = 1
            while key in metadata:
                suffix += 1
                key = f"{qualified_name}#{suffix}"

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
                fixed_nodes, extractor=fixed_extractor
            )

        vuln_meta, fixed_meta = cls.diff_changed_symbols(
            vuln_meta=vuln_meta_all, fixed_meta=fixed_meta_all
        )
        return vuln_meta, fixed_meta, language


def generate_reachability_report(patch, repo, candidate_resources, logger=None):
    vcs_url = patch.get("vcs_url")
    commit_hash = patch.get("commit_hash")

    try:
        patch_analyzer = PatchAnalyzer(repo=repo, commit_hash=commit_hash)
        patch_symbols_by_language = patch_analyzer.collect_patch_symbols()

        if not patch_symbols_by_language:
            return

        for resource in candidate_resources:
            resource_language = resource.programming_language
            patch_symbols = patch_symbols_by_language.get(resource_language)

            if not patch_symbols:
                continue

            file_content = normalize_text(resource.file_content)
            if not file_content:
                continue

            resource_analyzer = ResourceAnalyzer(
                resource_text=file_content, language=resource_language
            )
            resource_index = resource_analyzer.build_index()

            if not resource_index:
                continue

            matcher = ResourcePatchMatcher(resource_index=resource_index)
            vuln_evidence = matcher.match(patch_symbols["vulnerable"])
            fixed_evidence = matcher.match(patch_symbols["fixed"])

            if not any([vuln_evidence, fixed_evidence]):
                continue

            report = {
                "symbols_reachability": {
                    "patch": {
                        "vcs_url": vcs_url,
                        "commit_hash": commit_hash,
                    },
                    "evidence": list(vuln_evidence.values()),
                    "fixed_symbols": sorted(fixed_evidence.keys()),
                    "vulnerable_symbols": sorted(vuln_evidence.keys()),
                    "reachability_status": classify_reachability(vuln_evidence).value,
                }
            }
            print(report)

            existing = resource.extra_data.get("symbols_reachability")
            reports = existing if isinstance(existing, list) else []

            if not any(
                r.get("patch", {}).get("commit_hash") == commit_hash for r in reports
            ):
                reports.append(report)
                resource.update_extra_data({"symbols_reachability": reports})

    except Exception as e:
        if logger:
            logger(
                f"Failed to collect symbol reachability for "
                f"{vcs_url}@{commit_hash}: {e}"
            )


def collect_and_store_symbol_reachability_results(project, logger=None):
    candidate_resources = project.codebaseresources.files().filter(
        is_binary=False, is_archive=False, is_media=False
    )

    for vulnerability in project.package_vulnerabilities:
        patches_by_repo = {}
        for patch in vulnerability.get("fixed_in_patches", []):
            vcs_url = patch.get("vcs_url")
            commit_hash = patch.get("commit_hash")
            if vcs_url and commit_hash:
                patches_by_repo.setdefault(vcs_url, []).append(patch)

        for vcs_url, patches in patches_by_repo.items():
            try:
                with GitRepositoryContext(vcs_url) as git_context:
                    for patch in patches:
                        commit_hash = patch.get("commit_hash")
                        git_context.repo.git.checkout(commit_hash)
                        generate_reachability_report(
                            patch, git_context.repo, candidate_resources, logger
                        )
            except Exception as e:
                if logger:
                    logger(
                        f"Failed to process repository {vcs_url} "
                        f"for symbol reachability: {e}"
                    )


def classify_reachability(evidence):
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
            status = ReachabilityStatus.POTENTIALLY_REACHABLE

    return status


class ResourceAnalyzer:
    def __init__(self, resource_text: str, language: str):
        self.resource_text = normalize_text(resource_text)
        self.language = language

    def process_node(
        self, node, extractor, definitions_index, definitions: set, fingerprints: set
    ) -> str | None:
        """Extract the qualified name, update definitions, and fingerprint"""
        qualified_name = extractor._build_qualified_name(node, definitions_index)
        if not qualified_name:
            return None

        definitions.add(qualified_name)
        body_text = node.text.decode("utf-8", errors="replace")
        fingerprint = create_sha256_fingerprint(body_text)

        if fingerprint:
            fingerprints.add(fingerprint)

        return qualified_name

    def build_index(self) -> dict | None:
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
            # Skip constants defined inside functions, classes, or other blocks
            if node.parent == tree.root_node:
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
    def __init__(self, resource_index: dict):
        self.resource_index = resource_index
        self.definitions = resource_index.get("definitions", set())
        self.fingerprints = resource_index.get("fingerprints", set())
        self.imports = resource_index.get("imports", {})
        self.callers_of = resource_index.get("callers_of", {})
        self.separator = resource_index.get("separator", ".")

    def match(self, patch_symbols_metadata: dict[str, Any]) -> dict[str, Any]:
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

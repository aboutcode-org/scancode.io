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
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any

from git import Repo
from git.diff import NULL_TREE
from git.exc import BadName
from scancode.api import get_file_info
from unidiff import PatchSet

from scanpipe.pipes.symbols import TS_QUERIES
from scanpipe.pipes.symbols import _root_of
from scanpipe.pipes.symbols import collect_definitions
from scanpipe.pipes.symbols import create_sha256_fingerprint
from scanpipe.pipes.symbols import extract_definitions
from scanpipe.pipes.symbols import extract_symbols
from scanpipe.pipes.symbols import get_query
from scanpipe.pipes.symbols import parse_code_to_ast
from scanpipe.pipes.symbols import qualified_name_from_index

EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8b8e6f9b79b4d2b"


class ReachabilityStatus(str, Enum):
    REACHABLE = "REACHABLE"
    POTENTIALLY_REACHABLE = "POTENTIALLY_REACHABLE"
    NOT_REACHABLE = "NOT_REACHABLE"


def api_mocker():
    """TODO: Remove this once the API patch url is done"""
    return [
        {
            "vcs_url": "https://github.com/pallets/flask",
            "commit_hash": "089cb86dd22bff589a4eafb7ab8e42dc357623b4",
        },
        # {
        #     "vcs_url": "https://github.com/aio-libs/aiohttp",
        #     "commit_hash": "0c2e9da51126238a421568eb7c5b53e5b5d17b36",
        # }
    ]


def clone_repo(vcs_url, commit_hash=None):
    repo_path = tempfile.mkdtemp(prefix="symbol-reachability-")

    try:
        repo = Repo.clone_from(vcs_url, repo_path)

        if commit_hash:
            repo.git.checkout(commit_hash)

        return repo_path

    except BadName as exc:
        cleanup_repo(repo_path)
        raise ValueError(f"Commit {commit_hash} not found") from exc

    except Exception:
        cleanup_repo(repo_path)
        raise


def cleanup_repo(repo_path):
    if repo_path and os.path.exists(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)


def normalize_text(content):
    if content is None:
        return ""

    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)


def is_supported_language(language):
    """Return True if the language is supported by tree-sitter queries."""
    return bool(language) and language in TS_QUERIES


def detect_language_with_scancode(file_path, content):
    """
    Write `content` to a temp file preserving `file_path`'s basename
    so the extension is meaningful, then ask ScanCode's `get_file_info`
    to return the programming language.
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


def get_commit_and_parent(repo, commit_hash):
    commit = repo.commit(commit_hash)
    parent = commit.parents[0] if commit.parents else None
    return commit, parent


def get_commit_diff_text(repo, parent_commit, commit):
    """Whole-commit unified diff (used to extract changed line numbers)."""
    base = parent_commit.hexsha if parent_commit else EMPTY_TREE_SHA
    return repo.git.diff(base, commit.hexsha, unified=3)


def get_changed_files(parent_commit, commit):
    """
    Return:
        {
            file_path: {
                "vulnerable_text": "...",
                "fixed_text": "...",
            }
        }

    """
    diffs = (
        parent_commit.diff(commit, create_patch=False)
        if parent_commit
        else commit.diff(NULL_TREE, create_patch=False)
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
            path_key,
            {
                "vulnerable_text": "",
                "fixed_text": "",
            },
        )

        if old_path and parent_commit:
            entry["vulnerable_text"] = (
                (parent_commit.tree / old_path)
                .data_stream.read()
                .decode("utf-8", errors="replace")
            )

        if new_path:
            entry["fixed_text"] = (
                (commit.tree / new_path)
                .data_stream.read()
                .decode("utf-8", errors="replace")
            )

    return files


def get_changed_lines(diff_text, file_path):
    """
    Return `(removed_lines, added_lines)` for one file.

    For pure-insertion hunks (no removed lines) we anchor the vulnerable side
    to the hunk's source location so the enclosing old symbol is still found.
    For pure-deletion hunks we do the mirror image on the added side.
    """
    removed = []
    added = []

    if not diff_text:
        return removed, added

    for patched_file in PatchSet.from_string(diff_text):
        candidates = {
            patched_file.path,
            (patched_file.source_file or "").removeprefix("a/"),
            (patched_file.target_file or "").removeprefix("b/"),
        }
        if file_path not in candidates:
            continue

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

            # Pure insertion: nothing removed -> anchor old side to the
            # line just before the insertion point in the source file.
            if hunk_added and not hunk_removed:
                anchor = max(hunk.source_start, 1)
                hunk_removed = [anchor]

            # Pure deletion: nothing added -> anchor new side similarly.
            if hunk_removed and not hunk_added:
                anchor = max(hunk.target_start, 1)
                hunk_added = [anchor]

            removed.extend(hunk_removed)
            added.extend(hunk_added)

    return removed, added


def diff_changed_symbols(vuln_meta, fixed_meta):
    """
    Keep only symbols whose body actually differs between vulnerable and fixed
    versions. Utilizes the unique suffix keys generated by build_symbol_metadata.
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


def analyze_patched_file(vulnerable_text, fixed_text, diff_text, file_path):
    """
    Return `(vuln_metadata, fixed_metadata, language)` for one changed file,
    restricted to symbols actually touched by the patch.
    """
    vulnerable_text = normalize_text(vulnerable_text)
    fixed_text = normalize_text(fixed_text)

    language = detect_language_with_scancode(
        file_path, fixed_text
    ) or detect_language_with_scancode(file_path, vulnerable_text)

    if not is_supported_language(language):
        return {}, {}, language

    vuln_tree, _ = (
        parse_code_to_ast(vulnerable_text, language)
        if vulnerable_text
        else (None, None)
    )

    fixed_tree, _ = (
        parse_code_to_ast(fixed_text, language) if fixed_text else (None, None)
    )

    if vuln_tree is None and fixed_tree is None:
        return {}, {}, language

    removed_lines, added_lines = get_changed_lines(diff_text, file_path)

    vuln_nodes = (
        extract_symbols(vuln_tree, removed_lines, language) if vuln_tree else []
    )

    fixed_nodes = (
        extract_symbols(fixed_tree, added_lines, language) if fixed_tree else []
    )

    vuln_meta, fixed_meta = diff_changed_symbols(
        build_symbol_metadata(vuln_nodes, language),
        build_symbol_metadata(fixed_nodes, language),
    )

    return vuln_meta, fixed_meta, language


def collect_patch_symbols(repo, commit_hash):
    """
    Return:
        {
            language: {
                "vulnerable": {
                    "file_path::symbol_key": metadata,
                    ...
                },
                "fixed": {
                    "file_path::symbol_key": metadata,
                    ...
                },
            },
            ...
        }

    """
    commit, parent = get_commit_and_parent(repo=repo, commit_hash=commit_hash)
    diff_text = get_commit_diff_text(repo, parent, commit)
    changed = get_changed_files(parent, commit)

    by_language = {}
    for file_path, texts in changed.items():
        vulnerable_text = texts["vulnerable_text"]
        fixed_text = texts["fixed_text"]
        vuln_meta, fixed_meta, language = analyze_patched_file(
            vulnerable_text=vulnerable_text,
            fixed_text=fixed_text,
            diff_text=diff_text,
            file_path=file_path,
        )

        if not language or not (vuln_meta or fixed_meta):
            continue

        language_bucket = by_language.setdefault(
            language,
            {
                "vulnerable": {},
                "fixed": {},
            },
        )

        language_bucket["vulnerable"].update(
            {f"{file_path}::{key}": metadata for key, metadata in vuln_meta.items()}
        )

        language_bucket["fixed"].update(
            {f"{file_path}::{key}": metadata for key, metadata in fixed_meta.items()}
        )

    return by_language


def collect_and_store_symbol_reachability_results(project, logger=None):
    """
    For each known patch commit, determine whether each project codebase
    resource is reachable to the vulnerable code by comparing tree-sitter ASTs
    of the patch versus the resource.
    """
    candidate_resources = project.codebaseresources.files().filter(
        is_binary=False,
        is_archive=False,
        is_media=False,
    )

    for patch in api_mocker():
        vcs_url = patch["vcs_url"]
        commit_hash = patch["commit_hash"]
        try:
            # repo_path = clone_repo(vcs_url, commit_hash)
            # repo = Repo(repo_path)

            repo = Repo("/home/ziad-hany/PycharmProjects/flask")
            # repo = Repo("/home/ziad-hany/PycharmProjects/vulnerablecode")
            patch_symbols_by_language = collect_patch_symbols(repo, commit_hash)

            if not patch_symbols_by_language:
                continue

            for resource in candidate_resources:
                resource_language = resource.programming_language
                if resource_language not in patch_symbols_by_language:
                    continue

                resource_text = resource.file_content
                if not resource_text:
                    continue

                patch_symbols = patch_symbols_by_language[resource_language]
                resource_index = build_resource_index(
                    resource_text,
                    resource_language,
                )

                if not resource_index:
                    continue

                vuln_evidence = match_symbols_against_resource(
                    patch_symbols["vulnerable"],
                    resource_index,
                )

                fixed_evidence = match_symbols_against_resource(
                    patch_symbols["fixed"],
                    resource_index,
                )

                if not vuln_evidence and not fixed_evidence:
                    continue

                result = {
                    "symbols_reachability": {
                        "patch": {
                            "vcs_url": vcs_url,
                            "commit_hash": commit_hash,
                        },
                        "evidence": list(vuln_evidence.values()),
                        "fixed_symbols": sorted(fixed_evidence.keys()),
                        "vulnerable_symbols": sorted(vuln_evidence.keys()),
                        "reachability_status": classify_reachability(
                            vuln_evidence
                        ).value,
                    }
                }

                resource.update_extra_data(
                    {
                        "symbols_reachability": result,
                    }
                )

        except Exception as e:
            logger(
                f"Failed to collect symbol reachability for "
                f"{vcs_url}@{commit_hash}: {e}"
            )
        finally:
            # cleanup_repo(repo_path)
            pass


@dataclass
class SymbolNode:
    qualified_name: str
    node: Any  # tree-sitter node
    node_type: str
    fingerprint: str


@dataclass
class CallGraph:
    nodes: dict[str, SymbolNode] = field(default_factory=dict)
    edges_qualified: dict[str, set[str]] = field(default_factory=dict)
    imports: dict[str, str] = field(default_factory=dict)


@dataclass
class ResourceIndex:
    definitions: set[str] = field(default_factory=set)
    fingerprints: set[str] = field(default_factory=set)
    call_graph: CallGraph | None = None

    def to_dict(self):
        return {
            "definitions": self.definitions,
            "fingerprints": self.fingerprints,
            "call_graph": {
                "nodes": {k: vars(v) for k, v in self.call_graph.nodes.items()},
                "edges_qualified": self.call_graph.edges_qualified,
                "imports": self.call_graph.imports,
            }
            if self.call_graph
            else None,
        }


class CallGraphBuilder:
    def __init__(self, tree, language: str):
        self.tree = tree
        self.language = language
        self.index = collect_definitions(tree.root_node, language)
        self.imports = collect_imports(tree.root_node, language)

        self.nodes: dict[str, SymbolNode] = {}
        self.definitions_by_name: dict[str, set[str]] = {}
        self.class_methods: set[str] = set()

    def build(self) -> CallGraph:
        """Main execution flow for building the call graph."""
        self._extract_nodes()
        edges = self._resolve_all_edges()

        return CallGraph(nodes=self.nodes, edges_qualified=edges, imports=self.imports)

    def _extract_nodes(self):
        """Extract all definitions and populate lookup maps."""
        sep = get_imports_language_config(self.language)["separator"]

        for definition in self.index.values():
            node = definition["node"]
            qualified_name = qualified_name_from_index(node, self.index)

            if not qualified_name:
                continue

            body_text = node.text.decode("utf-8", errors="replace")
            fingerprint = create_sha256_fingerprint(body_text)

            self.nodes[qualified_name] = SymbolNode(
                qualified_name=qualified_name,
                node=node,
                node_type=node.type,
                fingerprint=fingerprint,
            )

            short_name = qualified_name.rsplit(sep, 1)[-1]
            self.definitions_by_name.setdefault(short_name, set()).add(qualified_name)

            if node.type == "function_definition":
                parent = node.parent
                if parent is not None and parent.type == "class_definition":
                    self.class_methods.add(qualified_name)

    def _resolve_all_edges(self) -> dict[str, set[str]]:
        """Map out all direct calls for every node in the graph."""
        edges_qualified = {}

        for qualified_name, symbol_node in self.nodes.items():
            direct_calls = extract_direct_calls(symbol_node.node, self.language)
            resolved_callees = set()

            for receiver_name, callee_name in direct_calls:
                resolved_callees |= resolve_callee(
                    receiver_name=receiver_name,
                    callee_name=callee_name,
                    owner_qn=qualified_name,
                    definitions_by_name=self.definitions_by_name,
                    class_methods=self.class_methods,
                    import_map=self.imports,
                    language=self.language,
                )

            edges_qualified[qualified_name] = resolved_callees

        return edges_qualified


def build_resource_index(resource_text, language) -> ResourceIndex | None:
    if not is_supported_language(language) or not resource_text:
        return None

    tree, _ = parse_code_to_ast(resource_text, language)
    if tree is None:
        return None

    call_graph = build_call_graph(tree, language)

    if call_graph:
        definitions = set(call_graph.nodes.keys())
        fingerprints = {
            node.fingerprint for node in call_graph.nodes.values() if node.fingerprint
        }
    else:
        meta = build_symbol_metadata(extract_definitions(tree, language), language)
        definitions = {m["qualified_name"] for m in meta.values()}
        fingerprints = {m["fingerprint"] for m in meta.values() if m["fingerprint"]}

    return ResourceIndex(
        definitions=definitions, fingerprints=fingerprints, call_graph=call_graph
    )


def match_symbols_against_resource(
    patch_symbols_metadata: dict[str, Any], resource_index: "ResourceIndex"
) -> dict[str, Any]:
    if not patch_symbols_metadata or not resource_index:
        return {}

    call_graph = resource_index.call_graph
    imports = call_graph.imports if call_graph else {}
    edges_qualified = call_graph.edges_qualified if call_graph else {}

    imported_fq_names = set(imports.values())

    target_qualified_names = {
        metadata["qualified_name"] for metadata in patch_symbols_metadata.values()
    }

    reachable_callers, _ = compute_reachable_symbols(
        edges_qualified,
        target_qualified_names,
    )

    called_qualified_names = set()
    for callees in edges_qualified.values():
        called_qualified_names |= set(callees)

    matched = {}
    for metadata in patch_symbols_metadata.values():
        qualified_name = metadata["qualified_name"]
        fingerprint = metadata["fingerprint"]

        defined = qualified_name in resource_index.definitions
        fingerprint_hit = bool(
            fingerprint and fingerprint in resource_index.fingerprints
        )

        imported = (
            qualified_name in imports
            or qualified_name in imported_fq_names
            or any(
                fq == qualified_name or fq.endswith("." + qualified_name)
                for fq in imported_fq_names
            )
        )

        called = any(
            fq_name == qualified_name or fq_name.endswith("." + qualified_name)
            for fq_name in called_qualified_names
        )

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
            entry["reachable_from"] = sorted(reachable_callers)
        if fingerprint:
            entry["fingerprint"] = fingerprint

    return matched


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


def build_symbol_metadata(nodes, language, index=None):
    if index is None and nodes:
        index = collect_definitions(_root_of(nodes[0]), language)

    metadata = {}
    for node in nodes:
        qualified_name = qualified_name_from_index(node, index)
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


def build_call_graph(tree, language) -> CallGraph | None:
    if tree is None or not is_supported_language(language):
        return None

    builder = CallGraphBuilder(tree, language)
    return builder.build()


def extract_direct_calls(node, language):
    """
    Return direct calls inside `node`, excluding calls inside nested definitions.

    Returns:
        list of (receiver_name, callee_name)

    Examples:
        foo()       -> (None, "foo")
        self.foo()  -> ("self", "foo")
        obj.foo()   -> ("obj", "foo")

    """
    query = get_query(language, "calls")
    if query is None or node is None:
        return []

    calls = []
    definition_types = {"function_definition", "class_definition"}

    for _, captures in query.matches(node):
        for callee_node in captures.get("callee", []):
            cur = callee_node.parent
            inside_nested = False
            while cur is not None and cur.id != node.id:
                if cur.type in definition_types:
                    inside_nested = True
                    break
                cur = cur.parent

            if inside_nested:
                continue

            receiver_name = get_call_receiver(callee_node)
            callee_name = callee_node.text.decode("utf-8", errors="replace")

            if callee_name:
                calls.append((receiver_name, callee_name))
    return calls


def get_call_receiver(callee_node):
    """
    Return receiver name for attribute calls.

    Examples:
        foo()       -> None
        self.foo()  -> "self"
        obj.foo()   -> "obj"

    """
    parent = callee_node.parent

    if parent is None or parent.type != "attribute":
        return None

    object_node = parent.child_by_field_name("object")
    if object_node is None:
        return None

    return object_node.text.decode("utf-8", errors="replace")


def compute_reachable_symbols(call_graph, target_qualified_names):
    """Transitive callers using resolved qualified-name edges."""
    if not call_graph or not target_qualified_names:
        return set(), False

    edges = call_graph.get("edges_qualified")
    if not edges:
        return set(), False

    callers_of = {}
    for caller, callees in edges.items():
        for callee in callees:
            callers_of.setdefault(callee, set()).add(caller)

    targets = set(target_qualified_names)
    direct = set()
    for target in targets:
        direct |= callers_of.get(target, set())

    reachable = set(direct)
    frontier = list(direct)
    while frontier:
        cur = frontier.pop()
        for parent in callers_of.get(cur, ()):
            if parent not in reachable:
                reachable.add(parent)
                frontier.append(parent)

    return reachable, bool(direct)


def get_imports_language_config(language: str) -> dict:
    configs = {
        "Python": {"self_keyword": "self", "separator": ".", "wildcard_symbol": "*"},
        "Javascript": {
            "self_keyword": "this",
            "separator": ".",
            "wildcard_symbol": "*",
        },
        "Java": {"self_keyword": "this", "separator": ".", "wildcard_symbol": "*"},
        "C++": {"self_keyword": "this", "separator": "::", "wildcard_symbol": None},
        "PHP": {"self_keyword": "$this", "separator": "::", "wildcard_symbol": None},
        "Go": {"self_keyword": None, "separator": "/", "wildcard_symbol": None},
        "Ruby": {"self_keyword": "self", "separator": "::", "wildcard_symbol": None},
    }
    return configs.get(
        language, {"self_keyword": None, "separator": ".", "wildcard_symbol": None}
    )


def resolve_callee(
    receiver_name: str | None,
    callee_name: str,
    owner_qn: str,
    definitions_by_name: dict[str, set[str]],
    class_methods: set[str],
    language: str,
    import_map: dict | None = None,
) -> set[str]:
    config = get_imports_language_config(language)
    sep = config["separator"]
    self_kw = config["self_keyword"]
    import_map = import_map or {}

    if receiver_name:
        receiver_name = receiver_name.strip("'\"")
    if callee_name:
        callee_name = callee_name.strip("'\"")

    if self_kw is not None and receiver_name == self_kw:
        owner_class = owner_qn.rsplit(sep, 1)[0] if sep in owner_qn else owner_qn
        return {f"{owner_class}{sep}{callee_name}"}

    if callee_name in import_map:
        return {import_map[callee_name]}

    if receiver_name is not None and receiver_name != self_kw:
        candidates = set()

        if receiver_name in import_map and receiver_name != "*":
            base = import_map[receiver_name]
            candidates.add(f"{base}{sep}{callee_name}")

        static_fqn = f"{receiver_name}{sep}{callee_name}"
        if static_fqn in class_methods:
            candidates.add(static_fqn)

        return candidates

    local_defs = definitions_by_name.get(callee_name, set())
    if local_defs:
        return local_defs

    if "*" in import_map:
        return {f"{mod}{sep}{callee_name}" for mod in import_map["*"]}

    return set()


def collect_imports(root_node, language: str) -> dict[str, str | list[str]]:
    """
    Extract import statements from a Tree-sitter AST and map every local alias to its absolute imported path.
    """
    config = get_imports_language_config(language)
    separator = config["separator"]
    wildcard_sym = config.get("wildcard_symbol")

    query = get_query(language, "imports")
    if not query or not root_node:
        return {}

    import_map: dict[str, str | list[str]] = {}
    wildcard_modules: list[str] = []

    for _pattern_index, captures in query.matches(root_node):
        flat_captures = []
        for tag, nodes in captures.items():
            for n in nodes:
                flat_captures.append(
                    (
                        n.start_byte,
                        tag,
                        n.text.decode("utf-8", errors="replace").strip("'\""),
                    )
                )

        flat_captures.sort(key=lambda x: x[0])

        module_name = None
        current_import = None
        pairs = []

        for _, tag, text in flat_captures:
            if tag == "module_name":
                module_name = text
            elif tag == "import_name":
                if current_import is not None:
                    pairs.append((current_import, None))
                current_import = text
            elif tag == "alias":
                pairs.append((current_import, text))
                current_import = None

        if current_import is not None:
            pairs.append((current_import, None))

        for imp_name, alias in pairs:
            if not imp_name:
                continue

            if wildcard_sym is not None and imp_name == wildcard_sym:
                if module_name:
                    wildcard_modules.append(module_name)
                continue

            local_name = alias or imp_name

            if not alias and separator in imp_name:
                local_name = imp_name.split(separator)[0]

            absolute_path = (
                f"{module_name}{separator}{imp_name}" if module_name else imp_name
            )
            import_map[local_name] = absolute_path

    if wildcard_modules:
        import_map["*"] = wildcard_modules

    return import_map

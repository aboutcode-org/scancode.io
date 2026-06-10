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

from git import Repo
from git.diff import NULL_TREE
from git.exc import BadName
from scancode.api import get_file_info
from unidiff import PatchSet

from scanpipe.pipes.symbols import TS_QUERIES
from scanpipe.pipes.symbols import _root_of
from scanpipe.pipes.symbols import collect_definitions
from scanpipe.pipes.symbols import create_exact_symbol_fingerprint
from scanpipe.pipes.symbols import extract_definitions
from scanpipe.pipes.symbols import extract_symbols
from scanpipe.pipes.symbols import get_query
from scanpipe.pipes.symbols import is_nested_function
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
    return repo.git.diff(base, commit.hexsha, unified=0)


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
    """Return `(removed_lines, added_lines)` for one file from a unified diff."""
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
            for line in hunk:
                if line.is_removed and line.source_line_no:
                    removed.append(line.source_line_no)
                elif line.is_added and line.target_line_no:
                    added.append(line.target_line_no)

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
    commit, parent = get_commit_and_parent(repo, commit_hash)
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


def append_symbol_reachability_result(resource, result):
    """
    Append one symbol reachability result to the resource extra_data without
    overwriting previous results.
    """
    extra_data = resource.extra_data or {}
    existing_results = extra_data.get("symbols_reachability", [])

    if not isinstance(existing_results, list):
        existing_results = [existing_results]

    existing_results.append(result)

    resource.update_extra_data(
        {
            "symbols_reachability": existing_results,
        }
    )


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
            # repo = Repo("/home/ziad-hany/PycharmProjects/flask/")
            repo = Repo("/home/ziad-hany/PycharmProjects/aiohttp")

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
                vuln_patch_metadata = patch_symbols["vulnerable"]
                fixed_patch_metadata = patch_symbols["fixed"]

                resource_index = build_resource_index(
                    resource_text,
                    resource_language,
                )

                if not resource_index:
                    continue

                vuln_match_symbols = match_symbols_against_resource(
                    vuln_patch_metadata,
                    resource_index,
                )

                fixed_match_symbols = match_symbols_against_resource(
                    fixed_patch_metadata,
                    resource_index,
                )

                if not vuln_match_symbols and not fixed_match_symbols:
                    continue

                result = {
                    "reachability_status": classify_reachability(vuln_match_symbols),
                    "summary": {
                        "call_paths": {
                            qualified_name: ev.get("reachable_from", [])
                            for qualified_name, ev in vuln_match_symbols.items()
                            if ev.get("called")
                        },
                    },
                    "evidence": vuln_match_symbols,
                    "vulnerable_symbols": sorted(vuln_match_symbols),
                    "fixed_symbols": sorted(fixed_match_symbols),
                    "patch": {
                        "vcs_url": vcs_url,
                        "commit_hash": commit_hash,
                    },
                }
                print(result)
                append_symbol_reachability_result(resource, result)

        except Exception as e:
            logger(
                f"Failed to collect symbol reachability for "
                f"{vcs_url}@{commit_hash}: {e}"
            )
        finally:
            if repo:
                repo.close()

            # cleanup_repo(repo_path)


def build_resource_index(resource_text, language):
    if not is_supported_language(language) or not resource_text:
        return None

    tree, _ = parse_code_to_ast(resource_text, language)

    if tree is None:
        return None

    call_graph = build_call_graph(tree, language)

    meta = (
        call_graph["nodes"]
        if call_graph
        else build_symbol_metadata(
            extract_definitions(tree, language),
            language,
        )
    )

    return {
        "definitions": {metadata["qualified_name"] for metadata in meta.values()},
        "fingerprints": {
            metadata["fingerprint"]
            for metadata in meta.values()
            if metadata["fingerprint"]
        },
        "call_graph": call_graph,
    }


def match_symbols_against_resource(patch_symbols_metadata, resource_index):
    if not patch_symbols_metadata or not resource_index:
        return {}

    call_graph = resource_index.get("call_graph")

    target_qualified_names = {
        metadata["qualified_name"] for metadata in patch_symbols_metadata.values()
    }

    reachable_callers, _ = compute_reachable_symbols(
        call_graph,
        target_qualified_names,
    )

    called_qualified_names = set()

    if call_graph:
        for callees in call_graph.get("edges_qualified", {}).values():
            called_qualified_names |= set(callees)

    matched = {}

    for metadata in patch_symbols_metadata.values():
        qualified_name = metadata["qualified_name"]
        fingerprint = metadata["fingerprint"]

        defined = qualified_name in resource_index.get("definitions", {})
        fingerprint_hit = bool(
            fingerprint and fingerprint in resource_index.get("fingerprints", {})
        )
        called = qualified_name in called_qualified_names

        if not (defined or fingerprint_hit or called):
            continue

        entry = matched.setdefault(
            qualified_name,
            {
                "defined": False,
                "called": False,
                "reachable_from": [],
            },
        )

        entry["defined"] = entry["defined"] or defined
        entry["called"] = entry["called"] or called

        if fingerprint_hit:
            entry["exact_match_fingerprint"] = fingerprint

        if called:
            entry["reachable_from"] = sorted(reachable_callers)

    return matched


def classify_reachability(evidence):
    if not evidence:
        return ReachabilityStatus.NOT_REACHABLE

    highest_status = ReachabilityStatus.NOT_REACHABLE

    for item in evidence.values():
        is_called = bool(item.get("called"))
        has_path = bool(item.get("reachable_from"))
        is_exact = "exact_match_fingerprint" in item
        is_defined = bool(item.get("defined"))

        if is_called or has_path:
            return ReachabilityStatus.REACHABLE

        if is_exact or is_defined:
            highest_status = ReachabilityStatus.POTENTIALLY_REACHABLE

    return highest_status


def build_symbol_metadata(nodes, language, index=None):
    if index is None and nodes:
        index = collect_definitions(_root_of(nodes[0]), language)

    metadata = {}
    for node in nodes:
        if is_nested_function(node, language):
            continue

        qualified_name = qualified_name_from_index(node, index)
        if not qualified_name:
            continue

        body_text = node.text.decode("utf-8", errors="replace")
        fingerprints = create_exact_symbol_fingerprint(body_text)

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


def build_call_graph(tree, language):
    if tree is None or not is_supported_language(language):
        return None

    index = collect_definitions(tree.root_node, language)

    graph_meta = {}
    for definition in index.values():
        node = definition["node"]
        qualified_name = qualified_name_from_index(node, index)

        if not qualified_name:
            continue

        body_text = node.text.decode("utf-8", errors="replace")
        fingerprints = create_exact_symbol_fingerprint(body_text) or {}

        graph_meta[qualified_name] = {
            "qualified_name": qualified_name,
            "node": node,
            "node_type": node.type,
            "fingerprint": fingerprints,
        }

    definitions_by_name = {}
    class_methods = set()

    for qualified_name, metadata in graph_meta.items():
        name = qualified_name.rsplit(".", 1)[-1]
        definitions_by_name.setdefault(name, set()).add(qualified_name)

        if metadata["node_type"] == "function_definition" and "." in qualified_name:
            class_methods.add(qualified_name)

    edges_qualified = {}
    for qualified_name, metadata in graph_meta.items():
        direct_calls = extract_direct_calls(metadata["node"], language, index)

        resolved_callees = set()

        for receiver_name, callee_name in direct_calls:
            resolved_callees |= resolve_callee(
                receiver_name=receiver_name,
                callee_name=callee_name,
                owner_qn=qualified_name,
                definitions_by_name=definitions_by_name,
                class_methods=class_methods,
            )

        edges_qualified[qualified_name] = resolved_callees

    return {
        "nodes": graph_meta,
        "edges_qualified": edges_qualified,
    }


def extract_direct_calls(node, language, definition_index):
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

    definition_ids = set(definition_index)
    calls = []

    for _, captures in query.matches(node):
        for callee_node in captures.get("callee", []):
            if is_inside_nested_definition(
                node=callee_node,
                owner_node=node,
                definition_ids=definition_ids,
            ):
                continue

            receiver_name = get_call_receiver(callee_node)
            callee_name = node_text(callee_node)

            if callee_name:
                calls.append((receiver_name, callee_name))

    return calls


def is_inside_nested_definition(node, owner_node, definition_ids):
    """
    Return True if node is inside a nested function/class within `owner_node`.

    Example:
        def outer():
            foo()      # belongs to outer

            def inner():
                bar()  # nested; should not count as outer's call

    """
    current = node.parent

    while current is not None and current is not owner_node:
        if current.id in definition_ids:
            return True

        current = current.parent

    return False


def node_text(node):
    return node.text.decode("utf-8", errors="replace")


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

    return node_text(object_node)


def resolve_callee(
    receiver_name, callee_name, owner_qn, definitions_by_name, class_methods
):
    """
    Resolve a call to candidate qualified names.

    Examples:
        self.foo() from class A -> {"A.foo"} if A.foo exists
        foo()                  -> definitions named "foo"

    """
    if receiver_name == "self":
        owner_class = get_owner_class_name(owner_qn)

        if owner_class:
            method_qn = f"{owner_class}.{callee_name}"

            if method_qn in class_methods:
                return {method_qn}

    candidates = definitions_by_name.get(callee_name, set())
    return set(candidates)


def get_owner_class_name(owner_qn):
    """
    Return enclosing class name from a qualified name.

    Examples:
        "User.save"       -> "User"
        "User.Inner.save" -> "User.Inner"
        "save"            -> None

    """
    if "." not in owner_qn:
        return None

    return owner_qn.rsplit(".", 1)[0]


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

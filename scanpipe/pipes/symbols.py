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

import hashlib
import importlib
from functools import cache

from django.db.models import Q

from source_inspector import symbols_ctags
from source_inspector import symbols_pygments
from source_inspector import symbols_tree_sitter
from source_inspector.symbols_tree_sitter import TS_LANGUAGE_WHEELS
from source_inspector.symbols_tree_sitter import TreeSitterWheelNotInstalled
from tree_sitter import Language
from tree_sitter import Parser
from tree_sitter import Query

from aboutcode.pipeline import LoopProgress


class UniversalCtagsNotFound(Exception):
    pass


def collect_and_store_resource_symbols_ctags(project, logger=None):
    """
    Collect symbols from codebase files using Ctags and store
    them in the extra data field.
    """
    from source_inspector import symbols_ctags

    if not symbols_ctags.is_ctags_installed():
        raise UniversalCtagsNotFound(
            "``Universal Ctags`` not found."
            "Install ``Universal Ctags`` to use this pipeline."
        )

    project_files = project.codebaseresources.files()

    resources = project_files.filter(
        is_binary=False,
        is_archive=False,
        is_media=False,
    )

    resources_count = resources.count()

    resource_iterator = resources.iterator(chunk_size=2000)
    progress = LoopProgress(resources_count, logger)

    for resource in progress.iter(resource_iterator):
        _collect_and_store_resource_symbols_ctags(resource)


def _collect_and_store_resource_symbols_ctags(resource):
    """
    Collect symbols from a resource using Ctags and store
    them in the extra data field.
    """
    from source_inspector import symbols_ctags

    symbols = symbols_ctags.collect_symbols(resource.location)
    tags = [symbol["name"] for symbol in symbols if "name" in symbol]
    resource.update_extra_data({"source_symbols": tags})


def collect_and_store_pygments_symbols_and_strings(project, logger=None):
    """
    Collect symbols, strings and comments from codebase files using pygments and store
    them in the extra data field.
    """
    project_files = project.codebaseresources.files()

    resources = project_files.filter(
        is_binary=False,
        is_archive=False,
        is_media=False,
    )

    resources_count = resources.count()

    resource_iterator = resources.iterator(chunk_size=2000)
    progress = LoopProgress(resources_count, logger)

    for resource in progress.iter(resource_iterator):
        _collect_and_store_pygments_symbols_and_strings(resource)


def _collect_and_store_pygments_symbols_and_strings(resource):
    """
    Collect symbols, strings and comments from a resource using pygments and store
    them in the extra data field.
    """
    from source_inspector import symbols_pygments

    result = symbols_pygments.get_pygments_symbols(resource.location)
    resource.update_extra_data(
        {
            "source_symbols": result.get("source_symbols"),
            "source_strings": result.get("source_strings"),
            "source_comments": result.get("source_comments"),
        }
    )


def collect_and_store_tree_sitter_symbols_and_strings(
    project, logger=None, project_files=None
):
    """
    Collect symbols from codebase files using tree-sitter and store
    them in the extra data field.

    Collect from `project_files` instead of all codebase files if specified.
    """
    from source_inspector import symbols_tree_sitter

    if not project_files:
        project_files = project.codebaseresources.files()

    language_qs = Q()

    for language in symbols_tree_sitter.TS_LANGUAGE_WHEELS.keys():
        language_qs |= Q(programming_language__iexact=language)

    resources = project_files.filter(
        is_binary=False,
        is_archive=False,
        is_media=False,
    ).filter(language_qs)

    resources_count = resources.count()
    if logger:
        logger(
            f"Getting source symbols and strings from {resources_count:,d}"
            " resources using tree-sitter."
        )

    resource_iterator = resources.iterator(chunk_size=2000)
    progress = LoopProgress(resources_count, logger)

    for resource in progress.iter(resource_iterator):
        try:
            _collect_and_store_tree_sitter_symbols_and_strings(resource)
        except Exception as e:
            project.add_error(
                description=f"Cannot collect strings from resource at {resource.path}",
                exception=e,
                model="collect_and_store_tree_sitter_symbols_and_strings",
                details={"resource_path": resource.path},
            )


def _collect_and_store_tree_sitter_symbols_and_strings(resource):
    """
    Collect symbols and string from a resource using tree-sitter and store
    them in the extra data field.
    """
    from source_inspector import symbols_tree_sitter

    result = symbols_tree_sitter.get_treesitter_symbols(resource.location)
    resource.update_extra_data(
        {
            "source_symbols": result.get("source_symbols"),
            "source_strings": result.get("source_strings"),
        }
    )


SYMBOLS_TYPE_SUPPORTED = {
    "ctags": symbols_ctags.get_symbols,
    "tree_sitter": symbols_tree_sitter.get_treesitter_symbols,
    "pygments": symbols_pygments.get_pygments_symbols,
}

TS_QUERIES = {
    "Python": {
        "functions": """
            (function_definition name: (identifier) @name) @function
        """,
        "classes": """
            (class_definition name: (identifier) @name) @class
        """,
        "calls": """
            (call function: (identifier) @callee)
            (call function: (attribute
                object: (_) @receiver
                attribute: (identifier) @callee))
        """,
        "imports": """
            (import_statement name: (dotted_name) @import_name)
            (import_statement
                name: (aliased_import
                    name: (dotted_name) @import_name
                    alias: (identifier) @alias))
            (import_from_statement
                module_name: (dotted_name) @module_name
                name: (dotted_name) @import_name)
            (import_from_statement
                module_name: (dotted_name) @module_name
                name: (aliased_import
                    name: (dotted_name) @import_name
                    alias: (identifier) @alias))
        """,
    },
}


@cache
def load_language(language: str) -> Language:
    if language not in TS_LANGUAGE_WHEELS:
        raise ValueError(f"Unsupported language: {language}")

    wheel = TS_LANGUAGE_WHEELS[language]["wheel"]
    try:
        grammar = importlib.import_module(wheel)
    except ModuleNotFoundError as exc:
        raise TreeSitterWheelNotInstalled(
            f"Grammar wheel '{wheel}' is not installed."
        ) from exc
    return Language(grammar.language())


@cache
def get_query(language: str, kind: str) -> Query | None:
    source = TS_QUERIES.get(language, {}).get(kind, "").strip()
    if not source:
        return None
    return Query(load_language(language), source)


def parse_code_to_ast(code_text: str, language: str):
    if not code_text or not language or language not in TS_LANGUAGE_WHEELS:
        return None, None

    ts_language = load_language(language)
    parser = Parser(language=ts_language)
    return parser.parse(code_text.encode("utf-8")), TS_LANGUAGE_WHEELS[language]


def run_query(query: Query, root_node):
    """Yield ``(definition_node, name)`` pairs for function/class queries."""
    if query is None:
        return

    for _pattern_index, captures in query.matches(root_node):
        def_nodes = captures.get("function") or captures.get("class") or []
        if not def_nodes:
            continue

        name_nodes = captures.get("name") or []
        name = (
            name_nodes[0].text.decode("utf-8", errors="replace") if name_nodes else None
        )
        yield def_nodes[0], name


def query_captures(language, kind, node):
    """Re-run a definition query on the root of node's tree."""
    query = get_query(language, kind)
    return list(run_query(query, _root_of(node)))


def _root_of(node):
    while node.parent is not None:
        node = node.parent
    return node


def is_nested_function(node, language):
    function_nodes = {
        captured_node
        for captured_node, _ in query_captures(language, "functions", node)
    }
    class_nodes = {
        captured_node for captured_node, _ in query_captures(language, "classes", node)
    }

    if node not in function_nodes:
        return False

    function_types = {captured_node.type for captured_node in function_nodes}
    class_types = {captured_node.type for captured_node in class_nodes}

    parent = node.parent

    while parent is not None:
        if parent.type in function_types:
            return True

        if parent.type in class_types:
            return False

        parent = parent.parent

    return False


def extract_calls_in_node(node, language: str):
    query = get_query(language, "calls")
    if query is None or node is None:
        return set()

    names = set()
    for _pattern_index, captures in query.matches(node):
        for callee_node in captures.get("callee", []):
            name = callee_node.text.decode("utf-8", errors="replace")
            if name:
                names.add(name)
    return names


def collect_definitions(root_node, language: str):
    index: dict[int, dict] = {}
    for kind in ("functions", "classes"):
        query = get_query(language, kind)
        for node, name in run_query(query, root_node):
            index[node.id] = {"node": node, "name": name, "kind": kind}
    return index


def extract_definitions(tree, language: str, kinds=("functions", "classes")):
    if tree is None:
        return []
    index = collect_definitions(tree.root_node, language)
    return [d["node"] for d in index.values() if d["kind"] in kinds]


def extract_symbols(tree, changed_lines: list[int], language: str):
    if tree is None or not changed_lines:
        return []

    definition_ids = set(collect_definitions(tree.root_node, language).keys())
    if not definition_ids:
        return []

    seen = set()
    enclosing = []

    for line in changed_lines:
        row = max(0, line - 1)
        node = tree.root_node.descendant_for_point_range((row, 0), (row, 0))

        while node is not None:
            if node.id in definition_ids and node.id not in seen:
                seen.add(node.id)
                enclosing.append(node)
                break
            node = node.parent

    return enclosing


def qualified_name_from_index(node, index):
    parts = []
    curr = node
    while curr is not None:
        definition = index.get(curr.id)
        if definition is not None and definition["name"]:
            parts.append(definition["name"])
        curr = curr.parent
    return ".".join(reversed(parts))


def create_exact_symbol_fingerprint(text):
    if text is None:
        return None

    text = text.encode("utf-8", errors="replace")
    return hashlib.sha256(text).hexdigest()

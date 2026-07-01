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
from abc import ABC
from functools import cache

from django.db.models import Q
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

@cache
def load_language(language: str):
    from source_inspector.symbols_tree_sitter import TS_LANGUAGE_WHEELS
    from source_inspector.symbols_tree_sitter import TreeSitterWheelNotInstalled
    from tree_sitter import Language

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


def create_sha256_fingerprint(text):
    if not text:
        return None

    text = text.encode("utf-8", errors="replace")
    return hashlib.sha256(text).hexdigest()


class LanguageQuery(ABC):
    language_name: str = ""
    constants_query: str = ""
    functions_query: str = ""
    classes_query: str = ""
    calls_query: str = ""
    imports_query: str = ""
    syntax_config: dict = {
        "self_keyword": None,
        "separator": ".",
        "wildcard_symbol": None,
    }

    def __init__(self):
        from tree_sitter import Query

        self.ts_language = load_language(self.language_name)
        self._compiled_queries = {}

        for kind in ("constants", "functions", "classes", "calls", "imports"):
            source = getattr(self, f"{kind}_query", "").strip()
            self._compiled_queries[kind] = (
                Query(self.ts_language, source) if source else None
            )

    def parse_code_to_ast(self, code_text: str):
        from source_inspector.symbols_tree_sitter import TS_LANGUAGE_WHEELS
        from tree_sitter import Parser

        if not code_text:
            return None, None
        parser = Parser(language=self.ts_language)
        return parser.parse(code_text.encode("utf-8")), TS_LANGUAGE_WHEELS[
            self.language_name
        ]

    def run_query(self, kind: str, root_node):
        query = self._compiled_queries.get(kind)
        return query.matches(root_node) if query else []

    def get_functions(self, root_node):
        for _, captures in self.run_query("functions", root_node):
            def_nodes = captures.get("function")
            if not def_nodes:
                continue
            name_nodes = captures.get("name")
            name = (
                name_nodes[0].text.decode("utf-8", errors="replace")
                if name_nodes
                else None
            )
            yield def_nodes[0], name

    def get_classes(self, root_node):
        for _, captures in self.run_query("classes", root_node):
            def_nodes = captures.get("class")
            if not def_nodes:
                continue
            name_nodes = captures.get("name")
            name = (
                name_nodes[0].text.decode("utf-8", errors="replace")
                if name_nodes
                else None
            )
            yield def_nodes[0], name

    def get_calls(self, node):
        """Yield raw (receiver_node, callee_node)."""
        seen_callees = set()
        for _, captures in self.run_query("calls", node):
            for callee_node in captures.get("callee", []):
                if callee_node.id in seen_callees:
                    continue
                seen_callees.add(callee_node.id)

                receiver_nodes = captures.get("receiver")
                receiver_node = receiver_nodes[0] if receiver_nodes else None
                yield receiver_node, callee_node

    def get_imports(self, root_node):
        """Yield raw (module_name, [(import_name, alias), ...])."""
        for _, captures in self.run_query("imports", root_node):
            flat_captures = []
            for tag, nodes in captures.items():
                for n in nodes:
                    text = n.text.decode("utf-8", errors="replace").strip("'\"")
                    flat_captures.append((n.start_byte, tag, text))

            flat_captures.sort(key=lambda x: x[0])
            module_name, current_import = None, None
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

            yield module_name, pairs

    def get_constants(self, root_node):
        """Yield raw (constant_node, name)."""
        for _, captures in self.run_query("constants", root_node):
            def_nodes = captures.get("constant")
            if not def_nodes:
                continue
            name_nodes = captures.get("name")
            name = (
                name_nodes[0].text.decode("utf-8", errors="replace")
                if name_nodes
                else None
            )
            yield def_nodes[0], name


class PythonTreeSitterQuery(LanguageQuery):
    language_name = "Python"
    constants_query = """
        (assignment
            left: (identifier) @name) @constant

        (assignment
            left: (pattern_list (identifier) @name)) @constant
    """
    functions_query = "(function_definition name: (identifier) @name) @function"
    classes_query = "(class_definition name: (identifier) @name) @class"
    calls_query = """
        (call function: (identifier) @callee)
        (call function: (attribute object: (_) @receiver
                                   attribute: (identifier) @callee))
    """
    imports_query = """
    (import_statement name: (dotted_name) @import_name)
    (import_statement name: (aliased_import
        name: (dotted_name) @import_name
        alias: (identifier) @alias))
    (import_from_statement
        module_name: [(dotted_name) (relative_import)] @module_name
        name: [
            (dotted_name) @import_name
            (aliased_import name: (dotted_name) @import_name
                            alias: (identifier) @alias)
        ])
    (import_from_statement
        module_name: [(dotted_name) (relative_import)] @module_name
        (wildcard_import) @import_name)
    """
    syntax_config = {"self_keyword": "self", "separator": ".", "wildcard_symbol": "*"}


TS_QUERIES = {
    "Python": PythonTreeSitterQuery,
}


class SymbolExtractor:
    def __init__(self, lang_query: LanguageQuery, root_node):
        self.lang_query = lang_query
        self.root_node = root_node
        self.syntax_config = lang_query.syntax_config

    def _build_qualified_name(self, node, index: dict) -> str:
        """
        Build fully qualified names internally
        (e.g., ClassName.function_name or ClassName::function_name).
        """
        parts = []
        curr = node
        while curr is not None:
            definition = index.get(curr.id)
            if definition is not None and definition["name"]:
                parts.append(definition["name"])
            curr = curr.parent

        separator = self.syntax_config.get("separator", ".")
        return separator.join(reversed(parts))

    def extract_definitions_index(self):
        """Build the index of definitions with fully qualified names."""
        index: dict[int, dict] = {}

        for node, name in self.lang_query.get_functions(self.root_node):
            index[node.id] = {"node": node, "name": name, "kind": "functions"}

        for node, name in self.lang_query.get_classes(self.root_node):
            index[node.id] = {"node": node, "name": name, "kind": "classes"}

        for node, name in self.lang_query.get_constants(self.root_node):
            index[node.id] = {"node": node, "name": name, "kind": "constants"}

        for def_info in index.values():
            def_info["qualified_name"] = self._build_qualified_name(
                def_info["node"], index
            )

        return index

    def extract_changed_symbols(self, changed_lines: list[int]):
        """Map changed line numbers to their enclosing symbol nodes."""
        if self.root_node is None or not changed_lines:
            return []

        definition_ids = set(self.extract_definitions_index().keys())
        if not definition_ids:
            return []

        seen = set()
        enclosing = []

        for line in changed_lines:
            row = max(0, line - 1)
            node = self.root_node.descendant_for_point_range((row, 0), (row, 0))

            while node is not None:
                if node.id in definition_ids and node.id not in seen:
                    seen.add(node.id)
                    enclosing.append(node)
                    break
                node = node.parent

        return enclosing

    def extract_calls(self, node):
        """Extract direct calls into (receiver_name, callee_name) text format."""
        calls = []
        for receiver_node, callee_node in self.lang_query.get_calls(node):
            receiver_name = (
                receiver_node.text.decode("utf-8", errors="replace")
                if receiver_node
                else None
            )
            callee_name = callee_node.text.decode("utf-8", errors="replace")

            if callee_name:
                calls.append((receiver_name, callee_name))

        return calls

    def extract_imports(self):
        """Map every local alias to its absolute imported path."""
        separator = self.syntax_config.get("separator", ".")
        wildcard_sym = self.syntax_config.get("wildcard_symbol")

        import_map: dict[str, str | list[str]] = {}
        wildcard_modules: list[str] = []

        for module_name, pairs in self.lang_query.get_imports(self.root_node):
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


def is_supported_language(language):
    """Return True if the language is supported by tree-sitter queries."""
    return bool(language) and language in TS_QUERIES

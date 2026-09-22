# scanpipe/pipes/cpg.py

# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import json
import subprocess
from collections import deque
from os import environ

from aboutcode.pipeline import LoopProgress
from scanpipe.pipes import run_command_safely
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import save_resource_reachability_report

CPG_NEO4J_EXECUTABLE = environ.get("CPG_NEO4J_EXECUTABLE")


def clean_symbol_name(name):
    """
    Normalize a CPG symbol name: strip a trailing signature, e.g.
    ``app.serve_report.build_file_path()`` ->
    ``app.serve_report.build_file_path``.
    """
    name = str(name or "")
    if not name.endswith(")"):
        return name
    depth = 0
    for index in range(len(name) - 1, -1, -1):
        char = name[index]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
            if depth == 0:
                return name[:index].rstrip()
    return name


def collect_resource_index(project, logger=None):
    """
    Execute the cpg-neo4j binary to generate a CPG JSON export for the
    project codebase and return the parsed project-wide graph.
    """
    if not CPG_NEO4J_EXECUTABLE:
        raise ValueError("CPG_NEO4J_EXECUTABLE is not set or found.")

    target_path = getattr(project, "codebase_path", None)
    if not target_path:
        resources = project.codebaseresources.all()
        if not resources:
            raise ValueError("No codebase resources found for this project.")
        target_path = resources[0].location_path

    export_json_path = project.get_output_file_path("cpg_reachability", "json")
    command_args = [
        CPG_NEO4J_EXECUTABLE,
        "--no-neo4j",
        "--top-level",
        str(target_path),
        "--export-json",
        str(export_json_path),
        str(target_path),
    ]

    if logger:
        logger(f"Generating CPG JSON for {target_path} ...")
    try:
        run_command_safely(command_args=command_args)
        if logger:
            logger("CPG resource_index pipeline completed successfully")
    except subprocess.SubprocessError as error:
        raise RuntimeError(f"CPG client failure: {error!r}")
    except FileNotFoundError:
        raise FileNotFoundError(
            "CPG not found. Please ensure CPG is correctly configured."
        )

    with open(export_json_path) as f:
        return json.load(f)


class Node:
    """A node of the CPG property graph."""

    def __init__(self, data):
        self.id = data["id"]
        self.labels = frozenset(data.get("labels") or [])
        self.properties = data.get("properties") or {}

    def is_a(self, *labels):
        return any(label in self.labels for label in labels)

    @property
    def name(self):
        return self.properties.get("name") or ""

    @property
    def full_name(self):
        return self.properties.get("fullName") or ""

    def describe(self):
        """Identifier used in the reported ``eog_path``."""
        return (
            clean_symbol_name(self.full_name)
            or clean_symbol_name(self.name)
            or f"node-{self.id}"
        )


class Graph:
    """
    A CPG property-graph dump with the lookups needed for symbol
    matching and EOG traversal. Supports both the old
    (``FunctionDeclaration``/``FileNode``) and the 2023+ (``Function``/
    ``File``) label schemas, and both naming conventions (bare and
    module-prefixed names, with or without a trailing signature).
    """

    DECLARATION_LABELS = (
        "FunctionDeclaration",
        "MethodDeclaration",
        "ConstructorDeclaration",
        "RecordDeclaration",
        "ClassDeclaration",
        "EnumDeclaration",  # old
        "Function",
        "Method",
        "Constructor",
        "Record",
        "Enum",
        "Interface",  # new
    )
    RECORD_LABELS = (
        "RecordDeclaration",
        "ClassDeclaration",
        "EnumDeclaration",  # old
        "Record",
        "Enum",
        "Interface",  # new
    )
    METHOD_LABELS = (
        "FunctionDeclaration",
        "MethodDeclaration",
        "ConstructorDeclaration",
        "Function",
        "Method",
        "Constructor",
    )
    FILE_LABELS = ("FileNode", "File", "FileLikeObject")
    STRUCTURAL_EDGE_TYPES = ("AST", "CONTAINS", "DECLARATIONS", "STATEMENTS", "BODY")
    CALL_EDGE_TYPES = ("INVOKES", "CONSTRUCTORS", "CALLS")

    def __init__(self, graph_json):
        graph_json = graph_json or {}
        self.nodes = {data["id"]: Node(data) for data in graph_json.get("nodes", [])}

        self._successors = {}  # edge type -> source id -> [target ids]
        self._predecessors = {}  # edge type -> target id -> [source ids]
        self._parents = {}  # child id -> parent id
        self._children = {}  # parent id -> [child ids]
        for edge in graph_json.get("edges", []):
            src = edge["startNode"]
            dst = edge["endNode"]
            edge_type = edge.get("type") or edge.get("edgeType")
            if not edge_type:
                continue
            self._successors.setdefault(edge_type, {}).setdefault(src, []).append(dst)
            self._predecessors.setdefault(edge_type, {}).setdefault(dst, []).append(src)
            if edge_type in self.STRUCTURAL_EDGE_TYPES:
                self._parents.setdefault(dst, src)
                self._children.setdefault(src, []).append(dst)

        self._call_edge_types = [
            edge_type
            for edge_type in self.CALL_EDGE_TYPES
            if self._successors.get(edge_type)
        ]
        self.invokers_of = {}
        for edge_type in self._call_edge_types:
            for src, targets in self._successors[edge_type].items():
                for dst in targets:
                    self.invokers_of.setdefault(dst, set()).add(src)

        self.delimiter = "."
        for node in self.nodes.values():
            if node.properties.get("nameDelimiter"):
                self.delimiter = node.properties["nameDelimiter"]
                break

        self.has_file_nodes = any(
            n.is_a(*self.FILE_LABELS) for n in self.nodes.values()
        )
        self._file_of = {}
        self._entries = None
        self._descendants = {}

    def successors(self, node, edge_type="EOG"):
        ids = self._successors.get(edge_type, {}).get(node.id, [])
        return [self.nodes[i] for i in ids if i in self.nodes]

    def predecessors(self, node, edge_type="EOG"):
        ids = self._predecessors.get(edge_type, {}).get(node.id, [])
        return [self.nodes[i] for i in ids if i in self.nodes]

    def invokes(self, node):
        """Declarations invoked by a call-expression-like node."""
        callees = []
        for edge_type in self._call_edge_types:
            callees.extend(self.successors(node, edge_type))
        return callees

    def parent(self, node):
        parent_id = self._parents.get(node.id)
        return self.nodes.get(parent_id) if parent_id is not None else None

    def is_inside(self, node, ancestor):
        """True if ``node`` is ``ancestor`` or lies in its subtree."""
        while node is not None:
            if node is ancestor:
                return True
            node = self.parent(node)
        return False

    def declarations(self, labels=DECLARATION_LABELS):
        return [n for n in self.nodes.values() if n.is_a(*labels)]

    def members(self, record):
        """
        Method/function declarations of a class (record): AST-contained,
        linked via DECLARATIONS, or linked via the reverse DECLARATION edge
        (whichever direction the schema uses).
        """
        found = {
            n.id: n
            for n in self.declarations(self.METHOD_LABELS)
            if self.is_inside(n, record)
        }
        for node in self.successors(record, "DECLARATIONS"):
            if node.is_a(*self.METHOD_LABELS):
                found.setdefault(node.id, node)
        for node in self.predecessors(record, "DECLARATION"):
            if node.is_a(*self.METHOD_LABELS):
                found.setdefault(node.id, node)
        return list(found.values())

    def ast_descendants(self, node):
        if node.id not in self._descendants:
            stack = list(self._children.get(node.id, []))
            out = []
            while stack:
                child_id = stack.pop()
                child = self.nodes.get(child_id)
                if child:
                    out.append(child)
                    stack.extend(self._children.get(child_id, []))
            self._descendants[node.id] = out
        return self._descendants[node.id]

    def file_of(self, node):
        """The File node containing ``node``, or ``None``."""
        if node.id not in self._file_of:
            current = self.parent(node)
            while current is not None and not current.is_a(*self.FILE_LABELS):
                current = self.parent(current)
            self._file_of[node.id] = current
        return self._file_of[node.id]

    @staticmethod
    def paths_match(a, b):
        """
        True when two file paths denote the same file, allowing one to
        be longer than the other (resource path vs CPG file path).
        """

        def clean(path):
            path = str(path).replace("\\", "/").rstrip("/")
            path = path.removeprefix("file://")
            return path

        a, b = clean(a), clean(b)
        return a == b or a.endswith("/" + b) or b.endswith("/" + a)

    def in_file(self, node, file_path):
        """
        True if ``node`` is declared in the file matching ``file_path``.

        When the node's file cannot be resolved from the export, the node
        is not excluded: dropping it would silently lose symbols on
        exports whose structural edges differ from what we map.
        """
        file_node = self.file_of(node)
        if file_node is None:
            return True  # cannot scope this node: don't drop the symbol
        candidates = (
            file_node.full_name,
            file_node.name,
            file_node.properties.get("file"),
            file_node.properties.get("path"),
        )
        return any(
            candidate and self.paths_match(candidate, file_path)
            for candidate in candidates
        )

    def find_symbols(self, qualified_name, file_path=None):
        """
        Declaration nodes matching a patch symbol name, scoped to
        ``file_path`` when given. Matches the qualified name exactly or as
        a suffix (the CPG prefixes module/component names, e.g.
        ``app.serve_report.build_file_path``), falling back to a
        bare-name match. Names are cleaned of trailing signatures.
        """
        qualified_name = clean_symbol_name(qualified_name)
        short_name = qualified_name.rsplit(self.delimiter, 1)[-1]
        suffix = self.delimiter + qualified_name

        exact = []
        by_name = []
        for node in self.declarations():
            full_name = clean_symbol_name(node.full_name)
            name = clean_symbol_name(node.name)
            if (
                full_name == qualified_name
                or full_name.endswith(suffix)
                or name == qualified_name
                or name.endswith(suffix)
            ):
                exact.append(node)
            elif (
                full_name.rsplit(self.delimiter, 1)[-1] == short_name
                or name.rsplit(self.delimiter, 1)[-1] == short_name
            ):
                by_name.append(node)

        for candidates in (exact, by_name):
            if not candidates:
                continue
            if not file_path:
                return candidates
            scoped = [node for node in candidates if self.in_file(node, file_path)]
            if scoped:
                return scoped
        return []

    def entry_declarations(self):
        """
        Traversal roots of the codebase: public declarations never
        invoked anywhere in the graph (dunders such as ``__init__`` count
        as public). Falls back to module-level EOG roots when every
        declaration is invoked.
        """
        if self._entries is not None:
            return self._entries

        invoked = set(self.invokers_of)
        entries = []
        for node in self.declarations(self.METHOD_LABELS):
            if node.id in invoked:
                continue
            # The privacy check applies to the bare name: the CPG may
            # prefix module names (``app._secret``).
            name = (
                clean_symbol_name(node.name).rsplit(self.delimiter, 1)[-1] or node.name
            )
            is_private = name.startswith("_") and not (
                name.startswith("__") and name.endswith("__")
            )
            if not is_private:
                entries.append(node)

        if not entries:
            # Fallback: EOG roots outside of any declaration, i.e. the
            # first statements executed at module level.
            declaration_ids = {n.id for n in self.declarations()}
            for node in self.nodes.values():
                if node.is_a(*self.DECLARATION_LABELS):
                    continue
                current = self.parent(node)
                inside_declaration = False
                while current is not None:
                    if current.id in declaration_ids:
                        inside_declaration = True
                        break
                    current = self.parent(current)
                if not inside_declaration and not self.predecessors(node, "EOG"):
                    entries.append(node)

        self._entries = entries
        return entries

    def eog_entries(self, declaration):
        """
        Where evaluation starts inside a declaration: its EOG successors
        (frontends that put the declaration on the EOG), else the EOG roots
        of its subtree (the first statement of its body).
        """
        entries = self.successors(declaration, "EOG")
        if entries:
            return entries
        return [
            node
            for node in self.ast_descendants(declaration)
            if not self.predecessors(node, "EOG")
        ]

    def eog_successors(self, node):
        """
        Evaluation-order successors of a node: EOG edges, entering
        declarations at the start of their body, plus the interprocedural
        hop into called declarations.

        Calls nested inside the node's subtree are also followed: newer
        CPG schemas keep call expressions off the EOG (the EOG runs through
        statements), so a statement's calls must be reached from the
        statement itself.
        """
        if node.is_a(*self.DECLARATION_LABELS):
            successors = list(self.eog_entries(node))
        else:
            successors = list(self.successors(node, "EOG"))
        successors.extend(self.invokes(node))
        for descendant in self.ast_descendants(node):
            successors.extend(self.invokes(descendant))
        return successors


def follow_eog_edges_until_hit(graph, start, predicate, max_steps=1_000_000):
    """
    Follow EOG edges forward from ``start`` (a node or an iterable of nodes)
    until a node satisfies ``predicate``. Simplified
    ``Node.followEOGEdgesUntilHit``:

    - ``Forward(GraphToFollow.EOG)``: walk EOG successors;
    - ``Interprocedural()``: at call expressions, follow INVOKES edges into
      the callee and continue from its body;
    - ``FilterUnreachableEOG``: only nodes reachable from ``start`` are
      visited, so dead code is never entered;
    - ``findAllPossiblePaths = false``: return the first (shortest) path.

    Returns the path of nodes leading to the hit, or ``None``.
    """
    starts = [start] if isinstance(start, Node) else list(start or [])
    parents = {node.id: None for node in starts}
    queue = deque(starts)
    steps = 0

    while queue:
        node = queue.popleft()
        steps += 1
        if steps > max_steps:
            return None

        if predicate(node):
            path = [node]
            while parents[path[-1].id] is not None:
                path.append(parents[path[-1].id])
            path.reverse()
            return path

        for successor in graph.eog_successors(node):
            if successor.id not in parents:
                parents[successor.id] = node
                queue.append(successor)

    return None


class ResourcePatchMatcher:
    """
    Match patch symbols against the CPG graph: find the symbol by name
    (scoped to a file), then check with ``follow_eog_edges_until_hit``
    that it lies on an evaluation path from the codebase entry points.
    """

    def __init__(self, resource_index):
        self.graph = (
            resource_index
            if isinstance(resource_index, Graph)
            else Graph(resource_index or {})
        )
        self.entry_points = self.graph.entry_declarations()
        self._cache = {}

    def match(self, patch_symbols_metadata, file_path=None):
        """
        Return ``{symbol_key: result}`` for each patch symbol that
        belongs to ``file_path`` (or to the file part of its key) and is
        defined in the graph. Results are keyed by the original symbol
        key (``file::name``), preserving the report format.
        """
        results = {}
        for symbol_key, metadata in (patch_symbols_metadata or {}).items():
            if not isinstance(metadata, dict):
                continue

            symbol_file, sep, qualified_name = str(symbol_key).partition("::")
            if not sep:
                qualified_name, symbol_file = symbol_key, None

            # Strip the "#2" duplicate suffix added by the patch collector.
            base, _, suffix = qualified_name.rpartition("#")
            if suffix.isdigit():
                qualified_name = base
            if not qualified_name:
                continue

            # Scope to the resource: the symbol's file must match it.
            if (
                file_path
                and symbol_file
                and not Graph.paths_match(file_path, symbol_file)
            ):
                continue

            cache_key = (qualified_name, symbol_file or file_path)
            if cache_key not in self._cache:
                self._cache[cache_key] = self.match_symbol(
                    qualified_name, symbol_file=symbol_file or file_path
                )
            result = self._cache[cache_key]
            if result:
                results[symbol_key] = result
        return results

    def match_symbol(self, qualified_name, symbol_file=None):
        nodes = self.graph.find_symbols(qualified_name, file_path=symbol_file)
        if not nodes:
            return None

        path = None
        for node in nodes:  # prefer a reachable candidate on name collisions
            path = self.reachable_path(node)
            if path:
                break

        return {
            "symbol_name": qualified_name,
            "is_defined": True,
            "is_reachable": path is not None,
            "eog_path": [node.describe() for node in path] if path else [],
        }

    def reachable_path(self, node):
        """
        EOG path from an entry point to ``node``, or ``None``.

        A class (record) is reachable through any of its members; a symbol
        is reachable when the traversal reaches the declaration itself, a
        node inside it, or a call site that invokes it.
        """
        targets = {node}
        if node.is_a(*Graph.RECORD_LABELS):
            targets.update(self.graph.members(node))

        target_ids = {target.id for target in targets}
        hit_ids = set(target_ids)
        for target in targets:
            hit_ids.update(child.id for child in self.graph.ast_descendants(target))
        for target_id in target_ids:
            hit_ids.update(self.graph.invokers_of.get(target_id, ()))

        return follow_eog_edges_until_hit(
            self.graph,
            self.entry_points,
            predicate=lambda current: current.id in hit_ids,
        )


def classify_reachability(matched_symbols):
    """Classify reachability from the simple matcher results."""
    if not matched_symbols:
        return ReachabilityStatus.NOT_REACHABLE
    if any(m.get("is_reachable") for m in matched_symbols.values()):
        return ReachabilityStatus.REACHABLE
    if any(m.get("is_defined") for m in matched_symbols.values()):
        return ReachabilityStatus.UNKNOWN
    return ReachabilityStatus.NOT_REACHABLE


def match_patches_to_resources(
    patches, patch_symbols, candidate_resources, resource_indexes, logger=None
):
    """
    Match resource symbols against patch symbols.
    """
    project_matcher = None
    legacy_indexes = None
    if isinstance(resource_indexes, Graph) or "nodes" in (resource_indexes or {}):
        project_matcher = ResourcePatchMatcher(resource_indexes)
    elif resource_indexes:
        legacy_indexes = resource_indexes

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
            lang_patch_symbols = patch_symbols_by_language.get(
                resource.programming_language
            )
            if not lang_patch_symbols:
                continue

            vulnerable_symbols = lang_patch_symbols.get("vulnerable", {})
            fixed_symbols = lang_patch_symbols.get("fixed", {})
            if not (vulnerable_symbols or fixed_symbols):
                continue

            matcher = project_matcher
            if matcher is None:
                resource_graph = (
                    legacy_indexes.get(resource.path) if legacy_indexes else None
                )
                if not resource_graph:
                    continue
                matcher = ResourcePatchMatcher(resource_graph)

            vuln_details = matcher.match(vulnerable_symbols, file_path=resource.path)
            fixed_details = matcher.match(fixed_symbols, file_path=resource.path)

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

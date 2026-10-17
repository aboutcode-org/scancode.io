# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations under the
# License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

"""
Reachability analysis using a Neo4j-backed Code Property Graph (CPG).

The CPG is produced by ``cpggen`` and persisted to Neo4j by the
``cpg-neo4j`` exporter from Fraunhofer-AISEC/cpg
(https://fraunhofer-aisec.github.io/cpg/). The graph schema used below
is the one documented at
https://fraunhofer-aisec.github.io/cpg/CPG/specs/graph and is generated
automatically from the in-memory CPG, so the node labels and relationship
types below are the *full* class names (e.g. ``RecordDeclaration``,
``FunctionDeclaration``) and *uppercase underscore-separated* edge types
(e.g. ``RECORD_DECLARATION``, ``INVOKES``).

Before deploying this module against a fresh database, run the helper
``scripts/introspect_neo4j_schema.py`` against the same Neo4j instance to
confirm that the labels and edge types enumerated below are the ones
actually persisted. If you are running an older / renamed CPG export
that uses short node labels (``Record``, ``Function``, ``Method``,
``Constructor``), update ``RECORD_LABELS`` / ``METHOD_LABELS`` accordingly.

Recommended Neo4j indexes (created once per database)::

    CREATE CONSTRAINT IF NOT EXISTS FOR (n:MethodDeclaration)
        REQUIRE elementId(n) IS UNIQUE;
    CREATE INDEX  IF NOT EXISTS FOR (n:FunctionDeclaration)   ON (n.fullName);
    CREATE INDEX  IF NOT EXISTS FOR (n:MethodDeclaration)    ON (n.fullName);
    CREATE INDEX  IF NOT EXISTS FOR (n:RecordDeclaration)    ON (n.fullName);
    CREATE INDEX  IF NOT EXISTS FOR (n:ConstructorDeclaration) ON (n.fullName);
"""

from os import environ

import neo4j

from aboutcode.pipeline import LoopProgress
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import save_resource_reachability_report

CPG_NEO4J_EXECUTABLE = environ.get("CPG_NEO4J_EXECUTABLE")
CPG_NEO4J_HOST = environ.get("CPG_NEO4J_HOST", "localhost")
CPG_NEO4J_PORT = environ.get("CPG_NEO4J_PORT", "7687")
CPG_NEO4J_USER = environ.get("CPG_NEO4J_USER", "neo4j")
CPG_NEO4J_PASSWORD = environ.get("CPG_NEO4J_PASSWORD", "password")

# Node labels -- full class names persisted by cpg-neo4j (Fraunhofer CPG).
# If your database uses the legacy short labels (``Record``, ``Function``,
# ``Method``, ``Constructor``), replace the tuples below with those.
RECORD_LABELS = (
    "RecordDeclaration",
    # ``EnumDeclaration`` extends ``RecordDeclaration`` and can hold
    # constructors / methods (e.g. Java enums with bodies).
    "EnumDeclaration",
)

METHOD_LABELS = (
    "FunctionDeclaration",
    "MethodDeclaration",
    "ConstructorDeclaration",
    # Operators (e.g. C++ ``operator==``) are callable declarations too.
    "OperatorDeclaration",
)

DECLARATION_LABELS = RECORD_LABELS + METHOD_LABELS

# Inter-procedural call edge. ``Call`` nodes (call sites) ``INVOKES`` their
# callee ``FunctionDeclaration``. Documented in the CPG Call node spec.
CALL_REL = "INVOKES"

# Structural (AST) edge types that we are willing to follow when expanding
# the subtree of a target node. These come from the cpg-neo4j graph schema
# (https://fraunhofer-aisec.github.io/cpg/CPG/specs/graph). Edge types
# previously listed here but NOT present in the documented schema
# (``SINGLE_DECLARATION``, ``OPERATOR_BASE``, ``OPERATOR_ARGUMENTS``,
# ``BRANCHED_BY``) have been removed. ``BODY`` was missing and is required
# to traverse from a FunctionDeclaration into its body block.
STRUCTURAL_REL = (
    "AST"
    "|BODY"
    "|DECLARATIONS"
    "|STATEMENTS"
    "|METHODS"
    "|CONSTRUCTORS"
    "|FIELDS"
    "|PARAMETERS"
    "|ARGUMENTS"
    "|INITIALIZER"
    "|INITIALIZERS"
    "|RECEIVER"
    "|LHS|RHS"
    "|KEY|VALUE"
    "|ARRAY_EXPRESSION"
    "|SUBSCRIPT_EXPRESSION"
    "|INPUT"
    "|CONDITION"
    "|THEN_STATEMENT"
    "|ELSE_STATEMENT"
    "|RECORD_DECLARATION"
    "|DEFINES"
)
EOG_AND_CALL_REL = f"EOG|{CALL_REL}"

# Visibility values used to exclude private / inaccessible entry points.
# NOTE: the documented Fraunhofer CPG schema does NOT persist a ``visibility``
# property on the Node base class -- visibility is normally expressed via
# ``Modifier`` AST children. If ``n.visibility`` is NULL on your database,
# the filter below is a no-op; consider replacing it with a Modifier-based
# check (see fetch_entry_point_ids).
PRIVATE_VISIBILITIES = ("PROTECTED", "PRIVATE", "PACKAGE", "INTERNAL")

MAX_PATH_LENGTH = 50
MAX_SUBTREE_DEPTH = 15


def clean_symbol_name(name):
    """Normalize a CPG symbol name by removing ()"""
    local, sep, qualifier = name.rpartition("()")
    if not sep:
        return name
    if not qualifier:
        return local
    if not local:
        return qualifier
    return f"{qualifier}.{local}"


def clean_path(path):
    """
    Normalize a file path: backslashes to slashes, strip trailing slashes
    and the ``file://`` / ``file:`` URI scheme
    """
    path = str(path).replace("\\", "/").rstrip("/")
    return path.removeprefix("file://").removeprefix("file:")


def paths_match(a, b):
    """
    Check whether two file paths denote the same file, allowing one to
    be longer than the other (resource path vs CPG file path).
    """
    a, b = clean_path(a), clean_path(b)
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def describe_node(node):
    """Return an identifier for a node"""
    full_name = node.get("fullName") or ""
    name = node.get("name") or ""
    return (
        clean_symbol_name(full_name)
        or clean_symbol_name(name)
        or f"node-{node.element_id}"
    )


def fetch_declarations(session):
    """
    All non-inferred declaration nodes of the graph, as dicts with the
    node_id, labels, name, full_name, file location (the ``artifact``
    property; the schema also lists ``file`` as a fallback) and
    name_delimiter used for symbol matching.
    """
    query = """
        MATCH (n)
        WHERE any(label IN $labels WHERE label IN labels(n))
          AND NOT coalesce(n.isInferred, false)
        RETURN elementId(n) AS node_id,
               labels(n) AS labels,
               n.name AS name,
               n.fullName AS full_name,
               coalesce(n.artifact, n.file, '') AS file,
               n.nameDelimiter AS name_delimiter
    """
    return list(session.run(query, labels=list(DECLARATION_LABELS)))


def fetch_entry_point_ids(session):
    """
    Traversal roots of the codebase: public method-like declarations never
    invoked anywhere in the graph, as element ids.

    A node qualifies as an entry point when ALL of the following hold:
      * it is a FunctionDeclaration / MethodDeclaration /
        ConstructorDeclaration / OperatorDeclaration;
      * it has a ``BODY`` (i.e. it actually holds executable code -- this
        excludes abstract methods and interface declarations);
      * nothing in the graph ``INVOKES`` it (no internal caller);
      * it is not an inferred stub (``isInferred``);
      * it is not declared private / protected / package-private.

    The visibility check uses ``n.visibility`` defensively -- if your
    CPG does not populate that property (the documented schema does not
    list it as a Node property; visibility is normally stored as ``Modifier``
    AST children), the check is a no-op and you may want to replace it
    with::

        AND NOT EXISTS {
            MATCH (n)-[:AST]->(m:Modifier)
            WHERE toUpper(m.type) IN ['PRIVATE','PROTECTED','PACKAGE','INTERNAL']
        }
    """
    query = f"""
        MATCH (n)
        WHERE any(label IN $labels WHERE label IN labels(n))
          AND (n)-[:BODY]->()
          AND NOT ()-[:{CALL_REL}]->(n)
          AND NOT coalesce(n.isInferred, false)
          AND NOT (toUpper(coalesce(n.visibility, '')) IN $private)
        RETURN elementId(n) AS node_id
    """
    return [
        record["node_id"]
        for record in session.run(
            query, labels=list(METHOD_LABELS), private=list(PRIVATE_VISIBILITIES)
        )
    ]


def fetch_record_member_ids(session, record_id):
    """
    Return method-like declarations structurally contained
    in or linked to the given record.

    Two traversal patterns are used, following the cpg-neo4j schema:
      * downward AST traversal from the record through ``METHODS``,
        ``CONSTRUCTORS`` (and any nested ``RECORDS`` / ``STATEMENTS``) to
        pick up methods declared inside the record body;
      * the ``RECORD_DECLARATION`` back-edge, picking up methods declared
        outside the record body that still refer back to it (common in C++,
        where member definitions live in a separate translation unit).
    """
    query = f"""
        MATCH (r) WHERE elementId(r) = $record_id
        MATCH (m)
        WHERE (
                (r)-[:{STRUCTURAL_REL}*1..{MAX_SUBTREE_DEPTH}]->(m)
                OR (m)-[:RECORD_DECLARATION]->(r)
              )
          AND any(label IN $labels WHERE label IN labels(m))
        RETURN DISTINCT elementId(m) AS node_id
    """
    return [
        record["node_id"]
        for record in session.run(
            query, record_id=record_id, labels=list(METHOD_LABELS)
        )
    ]


def fetch_subtree_ids(session, node_ids):
    """
    Return the element IDs of the given nodes and their structural descendants.

    Includes the nodes themselves (depth 0). ``BODY`` is now part of
    STRUCTURAL_REL so the traversal can enter a FunctionDeclaration's body
    block when computing the set of "reachable inside" nodes for a target.
    """
    query = f"""
        MATCH (t)-[:{STRUCTURAL_REL}*0..{MAX_SUBTREE_DEPTH}]->(d)
        WHERE elementId(t) IN $node_ids
        RETURN DISTINCT elementId(d) AS node_id
    """
    return {record["node_id"] for record in session.run(query, node_ids=list(node_ids))}


def fetch_invoker_ids(session, node_id):
    """
    Element ids of the call-expression nodes invoking the given node.

    ``INVOKES`` edges go from a ``Call`` (call site) to its callee
    ``FunctionDeclaration``. Returned ids are the call sites, which are
    added to the hit set so the reachability query can terminate at the
    call site rather than only at the callee signature itself.
    """
    query = f"""
        MATCH (invoker)-[:{CALL_REL}]->(t)
        WHERE elementId(t) = $node_id
        RETURN DISTINCT elementId(invoker) AS invoker_id
    """
    return [record["invoker_id"] for record in session.run(query, node_id=node_id)]


def find_reachability_path(session, entry_ids, hit_ids):
    """
    Shortest evaluation path from any entry point to any hit_ids node,
    following EOG edges plus the inter-procedural ``INVOKES`` edges, as the
    list of node identifiers of the path, or None.

    The query binds entry and hit nodes through ``elementId()`` (indexed by
    default in Neo4j 5+) and uses an explicit depth-bounded variable-length
    pattern. ``ORDER BY length(path) LIMIT 1`` returns the shortest path
    found within the depth bound -- this is the most portable form across
    Neo4j versions; for very large graphs you may switch to ``shortestPath``
    or GDS ``gds.shortestPath.yens.stream`` once indexes and constraints are
    in place.
    """
    if not entry_ids or not hit_ids:
        return None

    query = f"""
        MATCH (entry) WHERE elementId(entry) IN $entry_ids
        MATCH (hit)   WHERE elementId(hit)   IN $hit_ids
        MATCH path = (entry)-[:{EOG_AND_CALL_REL}*0..{MAX_PATH_LENGTH}]->(hit)
        RETURN path, length(path) AS len
        ORDER BY len
        LIMIT 1
    """
    records = list(session.run(query, entry_ids=list(entry_ids), hit_ids=list(hit_ids)))
    if not records:
        return None
    return [describe_node(node) for node in records[0]["path"].nodes]


class ResourcePatchMatcher:
    """
    Match patch symbols against the CPG in Neo4j: find the symbol by name
    (scoped to a file), then check with a Cypher path query that it lies
    on an evaluation path from the codebase entry points.
    """

    def __init__(self, neo4j_session):
        self.session = neo4j_session
        self.declarations = fetch_declarations(neo4j_session)
        self.entry_point_ids = fetch_entry_point_ids(neo4j_session)
        self.delimiter = next(
            (
                declaration["name_delimiter"]
                for declaration in self.declarations
                if declaration["name_delimiter"]
            ),
            ".",
        )
        self._cache = {}

    def in_file(self, declaration, file_path):
        """
        Check whether the declaration is in the file matching
        file_path.
        """
        file = declaration["file"]
        if not file:
            # A declaration without a known file is treated as belonging
            # to every file. This is permissive on purpose so that symbols
            # whose CPG node was inferred / lacks an ``artifact`` still
            # match -- but you may want to tighten this if your database
            # always sets ``artifact``.
            return True
        return paths_match(file, file_path)

    def find_symbols(self, qualified_name, file_path=None):
        """
        Find declarations matching a patch symbol name, scoped to
        file_path when given. Matches the qualified name exactly or as
        a suffix (the CPG prefixes module names, e.g.
        app.serve_report), falling back to a bare-name match. Inferred
        stubs for external callees are never matched: patch symbols always
        refer to code in the scanned codebase.
        """
        qualified_name = clean_symbol_name(qualified_name)
        short_name = qualified_name.rsplit(self.delimiter, 1)[-1]
        suffix = self.delimiter + qualified_name

        exact, by_name = [], []
        for declaration in self.declarations:
            names = [
                clean_symbol_name(declaration["full_name"] or ""),
                clean_symbol_name(declaration["name"] or ""),
            ]
            if any(name == qualified_name or name.endswith(suffix) for name in names):
                exact.append(declaration)
            elif any(
                name.rsplit(self.delimiter, 1)[-1] == short_name for name in names
            ):
                by_name.append(declaration)

        for candidates in (exact, by_name):
            if not candidates:
                continue
            if not file_path:
                return candidates
            scoped = [
                declaration
                for declaration in candidates
                if self.in_file(declaration, file_path)
            ]
            if scoped:
                return scoped
        return []

    def match(self, patch_symbols_metadata, file_path=None):
        """
        Return {symbol_key: result} for each patch symbol that
        belongs to file_path (or to the file part of its key) and is
        defined in the graph. Results are keyed by the original symbol
        key (file::name), preserving the report format.
        """
        results = {}
        for symbol_key, metadata in (patch_symbols_metadata or {}).items():
            if not isinstance(metadata, dict):
                continue

            symbol_file, sep, qualified_name = str(symbol_key).partition("::")
            if not sep:
                qualified_name, symbol_file = symbol_key, None

            if not qualified_name:
                continue

            if file_path and symbol_file and not paths_match(file_path, symbol_file):
                continue

            symbol_file = symbol_file or file_path
            cache_key = (qualified_name, symbol_file)
            if cache_key not in self._cache:
                self._cache[cache_key] = self.match_symbol(
                    qualified_name, symbol_file=symbol_file
                )
            result = self._cache[cache_key]
            if result:
                results[symbol_key] = result
        return results

    def match_symbol(self, qualified_name, symbol_file=None):
        """Match a symbol in the graph and evaluates its reachability."""
        declarations = self.find_symbols(qualified_name, file_path=symbol_file)
        if not declarations:
            return None

        path = None
        for declaration in declarations:
            path = self.reachable_path(declaration)
            if path:
                break

        return {
            "symbol_name": qualified_name,
            "is_defined": True,
            "is_reachable": path is not None,
            "eog_path": path or [],
        }

    def reachable_path(self, declaration):
        """
        Evaluate the path from an entry point to the declaration.

        A symbol is reachable when the traversal reaches the declaration
        itself, a node inside it (its subtree, now including its body),
        or a call site that invokes it.
        """
        target_ids = {declaration["node_id"]}
        if any(label in RECORD_LABELS for label in declaration["labels"]):
            target_ids.update(
                fetch_record_member_ids(self.session, declaration["node_id"])
            )

        hit_ids = fetch_subtree_ids(self.session, target_ids)
        for target_id in target_ids:
            hit_ids.update(fetch_invoker_ids(self.session, target_id))

        return find_reachability_path(self.session, self.entry_point_ids, hit_ids)


def classify_reachability(matched_symbols):
    """Classify reachability from the matcher results."""
    if not matched_symbols:
        return ReachabilityStatus.NOT_REACHABLE

    values = matched_symbols.values()
    if any(matched.get("is_reachable") for matched in values):
        return ReachabilityStatus.REACHABLE

    if any(matched.get("is_defined") for matched in values):
        return ReachabilityStatus.UNKNOWN
    return ReachabilityStatus.NOT_REACHABLE


def match_patches_to_resources(
    tool_name,
    patches,
    patch_symbols,
    candidate_resources,
    logger=None,
):
    """Match resource symbols against patch symbols."""
    driver = neo4j.GraphDatabase.driver(
        f"bolt://{CPG_NEO4J_HOST}:{CPG_NEO4J_PORT}",
        auth=(CPG_NEO4J_USER, CPG_NEO4J_PASSWORD),
    )
    try:
        with driver.session() as neo4j_session:
            project_matcher = ResourcePatchMatcher(neo4j_session)
            patch_progress = LoopProgress(len(patches), logger=logger)
            for patch in patch_progress.iter(patches):
                vcs_url = patch.get("vcs_url")
                commit_hash = patch.get("commit_hash")
                advisory_uids = patch.get("advisory_uids", [])

                patch_symbols_by_language = patch_symbols.get(commit_hash, {})
                if not patch_symbols_by_language:
                    continue

                for resource in candidate_resources:
                    by_language = {
                        str(language).lower(): symbols
                        for language, symbols in patch_symbols_by_language.items()
                    }
                    lang_patch_symbols = by_language.get(
                        str(resource.programming_language or "").lower()
                    )
                    if not lang_patch_symbols:
                        continue

                    vulnerable_symbols = lang_patch_symbols.get("vulnerable", {})
                    fixed_symbols = lang_patch_symbols.get("fixed", {})
                    if not (vulnerable_symbols or fixed_symbols):
                        continue

                    vuln_details = project_matcher.match(
                        vulnerable_symbols, file_path=resource.path
                    )
                    fixed_details = project_matcher.match(
                        fixed_symbols, file_path=resource.path
                    )
                    if not (vuln_details or fixed_details):
                        continue

                    report = {
                        "tool_name": tool_name,
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
    finally:
        driver.close()

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

RECORD_LABELS = (
    "Record",
    "Enumeration",
    "RecordDeclaration",
    "ClassDeclaration",
    "EnumDeclaration",
)

METHOD_LABELS = (
    "Function",
    "Method",
    "Constructor",
    "FunctionDeclaration",
    "MethodDeclaration",
    "ConstructorDeclaration",
)
DECLARATION_LABELS = RECORD_LABELS + METHOD_LABELS

CALL_REL = "INVOKES"

STRUCTURAL_REL = (
    "AST|DECLARATIONS|SINGLE_DECLARATION|STATEMENTS"
    "|METHODS|CONSTRUCTORS"
    "|PARAMETERS|ARGUMENTS|INITIALIZERS|RECEIVER"
    "|OPERATOR_BASE|OPERATOR_ARGUMENTS"
    "|LHS|RHS|KEY|VALUE"
    "|ARRAY_EXPRESSION|SUBSCRIPT_EXPRESSION|BRANCHED_BY"
)
EOG_AND_CALL_REL = f"EOG|{CALL_REL}"

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
    and the ``file://`` / ``file:`` URI scheme (the cpg exporter emits
    single-slash ``file:/...`` artifacts).
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
    property: this export has no ``file`` property) and name_delimiter
    used for symbol matching.
    """
    query = """
        MATCH (n)
        WHERE any(label IN $labels WHERE label IN labels(n))
          AND NOT coalesce(n.isInferred, false)
        RETURN elementId(n) AS node_id,
               labels(n) AS labels,
               n.name AS name,
               n.fullName AS full_name,
               coalesce(n.artifact, '') AS file,
               n.nameDelimiter AS name_delimiter
    """
    return list(session.run(query, labels=list(DECLARATION_LABELS)))


def fetch_entry_point_ids(session):
    """
    Traversal roots of the codebase: public method-like declarations never
    invoked anywhere in the graph, as element ids.
    """
    query = f"""
        MATCH (n)
        WHERE any(label IN $labels WHERE label IN labels(n))
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
    """Return method-like declarations structurally contained in or linked to the given record."""
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
    """Return the element IDs of the given nodes and their structural descendants."""
    query = f"""
        MATCH (t)-[:{STRUCTURAL_REL}*0..{MAX_SUBTREE_DEPTH}]->(d)
        WHERE elementId(t) IN $node_ids
        RETURN DISTINCT elementId(d) AS node_id
    """
    return {record["node_id"] for record in session.run(query, node_ids=list(node_ids))}


def fetch_invoker_ids(session, node_id):
    """Element ids of the call-expression nodes invoking the given node."""
    query = f"""
        MATCH (invoker)-[:{CALL_REL}]->(t)
        WHERE elementId(t) = $node_id
        RETURN DISTINCT elementId(invoker) AS invoker_id
    """
    return [record["invoker_id"] for record in session.run(query, node_id=node_id)]


def find_reachability_path(session, entry_ids, hit_ids):
    """
    Shortest evaluation path from an entry point to any hit_ids node,
    following EOG edges plus the interprocedural call edges, as the list of
    node identifiers of the path, or None.
    Replaces follow_eog_edges_until_hit: the traversal runs inside Neo4j.
    """
    query = f"""
        MATCH path = (entry)-[:{EOG_AND_CALL_REL}*0..{MAX_PATH_LENGTH}]->(hit)
        WHERE elementId(entry) IN $entry_ids AND elementId(hit) IN $hit_ids
        RETURN path
        ORDER BY length(path)
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
        file_path. Declarations without any file location are not
        excluded: dropping them would silently lose symbols.
        """
        file = declaration["file"]
        if not file:
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
        Evaluate the path from an entry point to the declaration

        A symbol is reachable when the traversal reaches the declaration itself, a
        node inside it, or a call site that invokes it.
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

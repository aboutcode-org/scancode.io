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
    and the ``file://`` / ``file:`` URI scheme.
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


EOG_PATH_QUERY = """
MATCH (entry)
WHERE any(label IN ['Function', 'Method', 'Constructor', 'Operator']
WHERE label IN labels(entry))
  AND NOT ()-[:INVOKES]->(entry)
  AND NOT toUpper(coalesce(entry.modifier, entry.access, ''))
  IN ['PROTECTED', 'PRIVATE', 'PACKAGE', 'INTERNAL']
  AND (coalesce(entry.isDefinition, false)
  OR (entry)-[:STATEMENTS|AST|FIRST_BASIC_BLOCK]->())
WITH entry
MATCH (target)
WHERE any(label IN ['Function', 'Method', 'Constructor', 'Operator', 'Record', 'Enum']
WHERE label IN labels(target))
  AND (target.fullName ENDS WITH $clean_target OR target.name = $short_target)

WITH entry, target, coalesce(target.artifact, target.fileName, target.path, '')
AS target_path
WHERE $file_path IS NULL
   OR target_path = $file_path
   OR target_path ENDS WITH ('/' + $file_path)
   OR $file_path ENDS WITH ('/' + target_path)

MATCH path = shortestPath((entry)-[:EOG|INVOKES*0..50]->(target))
RETURN [n IN nodes(path) | coalesce(n.fullName, n.name, elementId(n))] AS path_nodes
LIMIT 1
"""


SYMBOL_EXISTS_QUERY = """
MATCH (target)
WHERE any(label IN ['Function', 'Method', 'Constructor', 'Operator', 'Record', 'Enum']
WHERE label IN labels(target))
  AND (target.fullName ENDS WITH $clean_target OR target.name = $short_target)
RETURN count(target) > 0 AS exists
"""


def find_eog_path(session, clean_target, short_target, file_path=None):
    """
    Return the shortest EOG/INVOKES path from a valid entry point to the
    target symbol, as a list of node names, or None when no such path
    exists.
    """
    record = session.run(
        EOG_PATH_QUERY,
        clean_target=clean_target,
        short_target=short_target,
        file_path=file_path,
    ).single()

    if record:
        return record["path_nodes"]
    return None


def symbol_exists(session, clean_target, short_target):
    """
    Return True when at least one declaration node of the codebase matches
    the symbol name.
    """
    record = session.run(
        SYMBOL_EXISTS_QUERY,
        clean_target=clean_target,
        short_target=short_target,
    ).single()
    return bool(record["exists"])


def check_symbol_reachability(session, target_name, file_path=None):
    """
    Determine whether a symbol is reachable from any valid entry point of
    the codebase.
    """
    clean_target = clean_symbol_name(target_name)
    short_target = clean_target.split(".")[-1]
    cleaned_file_path = clean_path(file_path) if file_path else None

    eog_path = None
    if cleaned_file_path:
        eog_path = find_eog_path(session, clean_target, short_target, cleaned_file_path)

    if eog_path is None:
        eog_path = find_eog_path(session, clean_target, short_target)

    if eog_path is not None:
        return {
            "symbol_name": target_name,
            "is_defined": True,
            "is_reachable": True,
            "eog_path": eog_path,
        }

    return {
        "symbol_name": target_name,
        "is_defined": symbol_exists(session, clean_target, short_target),
        "is_reachable": False,
        "eog_path": [],
    }


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


def split_symbol_key(symbol_key):
    """
    Split a file.py::qualified.name patch symbol key into its
    qualified name and file.
    """
    symbol_file, sep, qualified_name = str(symbol_key).partition("::")
    if not sep:
        return symbol_key, None
    return qualified_name, symbol_file


def get_language_patch_symbols(patch_symbols_by_language, resource):
    """
    Return the patch symbols of the programming language of the
    resource, or None when the patch has none for that language.
    """
    by_language = {
        str(language).lower(): symbols
        for language, symbols in patch_symbols_by_language.items()
    }
    language = str(resource.programming_language or "").lower()
    return by_language.get(language)


def collect_symbol_details(session, symbols, resource, query_cache):
    """
    Collect the CPG reachability details of the patch symbols that are
    defined in the codebase for the given resource, keyed by symbol
    key.
    """
    details = {}
    for symbol_key, metadata in symbols.items():
        if not isinstance(metadata, dict):
            continue

        qualified_name, symbol_file = split_symbol_key(symbol_key)
        if not qualified_name:
            continue

        target_file = symbol_file or resource.path
        cache_key = (qualified_name, target_file)

        if cache_key not in query_cache:
            query_cache[cache_key] = check_symbol_reachability(
                session, qualified_name, target_file
            )

        result = query_cache[cache_key]
        if result and result["is_defined"]:
            details[symbol_key] = result

    return details


def match_resource_patch_symbols(
    session,
    tool_name,
    patch,
    patch_symbols_by_language,
    resource,
    query_cache,
):
    """
    Match the patch symbols against the symbols of a single ``resource``
    and save the resulting reachability report.
    """
    lang_patch_symbols = get_language_patch_symbols(patch_symbols_by_language, resource)
    vulnerable_symbols = (lang_patch_symbols or {}).get("vulnerable", {})
    fixed_symbols = (lang_patch_symbols or {}).get("fixed", {})
    if not (vulnerable_symbols or fixed_symbols):
        return

    vuln_details = collect_symbol_details(
        session, vulnerable_symbols, resource, query_cache
    )
    fixed_details = collect_symbol_details(
        session, fixed_symbols, resource, query_cache
    )
    if not (vuln_details or fixed_details):
        return

    commit_hash = patch.get("commit_hash")
    vcs_url = patch.get("vcs_url")
    report = {
        "tool_name": tool_name,
        "patch": {
            "vcs_url": vcs_url,
            "commit_hash": commit_hash,
        },
        "advisory_uids": patch.get("advisory_uids", []),
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

    query_cache = {}
    try:
        with driver.session() as neo4j_session:
            patch_progress = LoopProgress(len(patches), logger=logger)
            logger(f"patches={len(patches)} candidates={len(candidate_resources)}")

            for patch in patch_progress.iter(patches):
                patch_symbols_by_language = patch_symbols.get(
                    patch.get("commit_hash"), {}
                )
                if not patch_symbols_by_language:
                    continue

                for resource in candidate_resources:
                    match_resource_patch_symbols(
                        session=neo4j_session,
                        tool_name=tool_name,
                        patch=patch,
                        patch_symbols_by_language=patch_symbols_by_language,
                        resource=resource,
                        query_cache=query_cache,
                    )
    finally:
        driver.close()

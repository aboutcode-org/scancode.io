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

from aboutcode.pipeline import LoopProgress
from scanpipe.pipes.reachability import save_resource_reachability_report, ReachabilityStatus


_NAME_FIELDS = ("name", "fullName", "typeFullName", "resolvedMethod")


def classify_reachability(vuln_details, fixed_details):
    """Classify the reachability of a patch from its matched symbols.

    ``vuln_details`` and ``fixed_details`` are ``{symbol: [occurrence, ...]}``
    mappings produced by :class:`ResourcePatchMatcher`. Only the vulnerable
    symbols drive the verdict:

    - REACHABLE: a vulnerable symbol is called, or is flagged as reachable
      by the analyzer.
    - UNKNOWN: a vulnerable symbol occurrence is present but no call site
      was recorded, so the absence of a call proves nothing.
    - NOT_REACHABLE: no vulnerable symbol occurrence was matched.

    ``fixed_details`` are recorded in the report but do not change the
    reachability verdict. This function is a pure function of the occurrence
    data and makes no distinction between production and test code.
    """
    vuln_occurrences = [
        occurrence
        for occurrences in (vuln_details or {}).values()
        for occurrence in occurrences
    ]

    if any(o["is_call"] or o["is_reachable"] for o in vuln_occurrences):
        return ReachabilityStatus.REACHABLE
    if vuln_occurrences:
        return ReachabilityStatus.UNKNOWN
    return ReachabilityStatus.NOT_REACHABLE


class ResourcePatchMatcher:
    """Match patch symbols against the atom slices of a single resource."""

    def __init__(self, resource_index):
        self.resource_index = resource_index or {}
        self.occurrences = self._collect_occurrences()

    def match(self, symbols):
        """Return ``{symbol: [occurrence, ...]}`` for symbols found in the resource."""
        if not symbols:
            return {}
        names = symbols.keys() if isinstance(symbols, dict) else symbols
        return {
            name: occurrences
            for name, occurrences in (
                (name, self._find_occurrences(name)) for name in names
            )
            if occurrences
        }

    def _collect_occurrences(self):
        occurrences = []
        for slice_obj in self.resource_index.get("objectSlices") or []:
            occurrences.extend(self._occurrences_from_slice(slice_obj))
        for user_type in self.resource_index.get("userDefinedTypes") or []:
            occurrence = _make_occurrence(
                source=user_type,
                file_name=user_type.get("fileName") or "",
                kind="definition",
                is_call=False,
                is_reachable=bool(user_type.get("reachable")),
            )
            if occurrence:
                occurrences.append(occurrence)
        return occurrences

    def _occurrences_from_slice(self, slice_obj):
        file_name = slice_obj.get("fileName") or ""
        occurrences = []

        definition = _make_occurrence(
            source=slice_obj,
            file_name=file_name,
            kind="definition",
            is_call=False,
            is_reachable=bool(slice_obj.get("reachable")),
        )
        if definition:
            occurrences.append(definition)

        for usage in slice_obj.get("usages") or []:
            target = usage.get("targetObj") or {}
            label = (target.get("label") or "").upper()
            occurrence = _make_occurrence(
                source=target,
                file_name=target.get("fileName") or file_name,
                kind="call" if label == "CALL" else "usage",
                is_call=label == "CALL",
                is_reachable=bool(usage.get("reachable") or target.get("reachable")),
            )
            if occurrence:
                occurrences.append(occurrence)

        return occurrences

    def _find_occurrences(self, symbol):
        return [
            occurrence
            for occurrence in self.occurrences
            if any(_matches_symbol(name, symbol) for name in occurrence["names"])
        ]


def _make_occurrence(source, file_name, kind, is_call, is_reachable=False):
    names = [source[field] for field in _NAME_FIELDS if source.get(field)]
    if not names:
        return None
    return {
        "names": names,
        "kind": kind,
        "is_call": is_call,
        "is_reachable": is_reachable,
        "fileName": file_name,
        "lineNumber": source.get("lineNumber"),
        "columnNumber": source.get("columnNumber"),
    }


def _matches_symbol(name, symbol):
    """Dot-boundary suffix match in either direction.

    ``symbol`` may carry a ``path::QualifiedName`` prefix, as patch-symbol keys
    do (e.g.
    ``b2sdk/account_info/sqlite_account_info.py::SqliteAccountInfo._create_database``);
    the prefix is stripped before comparing. ``name`` is a bare
    (``_create_database``) or dotted (``SqliteAccountInfo._create_database``)
    atom name. A match happens when ``name == symbol``, ``name`` ends with
    ``.symbol``, or ``symbol`` ends with ``.name`` — the reverse direction
    matters when patch symbols are fully qualified while atom records only the
    bare name.
    """
    if not name or not symbol:
        return False
    if "::" in symbol:
        symbol = symbol.split("::", 1)[1]
    return (
        name == symbol
        or name.endswith("." + symbol)
        or symbol.endswith("." + name)
    )


def _normalize_path(path):
    path = (path or "").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def _find_resource_index(slices_by_file, resource):
    """Look up the slices for a resource, tolerating path prefix / basename diffs."""
    path = _normalize_path(resource.path)
    if not path:
        return None
    if path in slices_by_file:
        return slices_by_file[path]
    for file_name, index in slices_by_file.items():
        if _normalize_path(file_name) == path:
            return index
    base_name = path.rsplit("/", 1)[-1]
    for file_name, index in slices_by_file.items():
        if _normalize_path(file_name).rsplit("/", 1)[-1] == base_name:
            return index
    return None


def collect_and_match_resources(
    tool_name, patches, patch_symbols, resource_indexes, candidate_resources, logger=None
):
    """Match resource symbols against patch symbols and save reachability reports.

    Every candidate resource is analyzed, regardless of whether it lives in a
    test directory: the matcher and classifier operate purely on atom
    occurrences (``is_call`` / ``is_reachable``) and make no production-vs-test
    distinction.
    """

    resource_indexes = resource_indexes or {}
    slices_by_file = {}
    for slice_obj in resource_indexes.get("objectSlices") or []:
        file_name = slice_obj.get("fileName")
        if file_name:
            slices_by_file.setdefault(
                file_name, {"objectSlices": [], "userDefinedTypes": []}
            )["objectSlices"].append(slice_obj)
    for user_type in resource_indexes.get("userDefinedTypes") or []:
        file_name = user_type.get("fileName")
        if file_name:
            slices_by_file.setdefault(
                file_name, {"objectSlices": [], "userDefinedTypes": []}
            )["userDefinedTypes"].append(user_type)

    candidates = list(candidate_resources)
    stats = {
        "no_patch_symbols": 0,
        "no_index": 0,
        "no_lang": 0,
        "no_match": 0,
        "saved": 0,
    }

    if logger:
        logger(
            f"atom match: {len(slices_by_file)} slice files, "
            f"{len(candidates)} candidate resources, "
            f"{len(patch_symbols)} commits with symbols"
        )

    patch_progress = LoopProgress(len(patches), logger=logger)

    for patch in patch_progress.iter(patches):
        vcs_url = patch.get("vcs_url")
        commit_hash = patch.get("commit_hash")
        advisory_uids = patch.get("advisory_uids", [])

        patch_symbols_by_language = patch_symbols.get(commit_hash, {})
        if not patch_symbols_by_language:
            stats["no_patch_symbols"] += 1
            continue

        for resource in candidates:
            resource_index = _find_resource_index(slices_by_file, resource)
            if not resource_index:
                stats["no_index"] += 1
                continue

            lang_patch_symbols = patch_symbols_by_language.get(
                resource.programming_language
            )
            if not lang_patch_symbols:
                target = (resource.programming_language or "").strip().lower()
                lang_patch_symbols = next(
                    (
                        value
                        for key, value in patch_symbols_by_language.items()
                        if target and (key or "").strip().lower() == target
                    ),
                    {},
                )
            if not lang_patch_symbols:
                stats["no_lang"] += 1
                continue

            vulnerable_symbols = lang_patch_symbols.get("vulnerable", {})
            fixed_symbols = lang_patch_symbols.get("fixed", {})

            matcher = ResourcePatchMatcher(resource_index=resource_index)
            vuln_details = matcher.match(vulnerable_symbols)
            fixed_details = matcher.match(fixed_symbols)

            if not any([vuln_details, fixed_details]):
                stats["no_match"] += 1
                continue

            stats["saved"] += 1

            reachability_status = classify_reachability(vuln_details, fixed_details)
            report = {
                "tool_name": tool_name,
                "patch": {"vcs_url": vcs_url, "commit_hash": commit_hash},
                "advisory_uids": advisory_uids,
                "tool_details": vuln_details,
                "fixed_symbols": fixed_symbols,
                "vulnerable_symbols": vulnerable_symbols,
                "is_reachable": reachability_status,
            }
            save_resource_reachability_report(
                resource=resource,
                commit_hash=commit_hash,
                vcs_url=vcs_url,
                new_report=report,
            )

    if logger:
        logger(f"atom match stats: {stats}")
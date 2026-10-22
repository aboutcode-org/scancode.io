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

import re
from collections import defaultdict

from aboutcode.pipeline import LoopProgress
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import save_resource_reachability_report

_OPERATOR_PREFIXES = ("<operator>", "<operators>")
_MARKER_PATTERN = re.compile(r"<[^>]+>")

def normalize_file_path(path):
    """Return ``path`` as a normalized forward-slash relative path."""
    path = (path or "").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")

def normalize_symbol_name(name):
    """Convert an atom name to a comparable dotted form, or ``""`` if unusable."""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    if not name or name.startswith(_OPERATOR_PREFIXES):
        return ""

    if "::" in name:
        name = name.partition("::")[2]

    if ":" in name:
        # Convert ``pkg/mod.py:<module>.Class.method`` to ``pkg.mod.Class.method``.
        path, _, tail = name.partition(":")
        path = normalize_file_path(path).removesuffix(".py")
        name = path.replace("/", ".") + "." + tail

    name = _MARKER_PATTERN.sub("", name)

    while ".." in name:
        name = name.replace("..", ".")

    return name.strip(".")

class SliceMatcher:
    """Index the dotted symbol names of an atom slice, grouped by file."""

    def __init__(self, slices):
        self.by_file = defaultdict(set)
        self.by_basename = defaultdict(set)
        if slices:
            self.parse_slice(slices)

    @property
    def file_count(self):
        """Return the number of files indexed in this slice."""
        return len(self.by_file)

    def parse_slice(self, slices):
        """Populate the indexes from ``slices``. Subclasses must implement this."""
        raise NotImplementedError

    def add_symbols(self, file_name, *names):
        """Index each symbol in ``names`` under ``file_name``, in dotted form."""
        if not isinstance(file_name, str) or not file_name:
            return

        path = normalize_file_path(file_name)
        basename = path.rsplit("/", 1)[-1]
        for name in names:
            dotted = normalize_symbol_name(name)
            if dotted:
                self.by_file[path].add(dotted)
                self.by_basename[basename].add(dotted)

    def match_symbols(self, symbols, file_name):
        """Return the subset of ``symbols`` present in the slice for ``file_name``."""
        if not symbols:
            return set()

        path = normalize_file_path(file_name)
        names = self.by_file.get(path) or self.by_basename.get(path.rsplit("/", 1)[-1])
        if not names:
            return set()

        matched = set()
        for symbol in symbols:
            dotted = normalize_symbol_name(symbol)
            if not dotted:
                continue

            if any(
                    name == dotted
                    or name.endswith("." + dotted)
                    or ("." in name and dotted.endswith("." + name))
                    for name in names
            ):
                matched.add(symbol)

        return matched

class UsagesMatcher(SliceMatcher):
    """Index the usages slice (objectSlices / userDefinedTypes)."""

    def parse_slice(self, slices):
        if not isinstance(slices, dict):
            return

        for obj in slices.get("objectSlices") or []:
            self.add_object_slice(obj or {})

        for typ in slices.get("userDefinedTypes") or []:
            self.add_user_defined_type(typ or {})

    def add_object_slice(self, obj):
        """Index the symbols of one ``objectSlices`` entry."""
        file_name = obj.get("fileName")
        self.add_symbols(file_name, obj.get("fullName"))
        for usage in obj.get("usages") or []:
            usage = usage or {}

            for part in (usage.get("targetObj"), usage.get("definedBy")):
                part = part or {}
                self.add_symbols(
                    file_name,
                    part.get("name"),
                    part.get("typeFullName"),
                    part.get("resolvedMethod"),
                )

            for call in (usage.get("argToCalls") or []) + (
                usage.get("invokedCalls") or []
            ):
                call = call or {}
                self.add_symbols(
                    file_name, call.get("callName"), call.get("resolvedMethod")
                )

    def add_user_defined_type(self, typ):
        """Index the symbols of one ``userDefinedTypes`` entry."""
        file_name = typ.get("fileName")
        self.add_symbols(file_name, typ.get("name"))

        for field in typ.get("fields") or []:
            field = field or {}
            self.add_symbols(
                file_name,
                field.get("name"),
                field.get("typeFullName"),
                field.get("resolvedMethod"),
            )

        for proc in typ.get("procedures") or []:
            proc = proc or {}
            self.add_symbols(
                file_name, proc.get("callName"), proc.get("resolvedMethod")
            )

class ReachablesMatcher(SliceMatcher):
    """Index the ``reachables`` slice (``{"reachables": [{flows, purls}]}``)."""

    def parse_slice(self, slices):
        if isinstance(slices, dict):
            # atom writes ``{"reachables": [...]}``; tolerate a bare entry too.
            if "reachables" in slices:
                slices = slices["reachables"]
            elif "flows" in slices:
                slices = [slices]
            else:
                slices = []

        if not isinstance(slices, (list, tuple)):
            return

        for entry in slices:
            for flow in (entry or {}).get("flows") or []:
                flow = flow or {}
                self.add_symbols(
                    flow.get("parentFileName"),
                    flow.get("name"),
                    flow.get("fullName"),
                    flow.get("typeFullName"),
                    flow.get("parentMethodName"),
                    flow.get("parentClassName"),
                    self.compose_class_method_name(flow),
                )

    @classmethod
    def compose_class_method_name(self, flow):
        """Return ``Class.method`` from a reachables flow, or ``""``."""
        method = flow.get("parentMethodName") or ""
        klass = flow.get("parentClassName") or ""

        if not method or not klass:
            return ""

        if ":" in klass:
            klass = klass.partition(":")[2]

        return f"{klass}.{method}"

def classify_reachability(in_code, reachable):
    """
    Return the reachability verdict for a set of vulnerable symbols.

    reachable is the subset matched against the reachables slice.
    in_code is the subset matched against the usages slice.
    """
    if reachable:
        return ReachabilityStatus.REACHABLE

    if in_code:
        return ReachabilityStatus.UNKNOWN

    return ReachabilityStatus.NOT_REACHABLE

def collect_and_match_resources(
    tool_name,
    patches,
    patch_symbols,
    usages_slices,
    reachables_slices,
    candidate_resources,
    logger=None,
):
    """
    Match patch symbols against the atom slices and store a reachability report
    on each matching candidate resource.

    - a vulnerable symbol in ``reachables`` → REACHABLE
    - a vulnerable symbol only in ``usages`` → UNKNOWN
    - a vulnerable symbol in neither → NOT_REACHABLE
    """
    usages = UsagesMatcher(usages_slices)
    reachables = ReachablesMatcher(reachables_slices)

    if logger:
        logger(
            f"atom match: {usages.file_count} files in usages, "
            f"{reachables.file_count} files in reachables, "
            f"{len(candidate_resources)} candidates, {len(patches)} patches"
        )

    progress = LoopProgress(len(patches), logger=logger)
    for patch in progress.iter(patches):
        vcs_url = patch.get("vcs_url")
        commit_hash = patch.get("commit_hash")
        advisory_uids = patch.get("advisory_uids") or []

        patch_symbols_by_language = patch_symbols.get(commit_hash, {})
        if not patch_symbols_by_language:
            continue

        for resource in candidate_resources:
            lang_patch_symbols = patch_symbols_by_language.get(
                resource.programming_language
            )
            if not lang_patch_symbols:
                continue

            vulnerable = lang_patch_symbols.get("vulnerable") or {}
            fixed = lang_patch_symbols.get("fixed") or {}

            path = resource.path
            vuln_in_code = usages.match_symbols(vulnerable, path)
            vuln_reachable = reachables.match_symbols(vulnerable, path)
            fixed_in_code = usages.match_symbols(fixed, path)
            fixed_reachable = reachables.match_symbols(fixed, path)

            if not (
                vuln_in_code
                or vuln_reachable
                or fixed_in_code
                or fixed_reachable
            ):
                continue

            reachability_status = classify_reachability(
                vuln_in_code, vuln_reachable
            )
            tool_details = [
                {
                    "symbol": symbol,
                    "in_usage": symbol in vuln_in_code,
                    "in_reachable": symbol in vuln_reachable,
                }
                for symbol in sorted(vuln_in_code | vuln_reachable)
            ]
            report = {
                "tool_name": tool_name,
                "patch": {
                    "vcs_url": vcs_url,
                    "commit_hash": commit_hash,
                },
                "advisory_uids": advisory_uids,
                "tool_details": tool_details,
                "fixed_symbols": sorted(fixed),
                "vulnerable_symbols": sorted(vulnerable),
                "is_reachable": reachability_status.value,
            }

            save_resource_reachability_report(
                resource=resource,
                commit_hash=commit_hash,
                vcs_url=vcs_url,
                new_report=report,
            )
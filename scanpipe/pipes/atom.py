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

import json
import re
from collections import defaultdict
from os import environ
from subprocess import SubprocessError

from aboutcode.pipeline import LoopProgress
from scanpipe.pipes import run_command_safely
from scanpipe.pipes.reachability import ReachabilityStatus
from scanpipe.pipes.reachability import save_resource_reachability_report
from scanpipe.pipes.reachability_tools import ReachabilityTool

ATOM_EXECUTABLE = environ.get("ATOM_EXECUTABLE")

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
    """Index the usages slice (objectSlices / userDefinedTypes) and its calls."""

    def __init__(self, slices):
        self.calls_by_file = defaultdict(dict)
        self.calls_by_basename = defaultdict(dict)
        super().__init__(slices)

    def parse_slice(self, slices):
        if not isinstance(slices, dict):
            return

        for obj in slices.get("objectSlices") or []:
            self.add_object_slice(obj or {})

        for typ in slices.get("userDefinedTypes") or []:
            self.add_user_defined_type(typ or {})

    def add_calls(self, file_name, symbols, calls):
        """Associate ``calls`` with each symbol in ``symbols`` for ``file_name``."""
        if not isinstance(file_name, str) or not file_name or not calls:
            return

        path = normalize_file_path(file_name)
        basename = path.rsplit("/", 1)[-1]
        for symbol in symbols:
            dotted = normalize_symbol_name(symbol)
            if not dotted:
                continue

            file_slot = self.calls_by_file[path].setdefault(dotted, [])
            base_slot = self.calls_by_basename[basename].setdefault(dotted, [])

            for call in calls:
                if call not in file_slot:
                    file_slot.append(call)
                if call not in base_slot:
                    base_slot.append(call)

    def get_calls(self, symbols, file_name):
        """
        Return the calls associated with ``symbols`` in ``file_name``.

        Uses the same fuzzy matching as ``match_symbols`` (exact, suffix, or
        prefix), deduplicated by ``(call_name, resolved_method, line_number)``.
        """
        if not symbols:
            return []

        path = normalize_file_path(file_name)
        file_calls = self.calls_by_file.get(path)
        if not file_calls:
            file_calls = self.calls_by_basename.get(path.rsplit("/", 1)[-1], {})
        if not file_calls:
            return []

        result = []
        seen = set()
        for symbol in symbols:
            dotted = normalize_symbol_name(symbol)
            if not dotted:
                continue

            for name, name_calls in file_calls.items():
                if not (
                    name == dotted
                    or name.endswith("." + dotted)
                    or ("." in name and dotted.endswith("." + name))
                ):
                    continue

                for call in name_calls:
                    key = (
                        call.get("call_name"),
                        call.get("resolved_method"),
                        call.get("line_number"),
                    )
                    if key not in seen:
                        seen.add(key)
                        result.append(call)
        return result

    def build_call_record(self, call):
        """Return a compact call record from an atom call entry, or ``None``."""
        call = call or {}
        call_name = call.get("callName")
        resolved = call.get("resolvedMethod")
        if not (call_name or resolved):
            return None

        record = {}
        if call_name:
            record["call_name"] = call_name

        if resolved:
            record["resolved_method"] = resolved

        if call.get("lineNumber") is not None:
            record["line_number"] = call.get("lineNumber")

        if call.get("columnNumber") is not None:
            record["column_number"] = call.get("columnNumber")

        return record

    def add_object_slice(self, obj):
        """Index the symbols and calls of one ``objectSlices`` entry."""
        file_name = obj.get("fileName")
        self.add_symbols(file_name, obj.get("fullName"))

        for usage in obj.get("usages") or []:
            usage = usage or {}

            calls = []
            for raw_call in (usage.get("argToCalls") or []) + (
                usage.get("invokedCalls") or []
            ):
                raw_call = raw_call or {}
                self.add_symbols(
                    file_name,
                    raw_call.get("callName"),
                    raw_call.get("resolvedMethod"),
                )
                record = self.build_call_record(raw_call)
                if record:
                    calls.append(record)

            usage_symbols = []
            for part in (usage.get("targetObj"), usage.get("definedBy")):
                part = part or {}
                names = (
                    part.get("name"),
                    part.get("typeFullName"),
                    part.get("resolvedMethod"),
                )
                self.add_symbols(file_name, *names)
                usage_symbols.extend(name for name in names if name)

            if usage_symbols and calls:
                self.add_calls(file_name, usage_symbols, calls)

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
        if not isinstance(slices, list):
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

            if not (vuln_in_code or vuln_reachable or fixed_in_code):
                continue

            reachability_status = classify_reachability(vuln_in_code, vuln_reachable)
            tool_details = []
            for symbol in sorted(vuln_in_code | vuln_reachable):
                tool_details.append(
                    {
                        "symbol_name": symbol,
                        "in_usage": symbol in vuln_in_code,
                        "calls": usages.get_calls([symbol], path),
                        "in_reachable": symbol in vuln_reachable,
                    }
                )

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


class AtomTool(ReachabilityTool):
    tool_name = "atom"
    executable = ATOM_EXECUTABLE
    supported_languages = {
        "Java": "java",
        "Python": "python",
    }

    commands = ("usages", "reachables")

    @classmethod
    def get_availability(cls):
        if not cls.executable:
            return (
                "atom is not configured. Set the ATOM_EXECUTABLE environment variable."
            )

    @classmethod
    def get_atom_language(cls, project):
        """Return the atom ``-l`` value for ``project`` from the scan summary."""
        summary_path = project.get_latest_output("summary")
        with open(summary_path) as f:
            summary = json.load(f)

        primary_language = summary.get("primary_language")
        if not primary_language:
            raise ValueError(
                f"No primary_language in the scan summary of {project.name!r}."
            )

        language = cls.supported_languages.get(primary_language)
        if not language:
            raise ValueError(
                f"Unsupported primary_language {primary_language!r} for "
                f"{project.name!r}. Supported: {', '.join(cls.supported_languages)}."
            )
        return language

    @staticmethod
    def get_output_paths(project, atom_language):
        """Return the output paths shared by the atom commands."""
        manifest_path = project.get_output_file_path("atom_reachability", "json")
        prefix = f"{manifest_path.stem}.{atom_language}"
        return {
            "atom": manifest_path.with_name(f"{prefix}.atom"),
            "usages": manifest_path.with_name(f"{prefix}.usages.slices.json"),
            "reachables": manifest_path.with_name(f"{prefix}.reachables.slices.json"),
        }

    @classmethod
    def run_command(
        cls, command, target_path, atom_language, output_paths, logger=None
    ):
        """Run a single atom command and return its slices file path or None."""
        command_args = [
            cls.executable,
            command,
            "-l",
            atom_language,
            "--cache",
            "none",
            "-o",
            str(output_paths["atom"]),
            "-s",
            str(output_paths[command]),
            str(target_path),
        ]

        if logger:
            logger(f"Running atom {command} on {target_path} ...")
        try:
            run_command_safely(command_args=command_args)
        except SubprocessError as error:
            if logger:
                logger(f"atom {command} failed: {error!r}")
            return None
        return output_paths[command]

    @classmethod
    def run(cls, project, logger=None):
        """
        Run the atom ``usages`` and ``reachables`` commands.

        Return a mapping of command name to its slices file path (or ``None``
        when that command failed).
        """
        target_path = project.codebase_path
        if not target_path:
            raise ValueError(
                f"Cannot run Atom tools against project {project.name!r}:"
                f" codebase_path is None."
            )
        atom_language = cls.get_atom_language(project)
        output_paths = cls.get_output_paths(
            project=project, atom_language=atom_language
        )

        results = {}
        for command in cls.commands:
            results[command] = cls.run_command(
                command=command,
                target_path=target_path,
                atom_language=atom_language,
                output_paths=output_paths,
                logger=logger,
            )
        return results

    @staticmethod
    def load_slices(export_output_path, logger=None):
        """Load and return a single atom slices file."""
        if not export_output_path:
            return {}
        try:
            with open(export_output_path) as slice_file:
                return json.load(slice_file)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            if logger:
                logger(f"Skipping atom slices {export_output_path}: {error!r}")
            return {}

    @classmethod
    def parsed_output(cls, export_output_path, logger=None):
        """Load and return the atom slices keyed by command name."""
        if not export_output_path:
            return {}
        return {
            command: cls.load_slices(export_output_path=path, logger=logger)
            for command, path in export_output_path.items()
        }

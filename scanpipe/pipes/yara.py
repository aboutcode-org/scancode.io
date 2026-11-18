#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/scancode.io for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import re
from pathlib import Path
from typing import NamedTuple

import yara
from packageurl import PackageURL

from aboutcode.pipeline import LoopProgress
from scanpipe import pipes
from scanpipe.pipes import flag

# Point to upstream YARA rule repository once available
DEFAULT_RULES_DIR = (
    Path(__file__).resolve().parent.parent / "tests" / "data" / "yara_rules"
)


class InvalidYaraRules(Exception):
    pass


class MatchedString(NamedTuple):
    identifier: str
    value: str


class MatchResult(NamedTuple):
    rule: str
    purl: str
    version: str | None
    matched_strings: list[MatchedString]

    def matched_strings_dict(self):
        """Format matched strings as an identifier-to-value dictionary."""
        return {
            matched_string.identifier: matched_string.value
            for matched_string in self.matched_strings
        }


class YaraPackageScanner:
    """Scan files or byte streams with compiled YARA rules to detect packages."""

    def __init__(self, rule_path=DEFAULT_RULES_DIR):
        self.rule_path = Path(rule_path) if rule_path else DEFAULT_RULES_DIR
        self.rules = self._compile_rules(self.rule_path)

    @classmethod
    def _compile_rules(cls, rules_directory):
        """Compile YARA rules from a directory of .yar files."""
        if not rules_directory or not rules_directory.is_dir():
            raise InvalidYaraRules(
                f"YARA rules directory does not exist: {rules_directory}"
            )

        rule_files = sorted(rules_directory.glob("*.yar"))
        if not rule_files:
            raise InvalidYaraRules(
                f"No .yar rule files found in directory: {rules_directory}"
            )

        try:
            return yara.compile(filepaths={f.stem: str(f) for f in rule_files})
        except yara.Error as e:
            raise InvalidYaraRules(
                f"Failed to compile YARA rules from {rules_directory}: {e}"
            ) from e

    def scan_file(self, location):
        """Scan a codebase file and return matching package details."""
        if not location:
            return []
        try:
            yara_matches = self.rules.match(filepath=str(location))
        except yara.Error:
            return []

        return self._build_match_results(yara_matches=yara_matches)

    def _build_match_results(self, yara_matches):
        package_results = []
        for match in yara_matches:
            meta = match.meta
            base_purl = meta.get("base_purl")
            matched_strings = self._extract_matched_strings(yara_match=match)
            version_strings = []
            for ms in matched_strings:
                if ms.identifier.startswith("$version"):
                    version_strings.append(ms.value)

            version = self._extract_version(version_strings)
            purl = f"{base_purl}@{version}" if version else base_purl

            package_results.append(
                MatchResult(
                    rule=match.rule,
                    purl=purl,
                    version=version,
                    matched_strings=matched_strings,
                )
            )

        return package_results

    @staticmethod
    def _extract_matched_strings(yara_match):
        """
        Return a list of ``MatchedString`` from a YARA match.

        yara_match.strings contains all rule strings that matched in the file.
        Each string can match at multiple file offsets (`instances`).
        """
        matched_strings = []
        for yara_string in yara_match.strings:
            for instance in yara_string.instances:
                # Safely decode arbitrary binary without raising UnicodeDecodeError
                text = instance.matched_data.decode("utf-8", errors="replace").strip()
                if text:
                    matched_strings.append(
                        MatchedString(identifier=yara_string.identifier, value=text)
                    )
                    break
        return matched_strings

    @staticmethod
    def _extract_version(version_strings):
        """Extract clean version number from matched version strings."""
        for text in version_strings:
            if match := re.search(r"\d+(?:\.\d+)+(?:[a-zA-Z0-9.\-_]*)?", text):
                return match.group(0).rstrip(".-")


def match_resources_by_yara(project, logger=None):
    """
    Iterate through codebase files that have not yet been matched to a package,
    scan each resource with compiled YARA rules, and create ``DiscoveredPackage``
    records linked to the matched resources.
    """
    unmatched_files = project.codebaseresources.files().no_status()
    resource_count = unmatched_files.count()
    if not resource_count:
        return

    scanner = YaraPackageScanner()
    if logger:
        logger(f"Scanning {resource_count} resources with YARA rules.")

    progress = LoopProgress(total_iterations=resource_count, logger=logger)
    matched_count = 0

    for codebase_resource in progress.iter(unmatched_files):
        matches = scanner.scan_file(location=codebase_resource.location)
        if not matches:
            continue

        for match in matches:
            purl = PackageURL.from_string(match.purl)
            package_data = purl.to_dict()
            name = purl.name
            version = match.version

            match_extra_data = {
                "matched_by": "yara",
                "yara_rule": match.rule,
                "matched_strings": match.matched_strings_dict(),
            }

            # Group matching files under a single package record and
            # backfill version if found.
            existing_pkg = project.discoveredpackages.filter(name=name).first()
            if existing_pkg:
                if version and not existing_pkg.version:
                    updated_purl = PackageURL(
                        type=existing_pkg.type,
                        namespace=existing_pkg.namespace,
                        name=name,
                        version=version,
                    )
                    existing_pkg.version = version
                    existing_pkg.set_package_url(str(updated_purl))
                    existing_pkg.save()
                package = existing_pkg
            else:
                package_data["extra_data"] = match_extra_data
                package = pipes.update_or_create_package(
                    project=project,
                    package_data=package_data,
                )

            if package:
                package.codebase_resources.add(codebase_resource)

            codebase_resource.update_extra_data(match_extra_data)
            codebase_resource.update(status=flag.MATCHED_BY_YARA_RULE)
            matched_count += 1

    if logger:
        logger(f"{matched_count:,d} resources matched via YARA rules.")

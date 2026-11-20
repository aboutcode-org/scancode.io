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
from dataclasses import dataclass
from pathlib import Path

try:
    import yara
except ImportError:
    yara = None

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


def is_available():
    """Return True if the yara-python library is installed and available."""
    return yara is not None


@dataclass
class MatchedString:
    identifier: str
    value: str


@dataclass
class MatchResult:
    rule: str
    purl: PackageURL
    version: str | None
    matched_strings: list[MatchedString]

    def matched_strings_dict(self):
        """Format matched strings as an identifier-to-value dictionary."""
        return {
            matched_string.identifier: matched_string.value
            for matched_string in self.matched_strings
        }


def compile_rules(rules_directory=DEFAULT_RULES_DIR):
    """Compile YARA rules from a directory of .yar files."""
    rules_directory = Path(rules_directory)
    if not rules_directory.is_dir():
        raise InvalidYaraRules(
            f"YARA rules directory does not exist: {rules_directory}"
        )

    rule_files = sorted(rules_directory.glob("*.yar"))
    if not rule_files:
        raise InvalidYaraRules(
            f"No .yar rule files found in directory: {rules_directory}"
        )

    filepaths = {rule_file.stem: str(rule_file) for rule_file in rule_files}
    try:
        rules = yara.compile(filepaths=filepaths)
    except yara.Error as error:
        raise InvalidYaraRules(
            f"Failed to compile YARA rules from {rules_directory}: {error}"
        ) from error

    # Validate that each YARA rule has a valid base_purl
    for rule in rules:
        base_purl = rule.meta.get("base_purl")
        if not base_purl:
            raise InvalidYaraRules(f"Rule {rule.identifier} is missing base_purl.")
        try:
            PackageURL.from_string(base_purl)
        except ValueError as error:
            raise InvalidYaraRules(
                f"Rule {rule.identifier} has an invalid base_purl: {error}"
            )

    return rules


def scan_file(location, rules):
    """Scan a codebase file and return matching package details."""
    yara_matches = rules.match(filepath=str(location))
    return build_match_results(yara_matches=yara_matches)


def build_match_results(yara_matches):
    package_results = []
    for match in yara_matches:
        base_purl = PackageURL.from_string(match.meta["base_purl"])
        matched_strings = extract_matched_strings(yara_match=match)
        version_strings = [
            matched_string.value
            for matched_string in matched_strings
            if matched_string.identifier.startswith("$version")
        ]

        version = extract_version(version_strings)
        purl = (
            PackageURL(
                type=base_purl.type,
                namespace=base_purl.namespace,
                name=base_purl.name,
                version=version,
            )
            if version
            else base_purl
        )

        package_results.append(
            MatchResult(
                rule=match.rule,
                purl=purl,
                version=version,
                matched_strings=matched_strings,
            )
        )

    return package_results


def extract_matched_strings(yara_match):
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


def extract_version(version_strings):
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

    rules = compile_rules()
    if logger:
        logger(f"Scanning {resource_count} resources with YARA rules.")

    progress = LoopProgress(total_iterations=resource_count, logger=logger)
    matched_count = 0

    for codebase_resource in progress.iter(unmatched_files.iterator(chunk_size=2000)):
        try:
            matches = scan_file(location=codebase_resource.location, rules=rules)
        except yara.Error as error:
            project.add_error(
                model="match_resources_by_yara",
                exception=error,
                object_instance=codebase_resource,
            )
            continue

        for match in matches:
            purl = match.purl
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
                    existing_pkg.update(version=version)
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

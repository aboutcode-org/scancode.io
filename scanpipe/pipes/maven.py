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

import difflib
import json
import logging
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
from defusedxml import ElementTree as SafeElementTree
from license_expression import Licensing
from packageurl import PackageURL
from packageurl.contrib import purl2url

from scanpipe.models import DiscoveredPackage
from scanpipe.pipes import fetch
from scanpipe.pipes import flag
from scanpipe.pipes import jvm
from scanpipe.pipes import scancode

logger = logging.getLogger(__name__)


def check_input_and_return_purl(project):
    """Validate the input and return a maven PURL."""
    input_sources = project.inputsources.all()
    if len(input_sources) != 1:
        error_msg = "Only 1 maven purl is accepted."
        raise ValueError(error_msg)
    # Strip the qualifiers as this is not needed.
    project_input = str(input_sources[0]).split("?")[0]
    input_purl = PackageURL.from_string(project_input)

    if input_purl.type != "maven":
        error_msg = "Only maven purl is supported."
        raise ValueError(error_msg)
    if not input_purl.version:
        error_msg = "Version is required."
        raise ValueError(error_msg)

    return input_purl


def fetch_inputs(purl):
    """Fetch the binary and source for the given input purl"""
    purl_str = PackageURL.to_string(purl)

    purl_bin_path = fetch_path(purl_str, "binary")
    purl_src_path = fetch_path(f"{purl_str}?classifier=sources", "source")

    if not purl_bin_path and not purl_src_path:
        err_msg = f"No source or binary could be resolved for {purl}."
        raise ValueError(err_msg)

    return purl_src_path, purl_bin_path


def fetch_path(purl, package_type):
    """Fetch the purl and return the location of the fetched tarball"""
    try:
        return fetch.fetch_url(url=purl).path
    except (ValueError, requests.RequestException) as e:
        logger.warning("Failed to fetch %s package: %s", package_type, e)
        return None


def fetch_and_scan_remote_pom(input_purl, scan_output_location):
    """Fetch the .pom file from maven.org if not present in codebase."""
    with open(scan_output_location) as file:
        data = json.load(file)
    # Skip fetching the remote POM if a pom.xml is already present in the codebase.
    for file_entry in data["files"]:
        if PurePosixPath(file_entry["path"]).name == "pom.xml":
            return []

    pom_url = get_pom_url(input_purl)
    if not pom_url:
        return [{str(input_purl): ["Failed to resolve POM URL."]}]
    pom_file = download_pom_file(pom_url)
    if not pom_file:
        return [{pom_url: ["Failed to download the POM file."]}]
    scanning_errors = scan_pom_file(pom_file)

    scanned_pom_packages, scanned_dependencies = update_datafile_paths(pom_file)
    updated_data = update_scan_data(data, scanned_pom_packages, scanned_dependencies)

    with open(scan_output_location, "w") as file:
        json.dump(updated_data, file, indent=2)
    if not scanning_errors:
        return []
    return [scanning_errors] if isinstance(scanning_errors, dict) else scanning_errors


def update_scan_data(data, scanned_packages, scanned_dependencies):
    """Update packages and dependencies data"""
    data["packages"] = data.get("packages", []) + scanned_packages
    data["dependencies"] = data.get("dependencies", []) + scanned_dependencies
    return data


def get_pom_url(input_purl):
    """Construct a Maven POM URL from the input purl."""
    purl_str = PackageURL.to_string(input_purl)
    input_source_url = purl2url.get_download_url(purl_str)
    if not input_source_url:
        return ""

    parsed_url = urlparse(input_source_url)
    maven_hosts = {
        "repo1.maven.org",
        "repo.maven.apache.org",
        "maven.google.com",
    }
    pom_url = ""
    if parsed_url.netloc in maven_hosts:
        base_url = input_source_url.rsplit("/", 1)[0]
        pom_url = f"{base_url}/{input_purl.name}-{input_purl.version}.pom"
    return pom_url


def download_pom_file(pom_url):
    """Fetch the pom file from the input pom_url"""
    try:
        downloaded_pom = fetch.fetch_http(pom_url)
    except requests.RequestException:
        return {}
    path = str(downloaded_pom.path)
    return {
        "pom_file_path": path,
        "output_path": f"{path}-output.json",
        "pom_url": pom_url,
    }


def scan_pom_file(pom_file_dict):
    """Fetch and scan the pom file from the input pom_urls"""
    pom_file_path = pom_file_dict.get("pom_file_path", "")
    scanned_pom_output_path = pom_file_dict.get("output_path", "")

    # Run a package scan on the fetched pom.xml
    # Return scanning errors, if present
    return scancode.run_scan(
        location=pom_file_path,
        output_file=scanned_pom_output_path,
        run_scan_args={
            "package": True,
        },
    )


def update_datafile_paths(pom_file_dict):
    """Update datafile_paths in scanned packages and dependencies."""
    scanned_pom_packages = []
    scanned_pom_deps = []

    scanned_pom_output_path = pom_file_dict.get("output_path", "")
    pom_url = pom_file_dict.get("pom_url", "")

    with open(scanned_pom_output_path) as scanned_pom_file:
        scanned_pom_data = json.load(scanned_pom_file)

    scanned_packages = scanned_pom_data.get("packages", [])
    scanned_dependencies = scanned_pom_data.get("dependencies", [])

    for scanned_package in scanned_packages:
        scanned_package["datafile_paths"] = [pom_url]
        scanned_pom_packages.append(scanned_package)
    for scanned_dep in scanned_dependencies:
        # See https://github.com/aboutcode-org/scancode.io/issues/1763#issuecomment-3525165830
        scanned_dep["datafile_path"] = ""
        scanned_pom_deps.append(scanned_dep)
    return scanned_pom_packages, scanned_pom_deps


def update_package_license_from_resource_if_missing(project):
    """Populate missing licenses to packages based on resource data."""
    for package in project.discoveredpackages.all():
        if not package.get_declared_license_expression():
            matching_resources = (
                project.codebaseresources.has_license_expression().filter(
                    discovered_packages=package
                )
            )
            detected_licenses = list(
                matching_resources.values_list(
                    "detected_license_expression", flat=True
                ).distinct()
            )
            if detected_licenses:
                license_expression = " AND ".join(detected_licenses)
                declared_license_expression = str(Licensing().dedup(license_expression))
                package.declared_license_expression = declared_license_expression
                package.save()


def get_main_maven_pom(project, purl):
    """
    Return the main Maven POM or None if not found.

    The main POM is typically located at:
        .../META-INF/maven/<groupId>/<artifactId>/pom.xml
    """
    namespace = purl.namespace
    name = purl.name

    expected_suffix = f"{namespace}/{name}/pom.xml"
    return (
        project.codebaseresources.files()
        .to_codebase()
        .filter(path__endswith=expected_suffix)
        .first()
    )


def get_maven_shade_relocations(project, pom_resource):
    """
    Parse the POM and return a dict mapping "shadedPattern" to the
    original "pattern" for every <relocation> found in the POM file.

    Sample:
        <configuration>
            <relocations>
            <relocation>
                <pattern>org.apache.commons.logging</pattern>
                <shadedPattern>org.apache.htrace.commons.logging</shadedPattern>
            </relocation>
            <relocation>
                <pattern>com.fasterxml.jackson</pattern>
                <shadedPattern>org.apache.htrace.fasterxml.jackson</shadedPattern>
            </relocation>
            </relocations>
        </configuration>

    Return an empty dict when no relocation is found or when parsing fails.
    """
    relocations = {}
    if not pom_resource:
        return relocations

    pom_location = pom_resource.location
    if not pom_location:
        return relocations

    try:
        tree = SafeElementTree.parse(pom_location)
    except (SafeElementTree.ParseError, OSError, ValueError) as exception:
        project.add_error(
            description=f"Cannot parse POM at {pom_location}: {exception}",
            model="map_shaded_classes_to_maven_packages",
            details={"resource_path": pom_resource.path},
        )
        return relocations

    root = tree.getroot()

    for plugin in root.iterfind(".//{*}plugin"):
        if plugin.findtext("{*}artifactId", "").strip() != "maven-shade-plugin":
            continue
        for relocation in plugin.iterfind(".//{*}relocation"):
            pattern = relocation.findtext("{*}pattern", "").strip()
            shaded_pattern = relocation.findtext("{*}shadedPattern", "").strip()
            if pattern and shaded_pattern:
                relocations[shaded_pattern] = pattern

    return relocations


def _iter_maven_candidates(project):
    """
    Yield Maven "DiscoveredPackage" and "DiscoveredDependency" instances
    that are candidates for matching shaded classes.

    Resolved dependencies yield their resolved package. Unresolved
    dependencies yield the dependency itself, with the PURL fields populated
    in memory from "dependency_uid".
    """
    yield from project.discoveredpackages.filter(type="maven")

    for dependency in project.discovereddependencies.all():
        if dependency.resolved_to_package:
            package = dependency.resolved_to_package
            if package.type == "maven":
                yield package
            continue

        try:
            purl = PackageURL.from_string(dependency.dependency_uid)
        except (ValueError, TypeError):
            continue
        if purl.type != "maven":
            continue

        dependency.type = purl.type
        dependency.namespace = purl.namespace
        dependency.name = purl.name
        dependency.version = purl.version
        yield dependency


def _dedupe_maven_candidates(candidates, main_purl):
    """
    Return "candidates" deduplicated by "namespace" and "name", excluding the
    main package.
    """
    result = []
    seen = set()

    main_namespace = main_purl.namespace
    main_name = main_purl.name
    main_version = main_purl.version or ""

    for candidate in candidates:
        namespace = candidate.namespace
        name = candidate.name
        version = candidate.version or ""

        namespace_name = (namespace, name)
        if namespace_name in seen:
            continue

        if (
            namespace == main_namespace
            and name == main_name
            and version == main_version
        ):
            continue

        seen.add(namespace_name)
        result.append(candidate)

    return result


def get_maven_dependency_packages(project, main_purl):
    """
    Return the list of Maven dependencies discovered in the project,
    excluding the main package identified by the ``main_purl``.

    The returned list contains the following:

        - ``DiscoveredPackage`` for Maven packages identified in the project.

        - ``DiscoveredDependency`` for POM-declared dependencies without a
          corresponding ``DiscoveredPackage``.

    The list is deduplicated by ``namespace`` and ``name`` so the
    same dependency is not scored twice, which would produce a tie and leave
    shaded classes unmatched.
    """
    return _dedupe_maven_candidates(_iter_maven_candidates(project), main_purl)


def get_java_fqn_from_class_path(path):
    """
    Return the fully qualified Java class name from the provided "path".

    For example,
        "to/org/apache/htrace/Foo.class" -> "org.apache.htrace.Foo"
        "to/org/apache/htrace/Foo$Bar.class" -> "org.apache.htrace.Foo"
    """
    cleaned = path

    # Prefer the content after the last "-extract/" segment when present.
    if "-extract/" in cleaned:
        cleaned = cleaned.rsplit("-extract/", 1)[-1]
    elif cleaned.startswith("to/"):
        cleaned = cleaned.removeprefix("to/")

    cleaned = jvm.JavaLanguage.get_normalized_path(cleaned, "")

    return cleaned.replace("/", ".")


def apply_shade_relocations(fqn, relocations):
    """
    Reverse the shaded pattern replacements in "fqn" using "relocations".

    The longest matching shaded pattern wins. Matching is done
    on package boundaries so that a pattern such as "org.foo" does not
    accidentally match "org.foobar.Class".
    """
    sorted_patterns = sorted(relocations.keys(), key=len, reverse=True)

    for shaded_pattern in sorted_patterns:
        if fqn == shaded_pattern or fqn.startswith(f"{shaded_pattern}."):
            original_pattern = relocations[shaded_pattern]
            return original_pattern + fqn[len(shaded_pattern) :]

    return fqn


# The 0.8 is chosen as to accept small plural/singular and one-character
# variations while rejecting semantically related but lexically different
# words.
FUZZY_SEGMENT_MATCH_THRESHOLD = 0.8


def _fuzzy_segment_match(
    artifact_segment, package_segment, threshold=FUZZY_SEGMENT_MATCH_THRESHOLD
):
    """
    Return True if "artifact_segment" and "package_segment" are similar
    enough to consider as a match.
    """
    if not artifact_segment or not package_segment:
        return False
    return (
        difflib.SequenceMatcher(None, artifact_segment, package_segment).ratio()
        >= threshold
    )


# Required signals that must be present for a candidate to be considered.
# Both the "group" and the "artifact" of the dependency must contribute at
# least one matching segment for the FQN. This rejects the false matches
# where only the group (e.g. "com.google" for guava) matches the FQN
# namespace.
REQUIRED_MATCH_SIGNALS = {"group", "artifact"}

# Minimum score for a candidate to be accepted as a match.
#
# Scoring system:
#   - +1 per matching group segment
#   - +2 per matching artifact segment
#   - +3 for a fuzzy match on the artifact's last segment
#
# Both "group" and "artifact" signals are required, so scores start at 3
# (1 group + 1 artifact) and go up by 1 or 2 per extra matching segment.
# The threshold of 5 rejects 3 and 4, which cover the weak cases where only
# a single artifact segment matches, or the score relies on one artifact
# segment plus several generic group segments.
#
# Passing 5 requires one of:
#   - a second matching artifact segment (1 group + 2 artifact = 1 + 4 = 5)
#   - two extra matching group segments (3 group + 1 artifact = 3 + 2 = 5)
#   - a fuzzy match (1 group + 1 artifact + fuzzy = 1 + 2 + 3 = 6)

# The value is designed based on a small sample of shaded JARs. It
# should be revisited with a larger sample if false positives are observed.
MIN_MATCH_SCORE = 5


def _score_group_segments(group_id, package_segments):
    """
    Return the number of segments of "group_id" that appear in
    "package_segments".
    """
    return sum(
        1 for segment in group_id.split("/") if segment and segment in package_segments
    )


def _score_artifact_segments(artifact_id, package_segments):
    """
    Return twice the number of segments of "artifact_id" that appear in
    "package_segments". Artifact matches are weighted more than group ones.
    """
    return sum(
        2
        for segment in artifact_id.split("/")
        if segment and segment in package_segments
    )


def _score_fuzzy_segment(artifact_id, package_segments):
    """
    Return 3 if the last segment of "artifact_id" is a fuzzy match for the
    immediate parent package of the FQN, 0 otherwise.

    Returns 0 when either input is missing or when the two segments are not
    similar enough.
    """
    artifact_last = artifact_id.split("/")[-1]
    fqn_last = package_segments[-1]
    return 3 if _fuzzy_segment_match(artifact_last, fqn_last) else 0


def score_dependency_for_fqn(fqn, package):
    """
    Return a tuple (score, signals) to conclude the match result.

    "score" is computed from the matching segments, as described below.
    "signals" contains the names of the matching rules that matched:
        "group", "artifact", and optionally "fuzzy".

    Scoring:
        - +1 per matching segment of the group ID
        - +2 per matching segment of the artifact ID
        - +3 when the artifact's last segment is similar to the
          immediate parent package of the FQN

    Both "." and "-" are treated as segment separators for the group and
    artifact, so hyphenated group IDs such as "commons-logging" are split
    into ["commons", "logging"] before matching against the FQN segments.
    """
    empty_result = (0, set())

    group_id = (package.namespace or "").replace(".", "/").replace("-", "/")
    artifact_id = (package.name or "").replace(".", "/").replace("-", "/")

    fqn_segments = fqn.split(".")
    # Drop the class name and keep the package segments only.
    package_segments = fqn_segments[:-1]

    if not package_segments:
        return empty_result

    score = 0
    signals = set()

    group_score = _score_group_segments(group_id, package_segments)
    if group_score:
        score += group_score
        signals.add("group")

    artifact_score = _score_artifact_segments(artifact_id, package_segments)
    if artifact_score:
        score += artifact_score
        signals.add("artifact")

    fuzzy_score = _score_fuzzy_segment(artifact_id, package_segments)
    if fuzzy_score:
        score += fuzzy_score
        signals.add("fuzzy")

    return score, signals


def match_shaded_class_to_package(fqn, packages, min_score=MIN_MATCH_SCORE):
    """
    Return a tuple (package, score, signals) for the best matching package,
    or None.

    A candidate is considered only when the "group" and "artifact" signals are
    both present and the score reaches "min_score".

    Returns None when no candidate qualifies, or when several candidates
    tie for the top score, to avoid false positives.
    """
    candidates = []
    for package in packages:
        score, signals = score_dependency_for_fqn(fqn, package)
        if not REQUIRED_MATCH_SIGNALS.issubset(signals):
            continue
        if score < min_score:
            continue
        candidates.append((score, signals, package))

    if not candidates:
        return

    top_score = max(score for score, _, _ in candidates)
    top_candidates = [
        candidate for candidate in candidates if candidate[0] == top_score
    ]

    if len(top_candidates) != 1:
        # More than one package shares the top score.
        return

    score, signals, package = top_candidates[0]
    return package, score, signals


def _get_original_fqn(fqn, relocations, main_prefix):
    """
    Return the original fully qualified class name for a shaded class, or
    None when the class should not be considered for matching.
    """
    if relocations:
        is_shaded = any(
            fqn == shaded_pattern or fqn.startswith(f"{shaded_pattern}.")
            for shaded_pattern in relocations
        )
        if not is_shaded:
            return
        return apply_shade_relocations(fqn, relocations)

    if main_prefix and fqn.startswith(main_prefix):
        return

    return fqn


def _map_shaded_class_resource(resource, relocations, main_prefix, dependency_packages):
    """
    Try to map a single ".class" resource to a Maven dependency package.

    Return True when the resource was mapped and flagged as shaded, False
    otherwise.
    """
    fqn = get_java_fqn_from_class_path(resource.path)
    original_fqn = _get_original_fqn(fqn, relocations, main_prefix)

    if original_fqn is None:
        return False

    match = match_shaded_class_to_package(original_fqn, dependency_packages)
    if not match:
        return False

    matched_package, match_score, match_signals = match
    if isinstance(matched_package, DiscoveredPackage):
        resource.discovered_packages.add(matched_package)

    resource.update(
        status=flag.SHADED_CLASS,
        extra_data={
            **resource.extra_data,
            "shaded_from_package": matched_package.package_url,
            "original_fqn": original_fqn,
            "match_score": match_score,
            "match_signals": sorted(match_signals),
        },
    )
    return True


def map_shaded_classes_to_maven_packages(project, purl, logger=None):
    """Map shaded ".class" resources to their Maven dependency packages."""
    if logger:
        logger("Mapping shaded .class resources to Maven dependency packages.")

    to_classes = (
        project.codebaseresources.files()
        .to_codebase()
        .filter(extension=".class")
        .filter(
            status__in=[
                flag.NO_STATUS,
                flag.NO_JAVA_SOURCE,
                flag.REQUIRES_REVIEW,
            ]
        )
        .has_no_relation()
    )
    to_classes_count = to_classes.count()

    if not to_classes_count:
        if logger:
            logger("No unmapped .class resources to process.")
        return

    dependency_packages = get_maven_dependency_packages(project, main_purl=purl)

    if not dependency_packages:
        if logger:
            logger(
                f"No Maven dependency packages found for "
                f"{to_classes_count:,d} unmapped .class resources."
            )
        return

    main_pom = get_main_maven_pom(project, purl)
    relocations = get_maven_shade_relocations(project, main_pom)
    main_prefix = f"{purl.namespace}."

    mapped_count = 0
    unmatched_count = 0

    for resource in to_classes.iterator(chunk_size=2000):
        if _map_shaded_class_resource(
            resource, relocations, main_prefix, dependency_packages
        ):
            mapped_count += 1
        else:
            unmatched_count += 1

    if logger:
        logger(
            f"Mapped {mapped_count:,d} shaded .class resources to Maven "
            f"dependency packages. {unmatched_count:,d} left for review."
        )

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

import math
from collections import Counter
from dataclasses import dataclass
from dataclasses import field

from aboutcode.pipeline import LoopProgress
from scanpipe.models import CodebaseRelation
from scanpipe.pipes import flag

"""
Path matching using source and binary symbols.

The approach is to create a set of symbols obtained from the rust binary for
each of them and match them to the symbols obtained from the source
"""

MATCHING_RATIO_RUST = 0.5
SMALL_FILE_SYMBOLS_THRESHOLD = 20
MATCHING_RATIO_RUST_SMALL_FILE = 0.4
MATCHING_RATIO_ELF = 0.05
MATCHING_RATIO_MACHO = 0.15
MATCHING_RATIO_WINPE = 0.15
MATCHING_RATIO_JAVASCRIPT = 0.7
SMALL_FILE_SYMBOLS_THRESHOLD_JAVASCRIPT = 30
MATCHING_RATIO_JAVASCRIPT_SMALL_FILE = 0.5
JAVASCRIPT_DECOMPOSED_SYMBOLS_THRESHOLD = 0.5
STATS_FIELDS = [
    "matched_symbols",
    "unmatched_symbols",
    "matched_symbols_ratio",
    "matched_symbols_unique_ratio",
    "source_symbols_count",
    "matched_symbols_count",
]


@dataclass
class SymbolsMatchResult:
    """
    Statistics and debug information for each attempted matching
    between a binary and a source file using extracted symbols.
    Contains CodebaseRelation and other data to create the codebase
    realtions optionally if matching with symbols is successful.
    """

    from_resource: str
    is_matched: bool
    relation_key: tuple | None = None
    codebase_relation: CodebaseRelation | None = None
    matched_symbols: list = field(default_factory=list)
    unmatched_symbols: list = field(default_factory=list)
    matched_symbols_ratio: int = 0
    matched_symbols_unique_ratio: int = 0
    source_symbols_count: int = 0
    matched_symbols_count: int = 0

    def update_stats_from_mapping(self, data):
        for stats_field in STATS_FIELDS:
            value = data.get(stats_field)
            if value:
                setattr(self, stats_field, value)

    def get_stats_mapping(self):
        mapping = {}
        for stats_field in STATS_FIELDS:
            value = getattr(self, stats_field)
            if isinstance(value, list):
                value = sorted(value)

            mapping[stats_field] = value

        return mapping


def map_resources_with_symbols(
    project, to_resource, from_resources, binary_symbols, map_type, logger=None
):
    """
    Map paths found in the ``to_resource`` extra_data to paths of the ``from_resources``
    CodebaseResource queryset using the precomputed ``from_resources_index`` path index.
    """
    if not binary_symbols:
        return

    # Accumulate unique relation objects for bulk creation
    relations_to_create = {}
    unmapped_source_files_with_stats = {}

    # These are of type string
    paths_not_mapped = to_resource.extra_data[f"{map_type}_paths_not_mapped"] = []
    for result in match_source_paths_to_binary(
        to_resource=to_resource,
        from_resources=from_resources,
        binary_symbols=binary_symbols,
        map_type=map_type,
        logger=logger,
    ):
        stats = result.get_stats_mapping()
        result.from_resource.extra_data["match_stats"] = stats
        if not result.is_matched:
            paths_not_mapped.append(result.from_resource.path)
            unmapped_source_files_with_stats[result.from_resource.path] = stats
        else:
            if result.relation_key not in relations_to_create:
                relations_to_create[result.relation_key] = result.codebase_relation

        result.from_resource.save()

    # If there are any non-test files in the rust source files which
    # are not mapped, we mark the binary as REQUIRES_REVIEW
    has_undeployed_unmapped_files = any(
        [True for path in paths_not_mapped if "/tests/" not in path]
    )
    if paths_not_mapped and has_undeployed_unmapped_files:
        to_resource.update(status=flag.REQUIRES_REVIEW)
        warning_message = (
            f"WARNING: #{len(paths_not_mapped)} {map_type} paths NOT mapped for: "
            f"{to_resource.path!r}"
        )
        project.add_warning(
            description=warning_message,
            model="map_resources_with_symbols",
            details=unmapped_source_files_with_stats,
        )

    to_resource.save()

    if relations_to_create:
        rels = CodebaseRelation.objects.bulk_create(relations_to_create.values())
        from_resources.has_relation().update(status=flag.MAPPED_BY_SYMBOL)
        if logger:
            logger(
                f"Created {len(rels)} mappings using "
                f"{map_type} for: {to_resource.path!r}"
            )

    elif logger:
        logger(f"No mappings using {map_type} for: {to_resource.path!r}")


def match_source_symbols_to_binary(source_symbols, binary_symbols, map_type):
    binary_symbols_set = set(binary_symbols)
    source_symbols_set = set(source_symbols)
    source_symbols_count = len(source_symbols)
    source_symbols_unique_count = len(source_symbols_set)

    source_symbols_counter = Counter(source_symbols)

    matched_symbols = source_symbols_set.intersection(binary_symbols_set)
    unmatched_symbols = source_symbols_set.difference(matched_symbols)

    matched_symbols_count = sum(
        [source_symbols_counter.get(symbol) for symbol in matched_symbols]
    )
    matched_symbols_ratio = matched_symbols_count / source_symbols_count
    matched_symbols_unique_count = len(matched_symbols)
    matched_symbols_unique_ratio = (
        matched_symbols_unique_count / source_symbols_unique_count
    )
    stats = {
        "matched_symbols_unique_ratio": f"{matched_symbols_unique_ratio:.2f}",
        "matched_symbols_ratio": f"{matched_symbols_ratio:.2f}",
        "source_symbols_count": f"{source_symbols_count:.2f}",
        "matched_symbols_count": f"{matched_symbols_count:.2f}",
        "matched_symbols": list(matched_symbols),
        "unmatched_symbols": list(unmatched_symbols),
    }

    if map_type == "rust_symbols":
        if (
            matched_symbols_ratio > MATCHING_RATIO_RUST
            or matched_symbols_unique_ratio > MATCHING_RATIO_RUST
        ):
            return True, stats
        elif source_symbols_count > SMALL_FILE_SYMBOLS_THRESHOLD and (
            matched_symbols_ratio > MATCHING_RATIO_RUST_SMALL_FILE
            or matched_symbols_unique_ratio > MATCHING_RATIO_RUST_SMALL_FILE
        ):
            return True, stats
        else:
            return False, stats

    elif map_type == "elf_symbols":
        if (
            matched_symbols_ratio > MATCHING_RATIO_ELF
            or matched_symbols_unique_ratio > MATCHING_RATIO_ELF
        ):
            return True, stats
        else:
            return False, stats
    elif map_type == "macho_symbols":
        if (
            matched_symbols_ratio > MATCHING_RATIO_MACHO
            or matched_symbols_unique_ratio > MATCHING_RATIO_MACHO
        ):
            return True, stats
        else:
            return False, stats
    elif map_type == "winpe_symbols":
        if (
            matched_symbols_ratio > MATCHING_RATIO_WINPE
            or matched_symbols_unique_ratio > MATCHING_RATIO_WINPE
        ):
            return True, stats
        else:
            return False, stats


def match_source_paths_to_binary(
    to_resource,
    from_resources,
    binary_symbols,
    map_type,
    logger=None,
):
    resource_iterator = from_resources.iterator(chunk_size=2000)
    progress = LoopProgress(from_resources.count(), logger)

    for resource in progress.iter(resource_iterator):
        symbol_match_result = SymbolsMatchResult(
            from_resource=resource,
            is_matched=False,
        )
        source_symbols = resource.extra_data.get("source_symbols")
        if not source_symbols:
            yield symbol_match_result
            continue

        is_source_matched, match_stats = match_source_symbols_to_binary(
            source_symbols=source_symbols,
            binary_symbols=binary_symbols,
            map_type=map_type,
        )
        symbol_match_result.update_stats_from_mapping(data=match_stats)
        if not is_source_matched:
            yield symbol_match_result
            continue

        symbol_match_result.is_matched = True
        symbol_match_result.relation_key = (resource.path, to_resource.path, map_type)
        symbol_match_result.codebase_relation = CodebaseRelation(
            project=resource.project,
            from_resource=resource,
            to_resource=to_resource,
            map_type=map_type,
            extra_data=match_stats,
        )
        yield symbol_match_result


def is_decomposed_javascript(symbols):
    """Return whether given set of symbols represents decomposed JavaScript code."""
    meaningful_symbols = sum(1 for k in symbols if len(k) > 3)
    ratio = meaningful_symbols / len(symbols) if meaningful_symbols > 0 else 0

    return ratio < JAVASCRIPT_DECOMPOSED_SYMBOLS_THRESHOLD


def get_symbols_probability_distribution(symbols, unique_symbols):
    """Compute probability distribution of symbols based on their frequency."""
    counter = Counter(symbols)
    total_count = len(symbols)

    probability_dist = [
        (counter.get(symbol) / total_count) if symbol in counter else 0
        for symbol in unique_symbols
    ]

    return probability_dist


def jensenshannon(p, q):
    """Compute the Jensen-Shannon distance between two probability distributions."""
    m = [(pi + qi) / 2.0 for pi, qi in zip(p, q)]

    left = 0.0
    right = 0.0
    for pi, qi, mi in zip(p, q, m):
        if pi > 0:
            left += pi * math.log(pi / mi)
        if qi > 0:
            right += qi * math.log(qi / mi)

    return math.sqrt((left + right) / 2.0)


def get_similarity_between_source_and_deployed_symbols(
    source_symbols,
    deployed_symbols,
    matching_ratio,
    matching_ratio_small_file,
    small_file_threshold,
):
    """
    Compute similarity between source and deployed symbols based on Jensen-Shannon
    Divergence and return whether they match based on provided threshold.
    """
    unique_symbols = set(source_symbols).union(set(deployed_symbols))

    source_probability_dist = get_symbols_probability_distribution(
        source_symbols, unique_symbols
    )
    deployed_probability_dist = get_symbols_probability_distribution(
        deployed_symbols, unique_symbols
    )

    divergence = jensenshannon(source_probability_dist, deployed_probability_dist)
    similarity = 1 - divergence

    matching_threshold = matching_ratio
    if len(deployed_symbols) <= small_file_threshold:
        matching_threshold = matching_ratio_small_file

    is_match = similarity >= matching_threshold

    return is_match, similarity


def match_javascript_source_symbols_to_deployed(source_symbols, deployed_symbols):
    """Match source and deployed symbols using Jensen-Shannon Divergence."""
    is_match, similarity = get_similarity_between_source_and_deployed_symbols(
        source_symbols=source_symbols,
        deployed_symbols=deployed_symbols,
        matching_ratio=MATCHING_RATIO_JAVASCRIPT,
        matching_ratio_small_file=MATCHING_RATIO_JAVASCRIPT_SMALL_FILE,
        small_file_threshold=SMALL_FILE_SYMBOLS_THRESHOLD_JAVASCRIPT,
    )

    return is_match, similarity

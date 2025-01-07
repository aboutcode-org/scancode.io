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

from collections import Counter

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


def map_resources_with_symbols(
    to_resource, from_resources, binary_symbols, map_type, logger=None
):
    """
    Map paths found in the ``to_resource`` extra_data to paths of the ``from_resources``
    CodebaseResource queryset using the precomputed ``from_resources_index`` path index.
    """
    if not binary_symbols:
        return

    # Accumulate unique relation objects for bulk creation
    relations_to_create = {}

    # These are of type string
    paths_not_mapped = to_resource.extra_data[f"{map_type}_not_mapped"] = []
    for item in match_source_paths_to_binary(
        to_resource=to_resource,
        from_resources=from_resources,
        binary_symbols=binary_symbols,
        map_type=map_type,
        logger=logger,
    ):
        if isinstance(item, str):
            paths_not_mapped.append(item)
        else:
            rel_key, relation = item
            if rel_key not in relations_to_create:
                relations_to_create[rel_key] = relation

    # If there are any non-test files in the rust source files which
    # are not mapped, we mark the binary as REQUIRES_REVIEW
    has_non_test_unmapped_files = any(
        [True for path in paths_not_mapped if "/tests/" not in path]
    )
    if paths_not_mapped and has_non_test_unmapped_files:
        to_resource.update(status=flag.REQUIRES_REVIEW)
        if logger:
            logger(
                f"WARNING: #{len(paths_not_mapped)} {map_type} paths NOT mapped for: "
                f"{to_resource.path!r}"
            )

    if relations_to_create:
        rels = CodebaseRelation.objects.bulk_create(relations_to_create.values())
        from_resources.has_relation().update(status=flag.MAPPED_BY_SYMBOL)
        if logger:
            logger(
                f"Created {len(rels)} mappings using "
                f"{map_type} for: {to_resource.path!r}"
            )

    elif logger:
        logger(f"No mappings using {map_type} for: " f"{to_resource.path!r}")


def match_source_symbols_to_binary(source_symbols, binary_symbols):
    binary_symbols_set = set(binary_symbols)
    source_symbols_set = set(source_symbols)
    source_symbols_count = len(source_symbols)
    source_symbols_unique_count = len(source_symbols_set)

    source_symbols_counter = Counter(source_symbols)

    common_symbols = source_symbols_set.intersection(binary_symbols_set)
    common_symbols_count = sum(
        [source_symbols_counter.get(symbol) for symbol in common_symbols]
    )
    common_symbols_ratio = common_symbols_count / source_symbols_count
    common_symbols_unique_count = len(common_symbols)
    common_symbols_unique_ratio = (
        common_symbols_unique_count / source_symbols_unique_count
    )
    stats = {
        "common_symbols_unique_ratio": common_symbols_unique_ratio,
        "common_symbols_ratio": common_symbols_ratio,
    }

    if (
        common_symbols_ratio > MATCHING_RATIO_RUST
        or common_symbols_unique_ratio > MATCHING_RATIO_RUST
    ):
        return True, stats
    elif source_symbols_count > SMALL_FILE_SYMBOLS_THRESHOLD and (
        common_symbols_ratio > MATCHING_RATIO_RUST_SMALL_FILE
        or common_symbols_unique_ratio > MATCHING_RATIO_RUST_SMALL_FILE
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
        source_symbols = resource.extra_data.get("source_symbols")
        if not source_symbols:
            yield resource.path
            continue

        is_source_matched, match_stats = match_source_symbols_to_binary(
            source_symbols=source_symbols,
            binary_symbols=binary_symbols,
        )
        if not is_source_matched:
            yield resource.path
            continue

        rel_key = (resource.path, to_resource.path, map_type)
        relation = CodebaseRelation(
            project=resource.project,
            from_resource=resource,
            to_resource=to_resource,
            map_type=map_type,
            extra_data=match_stats,
        )
        yield rel_key, relation

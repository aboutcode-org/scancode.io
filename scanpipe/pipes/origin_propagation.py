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
from pathlib import Path

from scanpipe.models import CodebaseRelation
from scanpipe.models import PropagationBatch
from scanpipe.pipes import make_relation


def get_propagation_candidates(
    project,
    relation,
    strategy,
    similarity_threshold=0.8,
    pattern=None,
    logger=None,
):
    """
    Preview what resources would be affected by propagation.
    Returns a list of tuples: (to_resource, from_resource, map_type, confidence)
    """
    candidates = []

    if strategy == "similar":
        candidates = _get_similar_candidates(
            project, relation, similarity_threshold, logger
        )
    elif strategy == "directory":
        candidates = _get_directory_candidates(project, relation, logger)
    elif strategy == "package":
        candidates = _get_package_candidates(project, relation, logger)
    elif strategy == "pattern":
        if not pattern:
            if logger:
                logger("Pattern strategy requires a pattern parameter.")
            return []
        candidates = _get_pattern_candidates(project, relation, pattern, logger)

    return candidates


def propagate_origin_to_similar_resources(
    project,
    relation,
    similarity_threshold=0.8,
    user=None,
    logger=None,
):
    """
    Propagate origin determination to similar resources based on path similarity
    and checksum matching.

    Similarity is determined by:
    - Path similarity (common path segments)
    - Checksum matching (sha1, md5)
    """
    candidates = _get_similar_candidates(
        project, relation, similarity_threshold, logger
    )
    return _apply_propagation(project, relation, candidates, "similar", user, logger)


def propagate_origin_by_directory_structure(
    project,
    relation,
    user=None,
    logger=None,
):
    """
    Propagate origin determination to sibling files in the same directory structure.

    For each to_resource in the same directory as the relation's to_resource,
    find corresponding from_resource in the same directory as the relation's
    from_resource.
    """
    candidates = _get_directory_candidates(project, relation, logger)
    return _apply_propagation(project, relation, candidates, "directory", user, logger)


def propagate_origin_by_package(
    project,
    relation,
    user=None,
    logger=None,
):
    """
    Propagate origin determination to all resources in the same package.

    If the relation's to_resource belongs to a package, apply the same origin
    determination to all other to_resources in that package.
    """
    candidates = _get_package_candidates(project, relation, logger)
    return _apply_propagation(project, relation, candidates, "package", user, logger)


def propagate_origin_by_pattern(
    project,
    relation,
    pattern,
    user=None,
    logger=None,
):
    """
    Propagate origin determination to resources matching a path pattern.

    Pattern can be a glob pattern or regex pattern.
    """
    candidates = _get_pattern_candidates(project, relation, pattern, logger)
    return _apply_propagation(project, relation, candidates, "pattern", user, logger)


def _get_similar_candidates(  # noqa: C901 - complex similarity heuristics
    project, relation, similarity_threshold, logger=None
):
    """Find similar resources based on path and checksum."""
    candidates = []
    source_from = relation.from_resource
    source_to = relation.to_resource

    # Get all unmapped to_resources in the same codebase side
    to_resources = (
        project.codebaseresources.to_codebase()
        .files()
        .has_no_relation()
        .exclude(path=source_to.path)
    )

    # Try checksum matching first (most reliable)
    if source_to.sha1:
        sha1_matches = to_resources.filter(sha1=source_to.sha1)
        for to_res in sha1_matches:
            # Find corresponding from_resource with same checksum
            from_matches = (
                project.codebaseresources.from_codebase()
                .files()
                .filter(sha1=source_to.sha1)
            )
            for from_res in from_matches:
                candidates.append((to_res, from_res, "sha1", "high"))

    # Try path similarity
    source_to_path_parts = Path(source_to.path.lstrip("/")).parts
    source_from_path_parts = Path(source_from.path.lstrip("/")).parts

    # Calculate relative path difference
    if len(source_to_path_parts) > 1 and len(source_from_path_parts) > 1:
        # Get directory structure
        to_dir = "/".join(source_to_path_parts[:-1])
        from_dir = "/".join(source_from_path_parts[:-1])
        from_dir_parts = set(from_dir.split("/"))

        # Find resources in similar directory structures
        for to_res in to_resources:
            to_res_path_parts = Path(to_res.path.lstrip("/")).parts
            if len(to_res_path_parts) <= 1:
                continue

            to_res_dir = "/".join(to_res_path_parts[:-1])
            to_res_name = to_res_path_parts[-1]

            # Calculate directory similarity
            to_dir_parts = set(to_dir.split("/"))
            to_res_dir_parts = set(to_res_dir.split("/"))
            if to_dir_parts and to_res_dir_parts:
                dir_similarity = len(to_dir_parts & to_res_dir_parts) / len(
                    to_dir_parts | to_res_dir_parts
                )
                if dir_similarity >= similarity_threshold:
                    # Find from_resource with same name in similar directory
                    from_candidates = (
                        project.codebaseresources.from_codebase()
                        .files()
                        .filter(name=to_res_name)
                    )
                    for from_res in from_candidates:
                        from_res_dir = "/".join(
                            Path(from_res.path.lstrip("/")).parts[:-1]
                        )
                        from_res_dir_parts = set(from_res_dir.split("/"))
                        if from_res_dir_parts:
                            from_dir_similarity = len(
                                from_dir_parts & from_res_dir_parts
                            ) / len(from_dir_parts | from_res_dir_parts)
                            if from_dir_similarity >= similarity_threshold:
                                candidates.append((to_res, from_res, "path", "medium"))

    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for candidate in candidates:
        key = (candidate[0].path, candidate[1].path)
        if key not in seen:
            seen.add(key)
            unique_candidates.append(candidate)

    return unique_candidates


def _get_directory_candidates(project, relation, logger=None):
    """Find sibling files in same directory structure."""
    candidates = []
    source_from = relation.from_resource
    source_to = relation.to_resource

    # Get parent directories
    to_parent = str(Path(source_to.path).parent)
    from_parent = str(Path(source_from.path).parent)

    # Get all files in the same to/ directory
    to_siblings = (
        project.codebaseresources.to_codebase()
        .files()
        .has_no_relation()
        .filter(parent_path=to_parent)
        .exclude(path=source_to.path)
    )

    # For each sibling, try to find corresponding from_resource
    for to_sibling in to_siblings:
        # Try exact name match first
        from_matches = (
            project.codebaseresources.from_codebase()
            .files()
            .filter(name=to_sibling.name, parent_path=from_parent)
        )
        if from_matches.exists():
            candidates.append((to_sibling, from_matches.first(), "path", "high"))
        else:
            # Try extension match
            if to_sibling.extension:
                from_matches = (
                    project.codebaseresources.from_codebase()
                    .files()
                    .filter(
                        extension=to_sibling.extension,
                        parent_path=from_parent,
                    )
                )
                if from_matches.exists():
                    candidates.append(
                        (to_sibling, from_matches.first(), "path", "medium")
                    )

    return candidates


def _get_package_candidates(project, relation, logger=None):
    """Find resources in the same package."""
    candidates = []
    source_from = relation.from_resource
    source_to = relation.to_resource

    # Get packages for source resources
    to_packages = source_to.discovered_packages.all()
    if not to_packages.exists():
        if logger:
            logger(f"Source to_resource {source_to.path} has no packages.")
        return []

    # Get all to_resources in the same packages
    to_resources = (
        project.codebaseresources.to_codebase()
        .files()
        .has_no_relation()
        .filter(discovered_packages__in=to_packages)
        .distinct()
        .exclude(path=source_to.path)
    )

    # For each to_resource, try to find corresponding from_resource
    # Use the same relative path structure
    source_to_rel_path = _get_relative_path_from_package(source_to, to_packages.first())
    source_from_rel_path = _get_relative_path_from_package(
        source_from, source_from.discovered_packages.first()
    )

    if source_to_rel_path and source_from_rel_path:
        for to_res in to_resources:
            to_rel_path = _get_relative_path_from_package(to_res, to_packages.first())
            if not to_rel_path:
                continue

            # Try to find from_resource with similar relative path
            from_candidates = project.codebaseresources.from_codebase().files()
            # Match by name first
            from_candidates = from_candidates.filter(name=to_res.name)
            if from_candidates.exists():
                candidates.append((to_res, from_candidates.first(), "path", "medium"))

    return candidates


def _get_pattern_candidates(project, relation, pattern, logger=None):
    """Find resources matching a path pattern."""
    candidates = []

    # Determine if pattern is regex or glob
    try:
        # Try as regex first
        regex_pattern = re.compile(pattern)
    except re.error:
        # Treat as glob pattern
        # Convert glob to regex
        regex_pattern = re.compile(
            "^" + pattern.replace("*", ".*").replace("?", ".") + "$"
        )

    # Find all to_resources matching the pattern
    to_resources = project.codebaseresources.to_codebase().files().has_no_relation()

    matching_to_resources = []
    for to_res in to_resources:
        if regex_pattern.search(to_res.path):
            matching_to_resources.append(to_res)

    # For each matching to_resource, try to find corresponding from_resource
    # Use similar matching logic as directory structure
    for to_res in matching_to_resources:
        # Try name match
        from_matches = (
            project.codebaseresources.from_codebase().files().filter(name=to_res.name)
        )
        if from_matches.exists():
            candidates.append((to_res, from_matches.first(), "path", "medium"))

    return candidates


def _get_relative_path_from_package(resource, package):
    """Get relative path of resource from package root."""
    if not package:
        return None

    # Try to determine package root from resource path
    # This is a simplified version - may need enhancement
    # For now, return the resource path as-is
    return resource.path


def _apply_propagation(  # noqa: C901 - propagation workflow
    project,
    source_relation,
    candidates,
    map_type_prefix,
    user=None,
    logger=None,
):
    """
    Apply propagation by creating relations for candidates.
    Returns (count, created_relations, batch) tuple.
    """
    count = 0
    created_relations = []

    # Create propagation batch for tracking
    batch = None
    if user and user.is_authenticated:
        batch = PropagationBatch.objects.create(
            project=project,
            source_relation=source_relation,
            strategy=map_type_prefix,
            created_by=user,
            relation_count=0,
            extra_data={},
        )

    for to_resource, from_resource, map_type, confidence in candidates:
        # Check if relation already exists (any map_type)
        existing = CodebaseRelation.objects.filter(
            project=project,
            from_resource=from_resource,
            to_resource=to_resource,
        ).exists()

        if existing:
            if logger:
                logger(
                    f"Relation already exists: {to_resource.path} -> "
                    f"{from_resource.path}"
                )
            continue

        # Create relation
        try:
            extra_data = {
                "propagated_from": str(source_relation.uuid),
                "confidence": confidence,
            }
            if batch:
                extra_data["propagation_batch"] = str(batch.uuid)

            relation = make_relation(
                from_resource=from_resource,
                to_resource=to_resource,
                map_type=f"{map_type_prefix}_{map_type}",
                extra_data=extra_data,
            )
            created_relations.append(relation)
            count += 1

            if logger:
                logger(
                    f"Created relation: {to_resource.path} -> {from_resource.path} "
                    f"(confidence: {confidence})"
                )
        except Exception as e:
            if logger:
                logger(f"Error creating relation: {e}")

    # Update batch with actual count
    if batch:
        batch.relation_count = count
        batch.save(update_fields=["relation_count"])

    if logger:
        logger(f"Propagation complete: {count} relations created.")

    return count, created_relations, batch

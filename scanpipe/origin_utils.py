"""
Utility functions for working with Code Origin Determinations.

This module provides helper functions for creating and managing origin determinations
from scan results and other data sources.
"""

from scanpipe.models import CodeOriginDetermination, CodebaseResource


def create_origin_from_package_data(resource, package_data, confidence=0.8, method="package_data"):
    """
    Create an origin determination from package data.
    
    Args:
        resource: CodebaseResource instance
        package_data: Dictionary containing package information
        confidence: Confidence score (0.0 to 1.0)
        method: Detection method name
    
    Returns:
        CodeOriginDetermination instance or None if already exists
    """
    # Check if origin determination already exists
    if hasattr(resource, 'origin_determination'):
        return None
    
    origin_type = "package"
    origin_identifier = package_data.get("purl", "")
    
    if not origin_identifier:
        # Try to construct from package data
        name = package_data.get("name")
        version = package_data.get("version")
        package_type = package_data.get("type", "generic")
        
        if name and version:
            origin_identifier = f"pkg:{package_type}/{name}@{version}"
    
    if not origin_identifier:
        return None
    
    metadata = {
        "package_name": package_data.get("name"),
        "package_version": package_data.get("version"),
        "package_type": package_data.get("type"),
    }
    
    return CodeOriginDetermination.objects.create(
        codebase_resource=resource,
        detected_origin_type=origin_type,
        detected_origin_identifier=origin_identifier,
        detected_origin_confidence=confidence,
        detected_origin_method=method,
        detected_origin_metadata=metadata,
    )


def create_origin_from_repository(resource, repo_url, confidence=0.9, method="git_detection"):
    """
    Create an origin determination from repository URL.
    
    Args:
        resource: CodebaseResource instance
        repo_url: Repository URL
        confidence: Confidence score (0.0 to 1.0)
        method: Detection method name
    
    Returns:
        CodeOriginDetermination instance or None if already exists
    """
    if hasattr(resource, 'origin_determination'):
        return None
    
    return CodeOriginDetermination.objects.create(
        codebase_resource=resource,
        detected_origin_type="repository",
        detected_origin_identifier=repo_url,
        detected_origin_confidence=confidence,
        detected_origin_method=method,
        detected_origin_metadata={"repository_url": repo_url},
    )


def bulk_create_origins_from_scan_results(project, scan_results):
    """
    Bulk create origin determinations from scan results.
    
    Args:
        project: Project instance
        scan_results: List of dictionaries containing scan result data
            Each dict should have keys: 'path', 'origin_type', 'origin_identifier', 
            'confidence', 'method', 'metadata'
    
    Returns:
        Tuple of (created_count, skipped_count)
    """
    created_count = 0
    skipped_count = 0
    
    # Get all resources for the project
    resources_by_path = {
        r.path: r 
        for r in project.codebaseresources.all()
    }
    
    # Get existing origin determinations
    existing_resources = set(
        CodeOriginDetermination.objects.filter(
            codebase_resource__project=project
        ).values_list('codebase_resource__path', flat=True)
    )
    
    origins_to_create = []
    
    for result in scan_results:
        path = result.get('path')
        resource = resources_by_path.get(path)
        
        if not resource or path in existing_resources:
            skipped_count += 1
            continue
        
        origin = CodeOriginDetermination(
            codebase_resource=resource,
            detected_origin_type=result.get('origin_type', 'unknown'),
            detected_origin_identifier=result.get('origin_identifier', ''),
            detected_origin_confidence=result.get('confidence', 0.5),
            detected_origin_method=result.get('method', 'unknown'),
            detected_origin_metadata=result.get('metadata', {}),
        )
        origins_to_create.append(origin)
        created_count += 1
    
    # Bulk create
    if origins_to_create:
        CodeOriginDetermination.objects.bulk_create(origins_to_create)
    
    return created_count, skipped_count


def update_origin_confidence(origin_uuid, new_confidence, reason=""):
    """
    Update the confidence score for an origin determination.
    
    Args:
        origin_uuid: UUID of the origin determination
        new_confidence: New confidence score (0.0 to 1.0)
        reason: Optional reason for the update
    
    Returns:
        Updated CodeOriginDetermination instance
    """
    origin = CodeOriginDetermination.objects.get(uuid=origin_uuid)
    
    # Store old confidence in metadata
    if 'confidence_history' not in origin.detected_origin_metadata:
        origin.detected_origin_metadata['confidence_history'] = []
    
    origin.detected_origin_metadata['confidence_history'].append({
        'old_confidence': origin.detected_origin_confidence,
        'new_confidence': new_confidence,
        'reason': reason,
    })
    
    origin.detected_origin_confidence = new_confidence
    origin.save()
    
    return origin


def get_origins_by_confidence(project, min_confidence=None, max_confidence=None):
    """
    Get origin determinations filtered by confidence range.
    
    Args:
        project: Project instance
        min_confidence: Minimum confidence threshold (0.0 to 1.0)
        max_confidence: Maximum confidence threshold (0.0 to 1.0)
    
    Returns:
        QuerySet of CodeOriginDetermination instances
    """
    qs = CodeOriginDetermination.objects.filter(
        codebase_resource__project=project
    )
    
    if min_confidence is not None:
        qs = qs.filter(detected_origin_confidence__gte=min_confidence)
    
    if max_confidence is not None:
        qs = qs.filter(detected_origin_confidence__lte=max_confidence)
    
    return qs


def verify_origins_by_type(project, origin_type):
    """
    Mark all origins of a specific type as verified.
    
    Args:
        project: Project instance
        origin_type: Origin type to verify ('package', 'repository', 'url', 'unknown')
    
    Returns:
        Number of origins verified
    """
    return CodeOriginDetermination.objects.filter(
        codebase_resource__project=project,
        detected_origin_type=origin_type,
        is_verified=False
    ).update(is_verified=True)


def get_origin_statistics(project):
    """
    Get statistics about origin determinations for a project.
    
    Args:
        project: Project instance
    
    Returns:
        Dictionary with statistics
    """
    from django.db.models import Count, Avg, Q
    
    origins = CodeOriginDetermination.objects.filter(
        codebase_resource__project=project
    )
    
    total = origins.count()
    verified = origins.filter(is_verified=True).count()
    amended = origins.exclude(
        Q(amended_origin_type="") & Q(amended_origin_identifier="")
    ).count()
    
    by_type = origins.values('detected_origin_type').annotate(
        count=Count('uuid')
    ).order_by('-count')
    
    avg_confidence = origins.aggregate(
        avg=Avg('detected_origin_confidence')
    )['avg'] or 0
    
    high_confidence = origins.filter(detected_origin_confidence__gte=0.9).count()
    medium_confidence = origins.filter(
        detected_origin_confidence__gte=0.7,
        detected_origin_confidence__lt=0.9
    ).count()
    low_confidence = origins.filter(detected_origin_confidence__lt=0.7).count()
    
    return {
        'total': total,
        'verified': verified,
        'verified_percentage': (verified / total * 100) if total > 0 else 0,
        'amended': amended,
        'amended_percentage': (amended / total * 100) if total > 0 else 0,
        'by_type': list(by_type),
        'average_confidence': avg_confidence,
        'high_confidence_count': high_confidence,
        'medium_confidence_count': medium_confidence,
        'low_confidence_count': low_confidence,
    }


# ============================================================================
# ORIGIN PROPAGATION UTILITIES
# ============================================================================


def find_similar_files_by_path(resource, max_results=50):
    """
    Find files with similar path patterns to the given resource.
    
    Uses directory structure, naming patterns, and file extensions as signals.
    
    Args:
        resource: CodebaseResource instance
        max_results: Maximum number of similar files to return
    
    Returns:
        QuerySet of similar CodebaseResource instances
    """
    import os
    from django.db.models import Q
    
    path = resource.path
    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    name, ext = os.path.splitext(filename)
    
    # Build query for similar files
    q = Q()
    
    # Same directory
    if directory:
        q |= Q(path__startswith=directory + "/")
    
    # Same extension
    if ext:
        q |= Q(path__endswith=ext)
    
    # Similar filename (without extension)
    if name:
        q |= Q(path__icontains=name)
    
    # Exclude the resource itself
    similar = resource.project.codebaseresources.filter(q).exclude(
        pk=resource.pk
    ).exclude(
        # Exclude files that already have origins
        origin_determination__isnull=False
    )[:max_results]
    
    return similar


def find_files_in_same_package(resource):
    """
    Find files that belong to the same package as the given resource.
    
    Uses package data and package membership to identify related files.
    
    Args:
        resource: CodebaseResource instance with package information
    
    Returns:
        QuerySet of CodebaseResource instances in the same package
    """
    from django.db.models import Q
    
    # Get package information from the resource
    if not resource.discovered_packages.exists():
        return resource.project.codebaseresources.none()
    
    # Find all files that belong to the same packages
    package_uuids = list(
        resource.discovered_packages.values_list('uuid', flat=True)
    )
    
    related_files = resource.project.codebaseresources.filter(
        discovered_packages__uuid__in=package_uuids
    ).exclude(
        pk=resource.pk
    ).exclude(
        # Exclude files that already have origins
        origin_determination__isnull=False
    ).distinct()
    
    return related_files


def find_files_with_similar_licenses(resource, threshold=0.7):
    """
    Find files with similar license detection results.
    
    Uses license keys and license expressions to identify files with
    similar licensing.
    
    Args:
        resource: CodebaseResource instance
        threshold: Similarity threshold (0.0 to 1.0)
    
    Returns:
        List of tuples (CodebaseResource, similarity_score)
    """
    from django.db.models import Q
    
    if not resource.detected_license_expression:
        return []
    
    # Get license expression for the resource
    target_licenses = set(resource.detected_license_expression.split(" AND "))
    
    if not target_licenses:
        return []
    
    # Find files with overlapping licenses
    similar_files = []
    
    candidates = resource.project.codebaseresources.filter(
        detected_license_expression__isnull=False
    ).exclude(
        pk=resource.pk
    ).exclude(
        # Exclude files that already have origins
        origin_determination__isnull=False
    )
    
    for candidate in candidates:
        candidate_licenses = set(
            candidate.detected_license_expression.split(" AND ")
        )
        
        # Calculate Jaccard similarity
        intersection = target_licenses.intersection(candidate_licenses)
        union = target_licenses.union(candidate_licenses)
        
        if union:
            similarity = len(intersection) / len(union)
            
            if similarity >= threshold:
                similar_files.append((candidate, similarity))
    
    # Sort by similarity score (descending)
    similar_files.sort(key=lambda x: x[1], reverse=True)
    
    return similar_files


def calculate_propagation_confidence(
    source_origin, 
    target_resource, 
    method, 
    similarity_score=None
):
    """
    Calculate confidence score for origin propagation.
    
    Considers source confidence, propagation method, and similarity signals.
    
    Args:
        source_origin: CodeOriginDetermination to propagate from
        target_resource: CodebaseResource to propagate to
        method: Propagation method name
        similarity_score: Optional similarity score (0.0 to 1.0)
    
    Returns:
        Confidence score (0.0 to 1.0)
    """
    # Start with source confidence
    base_confidence = source_origin.detected_origin_confidence or 0.5
    
    # Apply method-specific modifiers
    method_modifiers = {
        "package_membership": 0.95,  # High confidence - same package
        "path_pattern_same_dir": 0.85,  # High confidence - same directory
        "path_pattern_similar": 0.70,  # Medium confidence - similar path
        "license_similarity": 0.75,  # Medium-high confidence
        "combined_signals": 0.80,  # Multiple signals
    }
    
    method_modifier = method_modifiers.get(method, 0.60)
    
    # Calculate propagated confidence
    propagated_confidence = base_confidence * method_modifier
    
    # If similarity score provided, factor it in
    if similarity_score is not None:
        propagated_confidence = (propagated_confidence + similarity_score) / 2
    
    # Cap at very high confidence (max 0.95 for propagated origins)
    propagated_confidence = min(propagated_confidence, 0.95)
    
    return propagated_confidence


def propagate_origin_by_package_membership(source_origin, max_targets=100):
    """
    Propagate origin to files in the same package.
    
    Args:
        source_origin: CodeOriginDetermination to propagate from
        max_targets: Maximum number of targets to propagate to
    
    Returns:
        List of newly created CodeOriginDetermination instances
    """
    if not source_origin.can_be_propagation_source:
        return []
    
    source_resource = source_origin.codebase_resource
    target_resources = find_files_in_same_package(source_resource)[:max_targets]
    
    propagated_origins = []
    
    for target_resource in target_resources:
        confidence = calculate_propagation_confidence(
            source_origin, 
            target_resource, 
            "package_membership"
        )
        
        propagated_origin = CodeOriginDetermination.objects.create(
            codebase_resource=target_resource,
            detected_origin_type=source_origin.effective_origin_type,
            detected_origin_identifier=source_origin.effective_origin_identifier,
            detected_origin_confidence=confidence,
            detected_origin_method=f"propagated_from_{source_origin.detected_origin_method}",
            detected_origin_metadata={
                "propagation_source_uuid": str(source_origin.uuid),
                "propagation_source_path": source_resource.path,
            },
            is_propagated=True,
            propagation_source=source_origin,
            propagation_method="package_membership",
            propagation_confidence=confidence,
            propagation_metadata={
                "reason": "Same package membership",
                "source_path": source_resource.path,
            },
        )
        
        propagated_origins.append(propagated_origin)
    
    return propagated_origins


def propagate_origin_by_path_pattern(source_origin, max_targets=100):
    """
    Propagate origin to files with similar path patterns.
    
    Args:
        source_origin: CodeOriginDetermination to propagate from
        max_targets: Maximum number of targets to propagate to
    
    Returns:
        List of newly created CodeOriginDetermination instances
    """
    import os
    
    if not source_origin.can_be_propagation_source:
        return []
    
    source_resource = source_origin.codebase_resource
    similar_files = find_similar_files_by_path(source_resource, max_targets)
    
    propagated_origins = []
    
    for target_resource in similar_files:
        # Determine if same directory or just similar
        source_dir = os.path.dirname(source_resource.path)
        target_dir = os.path.dirname(target_resource.path)
        
        if source_dir == target_dir:
            method = "path_pattern_same_dir"
        else:
            method = "path_pattern_similar"
        
        confidence = calculate_propagation_confidence(
            source_origin, 
            target_resource, 
            method
        )
        
        propagated_origin = CodeOriginDetermination.objects.create(
            codebase_resource=target_resource,
            detected_origin_type=source_origin.effective_origin_type,
            detected_origin_identifier=source_origin.effective_origin_identifier,
            detected_origin_confidence=confidence,
            detected_origin_method=f"propagated_from_{source_origin.detected_origin_method}",
            detected_origin_metadata={
                "propagation_source_uuid": str(source_origin.uuid),
                "propagation_source_path": source_resource.path,
            },
            is_propagated=True,
            propagation_source=source_origin,
            propagation_method=method,
            propagation_confidence=confidence,
            propagation_metadata={
                "reason": "Similar path pattern",
                "source_path": source_resource.path,
                "source_dir": source_dir,
                "target_dir": target_dir,
            },
        )
        
        propagated_origins.append(propagated_origin)
    
    return propagated_origins


def propagate_origin_by_license_similarity(source_origin, threshold=0.7, max_targets=100):
    """
    Propagate origin to files with similar license detection.
    
    Args:
        source_origin: CodeOriginDetermination to propagate from
        threshold: Minimum similarity score for propagation
        max_targets: Maximum number of targets to propagate to
    
    Returns:
        List of newly created CodeOriginDetermination instances
    """
    if not source_origin.can_be_propagation_source:
        return []
    
    source_resource = source_origin.codebase_resource
    similar_files = find_files_with_similar_licenses(
        source_resource, 
        threshold
    )[:max_targets]
    
    propagated_origins = []
    
    for target_resource, similarity_score in similar_files:
        confidence = calculate_propagation_confidence(
            source_origin, 
            target_resource, 
            "license_similarity",
            similarity_score
        )
        
        propagated_origin = CodeOriginDetermination.objects.create(
            codebase_resource=target_resource,
            detected_origin_type=source_origin.effective_origin_type,
            detected_origin_identifier=source_origin.effective_origin_identifier,
            detected_origin_confidence=confidence,
            detected_origin_method=f"propagated_from_{source_origin.detected_origin_method}",
            detected_origin_metadata={
                "propagation_source_uuid": str(source_origin.uuid),
                "propagation_source_path": source_resource.path,
            },
            is_propagated=True,
            propagation_source=source_origin,
            propagation_method="license_similarity",
            propagation_confidence=confidence,
            propagation_metadata={
                "reason": "Similar license detection",
                "source_path": source_resource.path,
                "similarity_score": similarity_score,
                "source_licenses": source_resource.detected_license_expression,
                "target_licenses": target_resource.detected_license_expression,
            },
        )
        
        propagated_origins.append(propagated_origin)
    
    return propagated_origins


def propagate_origins_for_project(
    project, 
    methods=None,
    min_source_confidence=0.8,
    max_targets_per_source=50
):
    """
    Main function to propagate origins across a project.
    
    Takes verified origins and propagates them to similar/related files
    using multiple methods.
    
    Args:
        project: Project instance
        methods: List of propagation methods to use (None = all methods)
            Available: 'package_membership', 'path_pattern', 'license_similarity'
        min_source_confidence: Minimum confidence for source origins
        max_targets_per_source: Max targets to propagate to per source
    
    Returns:
        Dictionary with propagation statistics
    """
    if methods is None:
        methods = ['package_membership', 'path_pattern', 'license_similarity']
    
    # Get all verified, high-confidence origins that can be propagation sources
    source_origins = CodeOriginDetermination.objects.filter(
        codebase_resource__project=project,
        is_verified=True,
        is_propagated=False,
        detected_origin_confidence__gte=min_source_confidence,
    )
    
    stats = {
        'source_origins_count': source_origins.count(),
        'propagated_by_method': {},
        'total_propagated': 0,
        'errors': [],
    }
    
    for source_origin in source_origins:
        try:
            if 'package_membership' in methods:
                propagated = propagate_origin_by_package_membership(
                    source_origin, 
                    max_targets_per_source
                )
                count = len(propagated)
                stats['propagated_by_method'].setdefault('package_membership', 0)
                stats['propagated_by_method']['package_membership'] += count
                stats['total_propagated'] += count
            
            if 'path_pattern' in methods:
                propagated = propagate_origin_by_path_pattern(
                    source_origin, 
                    max_targets_per_source
                )
                count = len(propagated)
                stats['propagated_by_method'].setdefault('path_pattern', 0)
                stats['propagated_by_method']['path_pattern'] += count
                stats['total_propagated'] += count
            
            if 'license_similarity' in methods:
                propagated = propagate_origin_by_license_similarity(
                    source_origin, 
                    max_targets=max_targets_per_source
                )
                count = len(propagated)
                stats['propagated_by_method'].setdefault('license_similarity', 0)
                stats['propagated_by_method']['license_similarity'] += count
                stats['total_propagated'] += count
                
        except Exception as e:
            stats['errors'].append({
                'source_origin_uuid': str(source_origin.uuid),
                'source_path': source_origin.codebase_resource.path,
                'error': str(e),
            })
    
    return stats


def get_propagation_statistics(project):
    """
    Get statistics about origin propagation for a project.
    
    Args:
        project: Project instance
    
    Returns:
        Dictionary with propagation statistics
    """
    from django.db.models import Count, Avg
    
    all_origins = CodeOriginDetermination.objects.filter(
        codebase_resource__project=project
    )
    
    propagated_origins = all_origins.filter(is_propagated=True)
    manual_origins = all_origins.filter(is_propagated=False)
    
    propagated_by_method = propagated_origins.values('propagation_method').annotate(
        count=Count('uuid')
    ).order_by('-count')
    
    avg_propagation_confidence = propagated_origins.aggregate(
        avg=Avg('propagation_confidence')
    )['avg'] or 0
    
    # Count how many propagated origins were later verified
    verified_propagated = propagated_origins.filter(is_verified=True).count()
    
    return {
        'total_origins': all_origins.count(),
        'manual_origins': manual_origins.count(),
        'propagated_origins': propagated_origins.count(),
        'propagated_percentage': (
            propagated_origins.count() / all_origins.count() * 100
            if all_origins.count() > 0 else 0
        ),
        'propagated_by_method': list(propagated_by_method),
        'average_propagation_confidence': avg_propagation_confidence,
        'verified_propagated_count': verified_propagated,
        'verified_propagated_percentage': (
            verified_propagated / propagated_origins.count() * 100
            if propagated_origins.count() > 0 else 0
        ),
    }

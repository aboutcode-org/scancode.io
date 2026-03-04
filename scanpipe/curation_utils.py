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

"""
Utilities for exporting, importing, and managing origin curations with FederatedCode.

This module provides functions for:
- Exporting curations to FederatedCode repositories
- Importing curations from external sources
- Resolving conflicts between curations
- Managing curation provenance
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from scanpipe.models import Project, CodeOriginDetermination, CodebaseResource
from scanpipe.models_curation import (
    CurationSource,
    CurationProvenance,
    CurationConflict,
    CurationExport,
)
from scanpipe.curation_schema import (
    CurationPackage,
    FileCuration,
    OriginData,
    ProvenanceRecord,
    validate_curation_package,
)
from scanpipe.pipes import federatedcode


logger = logging.getLogger(__name__)


def get_local_curation_source() -> CurationSource:
    """
    Get or create the local curation source representing this ScanCode.io instance.
    """
    source, created = CurationSource.objects.get_or_create(
        source_type="local",
        defaults={
            "name": "Local (This Instance)",
            "url": getattr(settings, "SCANCODEIO_BASE_URL", ""),
            "priority": 100,  # Local curations have highest priority
            "is_active": True,
        },
    )
    if created:
        logger.info("Created local curation source")
    return source


def origin_determination_to_origin_data(origin: CodeOriginDetermination) -> OriginData:
    """
    Convert a CodeOriginDetermination to OriginData schema object.
    """
    # Use amended if available, otherwise detected
    origin_type = origin.effective_origin_type or "unknown"
    origin_identifier = origin.effective_origin_identifier or ""
    
    # Determine confidence
    if origin.amended_origin_type:
        confidence = 1.0 if origin.is_verified else 0.9
    else:
        confidence = origin.detected_origin_confidence or 0.5
    
    # Determine detection method
    if origin.amended_origin_type:
        method = "manual_amendment"
    else:
        method = origin.detected_origin_method or "scancode"
    
    # Extract metadata
    metadata = {}
    if origin.detected_origin_metadata:
        metadata.update(origin.detected_origin_metadata)
    if origin.propagation_metadata and origin.is_propagated:
        metadata["propagation"] = origin.propagation_metadata
    
    return OriginData(
        origin_type=origin_type,
        origin_identifier=origin_identifier,
        confidence=confidence,
        detection_method=method,
        metadata=metadata,
    )


def origin_determination_to_file_curation(
    origin: CodeOriginDetermination,
    include_provenance: bool = True,
) -> FileCuration:
    """
    Convert a CodeOriginDetermination to a FileCuration schema object.
    """
    resource = origin.codebase_resource
    
    # Build detected origin
    detected_origin = None
    if origin.detected_origin_type:
        detected_origin = OriginData(
            origin_type=origin.detected_origin_type,
            origin_identifier=origin.detected_origin_identifier or "",
            confidence=origin.detected_origin_confidence or 0.5,
            detection_method=origin.detected_origin_method or "scancode",
            metadata=origin.detected_origin_metadata or {},
        )
    
    # Build amended origin
    amended_origin = None
    if origin.amended_origin_type:
        amended_origin = OriginData(
            origin_type=origin.amended_origin_type,
            origin_identifier=origin.amended_origin_identifier or "",
            confidence=1.0 if origin.is_verified else 0.9,
            detection_method="manual_amendment",
            metadata={},
        )
    
    # Build provenance chain
    provenance = []
    if include_provenance:
        for prov in origin.provenance_records.all().order_by("action_date"):
            provenance.append(
                ProvenanceRecord(
                    action_type=prov.action_type,
                    actor_name=prov.actor_name or "System",
                    actor_email=prov.actor_email or "",
                    action_date=prov.action_date.isoformat(),
                    source_instance_url=prov.curation_source.url if prov.curation_source else None,
                    source_name=prov.curation_source.name if prov.curation_source else None,
                    previous_value=prov.previous_value,
                    new_value=prov.new_value,
                    notes=prov.notes or "",
                    metadata=prov.metadata,
                )
            )
    
    # Build file curation
    return FileCuration(
        file_path=resource.path,
        file_sha256=resource.sha256 or None,
        file_size=resource.size or None,
        detected_origin=detected_origin,
        amended_origin=amended_origin,
        is_verified=origin.is_verified,
        is_propagated=origin.is_propagated,
        propagation_method=origin.propagation_method,
        propagation_source_path=(
            origin.propagation_source.codebase_resource.path
            if origin.propagation_source
            else None
        ),
        provenance=provenance,
        notes=origin.amended_origin_notes or "",
    )


def export_curations_for_project(
    project: Project,
    verified_only: bool = True,
    include_propagated: bool = False,
    include_provenance: bool = True,
    curator_name: str = "",
    curator_email: str = "",
) -> CurationPackage:
    """
    Export all curations for a project as a CurationPackage.
    
    Args:
        project: The project to export curations for
        verified_only: Only include verified curations
        include_propagated: Include propagated origins
        include_provenance: Include full provenance chain
        curator_name: Name of the curator
        curator_email: Email of the curator
    
    Returns:
        CurationPackage ready for serialization
    """
    logger.info(f"Exporting curations for project: {project.name}")
    
    # Build query for origin determinations
    origins_qs = CodeOriginDetermination.objects.filter(
        codebase_resource__project=project
    ).select_related("codebase_resource", "propagation_source")
    
    if include_provenance:
        origins_qs = origins_qs.prefetch_related("provenance_records__curation_source")
    
    if verified_only:
        origins_qs = origins_qs.filter(is_verified=True)
    
    if not include_propagated:
        origins_qs = origins_qs.filter(is_propagated=False)
    
    # Get package info from project
    package_purl = str(project.purl) if project.purl else f"pkg:generic/{project.name}"
    package_name = project.name
    package_version = None
    package_namespace = None
    
    if project.purl:
        package_version = project.purl.version
        package_namespace = project.purl.namespace
    
    # Create curation package
    curation_package = CurationPackage(
        package_purl=package_purl,
        package_name=package_name,
        package_version=package_version,
        package_namespace=package_namespace,
        source_instance_name=getattr(settings, "SCANCODEIO_INSTANCE_NAME", "ScanCode.io"),
        source_instance_url=getattr(settings, "SCANCODEIO_BASE_URL", ""),
        source_project_name=project.name,
        source_project_uuid=str(project.uuid),
        curator_name=curator_name,
        curator_email=curator_email,
        description=f"Origin curations for {project.name}",
    )
    
    # Add file curations
    for origin in origins_qs:
        file_curation = origin_determination_to_file_curation(origin, include_provenance)
        curation_package.add_file_curation(file_curation)
    
    logger.info(
        f"Exported {len(curation_package.file_curations)} curations "
        f"({curation_package.verified_files} verified, "
        f"{curation_package.propagated_files} propagated)"
    )
    
    return curation_package


def export_curations_to_file(
    project: Project,
    output_path: Path,
    format: str = "json",
    **export_options,
) -> Tuple[bool, str]:
    """
    Export curations to a file.
    
    Args:
        project: The project to export curations for
        output_path: Path where the export file will be written
        format: Export format ('json' or 'yaml')
        **export_options: Additional options passed to export_curations_for_project
    
    Returns:
        tuple: (success, message or error)
    """
    try:
        curation_package = export_curations_for_project(project, **export_options)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            output_path.write_text(curation_package.to_json(indent=2), encoding="utf-8")
        elif format == "yaml":
            import saneyaml
            output_path.write_text(
                saneyaml.dump(curation_package.to_dict()),
                encoding="utf-8"
            )
        else:
            return False, f"Unsupported format: {format}"
        
        logger.info(f"Exported curations to: {output_path}")
        return True, str(output_path)
        
    except Exception as e:
        error_msg = f"Error exporting curations: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def export_curations_to_federatedcode(
    project: Project,
    curator_name: str = "",
    curator_email: str = "",
    verified_only: bool = True,
    include_propagated: bool = False,
) -> Tuple[bool, str]:
    """
    Export curations to FederatedCode Git repository.
    
    This function:
    1. Checks FederatedCode eligibility
    2. Exports curations as JSON
    3. Clones/creates the target repository
    4. Commits and pushes the curations
    5. Records the export in CurationExport model
    
    Args:
        project: The project to export curations for
        curator_name: Name of the curator
        curator_email: Email of the curator
        verified_only: Only export verified curations
        include_propagated: Include propagated origins
    
    Returns:
        tuple: (success, message or error)
    """
    logger.info(f"Exporting curations to FederatedCode for project: {project.name}")
    
    # Create export record
    export_record = CurationExport.objects.create(
        project=project,
        verified_only=verified_only,
        include_propagated=include_propagated,
        status="in_progress",
        created_by=curator_name or "System",
    )
    
    try:
        # Check FederatedCode configuration
        if not federatedcode.is_configured():
            raise Exception("FederatedCode is not configured")
        
        # Check project eligibility
        eligibility_errors = federatedcode.check_federatedcode_eligibility(project)
        if eligibility_errors:
            raise Exception(f"Project not eligible: {'; '.join(eligibility_errors)}")
        
        # Export curations
        curation_package = export_curations_for_project(
            project,
            verified_only=verified_only,
            include_propagated=include_propagated,
            include_provenance=True,
            curator_name=curator_name,
            curator_email=curator_email,
        )
        
        if not curation_package.file_curations:
            raise Exception("No curations to export")
        
        # Create working directory
        temp_dir = project.project_work_directory / "federatedcode_curations"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Get repository info
        repo_name, git_url, scan_path = federatedcode.get_package_repository(project.purl)
        
        # Clone or create repository
        local_repo_path = temp_dir / repo_name
        try:
            repo = federatedcode.clone_repository(git_url, local_repo_path)
        except Exception as clone_error:
            logger.info(f"Repository doesn't exist, creating: {clone_error}")
            repo = federatedcode.get_or_create_repository(
                project.purl,
                local_repo_path,
                create_remote=True,
            )
        
        # Write curations file
        curations_dir = local_repo_path / scan_path / "curations"
        curations_dir.mkdir(parents=True, exist_ok=True)
        
        curations_file = curations_dir / "origins.json"
        curations_file.write_text(curation_package.to_json(indent=2), encoding="utf-8")
        
        # Commit and push
        commit_message = (
            f"Add origin curations for {project.name}\n\n"
            f"Exported {len(curation_package.file_curations)} curations "
            f"({curation_package.verified_files} verified) "
            f"from ScanCode.io project {project.uuid}"
        )
        
        commit_sha = federatedcode.commit_and_push_changes(
            repo=repo,
            message=commit_message,
            author_name=curator_name or getattr(settings, "FEDERATEDCODE_GIT_SERVICE_NAME", ""),
            author_email=curator_email or getattr(settings, "FEDERATEDCODE_GIT_SERVICE_EMAIL", ""),
        )
        
        # Update export record
        export_record.mark_completed(
            origin_count=len(curation_package.file_curations),
            file_path=str(curations_file),
            commit_sha=commit_sha,
        )
        
        success_msg = (
            f"Successfully exported {len(curation_package.file_curations)} curations "
            f"to FederatedCode (commit: {commit_sha[:8]})"
        )
        logger.info(success_msg)
        
        # Cleanup
        federatedcode.delete_local_clone(local_repo_path)
        
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Error exporting to FederatedCode: {str(e)}"
        logger.error(error_msg, exc_info=True)
        export_record.mark_failed(error_msg)
        return False, error_msg


def import_curation_package(
    curation_package: CurationPackage,
    project: Project,
    curation_source: Optional[CurationSource] = None,
    conflict_strategy: str = "manual_review",
    dry_run: bool = False,
) -> Dict[str, any]:
    """
    Import a curation package into a project.
    
    This function:
    1. Validates the curation package
    2. Matches file curations to codebase resources
    3. Detects conflicts with existing curations
    4. Applies conflict resolution strategy
    5. Creates/updates origin determinations
    6. Records provenance
    
    Args:
        curation_package: The curation package to import
        project: The project to import into
        curation_source: The source of these curations
        conflict_strategy: How to resolve conflicts
            - "manual_review": Create conflict records for manual resolution
            - "keep_existing": Keep existing curations, skip imports
            - "use_imported": Replace existing with imported
            - "highest_confidence": Use curation with higher confidence
            - "highest_priority": Use source with higher priority
        dry_run: If True, don't actually create/update records
    
    Returns:
        dict: Statistics about the import (imported, skipped, conflicts)
    """
    logger.info(
        f"Importing {len(curation_package.file_curations)} curations "
        f"into project: {project.name}"
    )
    
    stats = {
        "total": len(curation_package.file_curations),
        "imported": 0,
        "updated": 0,
        "skipped": 0,
        "conflicts": 0,
        "errors": 0,
        "error_details": [],
    }
    
    if not curation_source:
        curation_source = get_local_curation_source()
    
    with transaction.atomic():
        for file_curation in curation_package.file_curations:
            try:
                result = _import_single_file_curation(
                    file_curation,
                    project,
                    curation_source,
                    curation_package,
                    conflict_strategy,
                    dry_run,
                )
                stats[result] += 1
                
            except Exception as e:
                stats["errors"] += 1
                error_detail = f"{file_curation.file_path}: {str(e)}"
                stats["error_details"].append(error_detail)
                logger.error(f"Error importing file curation: {error_detail}")
        
        if dry_run:
            logger.info("Dry run - rolling back transaction")
            transaction.set_rollback(True)
    
    logger.info(
        f"Import complete: {stats['imported']} imported, "
        f"{stats['updated']} updated, {stats['skipped']} skipped, "
        f"{stats['conflicts']} conflicts, {stats['errors']} errors"
    )
    
    return stats


def _import_single_file_curation(
    file_curation: FileCuration,
    project: Project,
    curation_source: CurationSource,
    curation_package: CurationPackage,
    conflict_strategy: str,
    dry_run: bool,
) -> str:
    """
    Import a single file curation.
    
    Returns:
        str: Result status ("imported", "updated", "skipped", "conflicts")
    """
    # Find matching resource
    try:
        resource = CodebaseResource.objects.get(
            project=project,
            path=file_curation.file_path,
        )
    except CodebaseResource.DoesNotExist:
        logger.warning(f"Resource not found: {file_curation.file_path}")
        return "skipped"
    
    # Get effective origin from file curation
    imported_origin = file_curation.effective_origin
    if not imported_origin:
        logger.warning(f"No origin data in curation for: {file_curation.file_path}")
        return "skipped"
    
    # Check for existing origin determination
    existing_origin = None
    try:
        existing_origin = CodeOriginDetermination.objects.get(codebase_resource=resource)
    except CodeOriginDetermination.DoesNotExist:
        pass
    
    # No conflict - create new origin
    if not existing_origin:
        if not dry_run:
            _create_origin_from_imported (
                resource,
                imported_origin,
                file_curation,
                curation_source,
                curation_package,
            )
        return "imported"
    
    # Conflict exists - apply resolution strategy
    return _resolve_curation_conflict(
        existing_origin,
        imported_origin,
        file_curation,
        curation_source,
        curation_package,
        conflict_strategy,
        dry_run,
    )


def _create_origin_from_imported(
    resource: CodebaseResource,
    origin_data: OriginData,
    file_curation: FileCuration,
    curation_source: CurationSource,
    curation_package: CurationPackage,
):
    """Create a new CodeOriginDetermination from imported curation."""
    # Determine if this is amended or detected
    is_amended = file_curation.amended_origin is not None
    
    if is_amended:
        origin = CodeOriginDetermination.objects.create(
            codebase_resource=resource,
            amended_origin_type=origin_data.origin_type,
            amended_origin_identifier=origin_data.origin_identifier,
            amended_origin_notes=file_curation.notes or f"Imported from {curation_source.name}",
            amended_by=curation_package.curator_name or "Imported",
            is_verified=file_curation.is_verified,
            is_propagated=file_curation.is_propagated,
        )
    else:
        origin = CodeOriginDetermination.objects.create(
            codebase_resource=resource,
            detected_origin_type=origin_data.origin_type,
            detected_origin_identifier=origin_data.origin_identifier,
            detected_origin_confidence=origin_data.confidence,
            detected_origin_method=origin_data.detection_method,
            detected_origin_metadata=origin_data.metadata,
            is_verified=file_curation.is_verified,
            is_propagated=file_curation.is_propagated,
        )
    
    # Create provenance record
    CurationProvenance.objects.create(
        origin_determination=origin,
        action_type="imported",
        curation_source=curation_source,
        actor_name=curation_package.curator_name or "System",
        actor_email=curation_package.curator_email or "",
        action_date=timezone.now(),
        new_value={
            "origin_type": origin_data.origin_type,
            "origin_identifier": origin_data.origin_identifier,
            "confidence": origin_data.confidence,
        },
        notes=f"Imported from {curation_source.name}",
        metadata={
            "source_package": curation_package.package_purl,
            "source_instance": curation_package.source_instance_url,
        },
    )
    
    logger.debug(f"Created origin from import: {resource.path}")


def _resolve_curation_conflict(
    existing_origin: CodeOriginDetermination,
    imported_origin_data: OriginData,
    file_curation: FileCuration,
    curation_source: CurationSource,
    curation_package: CurationPackage,
    conflict_strategy: str,
    dry_run: bool,
) -> str:
    """
    Resolve a conflict between existing and imported curations.
    
    Returns:
        str: Result status ("updated", "skipped", "conflicts")
    """
    # Check if origins actually differ
    existing_type = existing_origin.effective_origin_type
    existing_id = existing_origin.effective_origin_identifier
    
    if (existing_type == imported_origin_data.origin_type and
        existing_id == imported_origin_data.origin_identifier):
        # No conflict - same origin
        return "skipped"
    
    # Determine conflict type
    if existing_type != imported_origin_data.origin_type:
        conflict_type = "origin_type_mismatch"
    elif existing_id != imported_origin_data.origin_identifier:
        conflict_type = "origin_identifier_mismatch"
    else:
        conflict_type = "multiple_sources"
    
    # Apply resolution strategy
    if conflict_strategy == "manual_review":
        if not dry_run:
            _create_conflict_record(
                existing_origin,
                imported_origin_data,
                file_curation,
                curation_source,
                curation_package,
                conflict_type,
            )
        return "conflicts"
    
    elif conflict_strategy == "keep_existing":
        return "skipped"
    
    elif conflict_strategy == "use_imported":
        if not dry_run:
            _update_origin_with_imported(
                existing_origin,
                imported_origin_data,
                file_curation,
                curation_source,
                curation_package,
                strategy="use_imported",
            )
        return "updated"
    
    elif conflict_strategy == "highest_confidence":
        existing_conf = (
            1.0 if existing_origin.is_verified
            else existing_origin.detected_origin_confidence or 0.5
        )
        imported_conf = imported_origin_data.confidence
        
        if imported_conf > existing_conf:
            if not dry_run:
                _update_origin_with_imported(
                    existing_origin,
                    imported_origin_data,
                    file_curation,
                    curation_source,
                    curation_package,
                    strategy="highest_confidence",
                )
            return "updated"
        else:
            return "skipped"
    
    elif conflict_strategy == "highest_priority":
        # Compare source priorities
        local_source = get_local_curation_source()
        if curation_source.priority > local_source.priority:
            if not dry_run:
                _update_origin_with_imported(
                    existing_origin,
                    imported_origin_data,
                    file_curation,
                    curation_source,
                    curation_package,
                    strategy="highest_priority",
                )
            return "updated"
        else:
            return "skipped"
    
    else:
        logger.warning(f"Unknown conflict strategy: {conflict_strategy}")
        return "skipped"


def _create_conflict_record(
    existing_origin: CodeOriginDetermination,
    imported_origin_data: OriginData,
    file_curation: FileCuration,
    curation_source: CurationSource,
    curation_package: CurationPackage,
    conflict_type: str,
):
    """Create a conflict record for manual resolution."""
    CurationConflict.objects.create(
        project=existing_origin.codebase_resource.project,
        resource_path=file_curation.file_path,
        conflict_type=conflict_type,
        existing_origin=existing_origin,
        imported_origin_data={
            "origin_type": imported_origin_data.origin_type,
            "origin_identifier": imported_origin_data.origin_identifier,
            "confidence": imported_origin_data.confidence,
            "detection_method": imported_origin_data.detection_method,
            "is_verified": file_curation.is_verified,
            "metadata": imported_origin_data.metadata,
        },
        imported_source=curation_source,
        resolution_status="pending",
        metadata={
            "source_package": curation_package.package_purl,
            "curator": curation_package.curator_name,
        },
    )
    logger.info(f"Created conflict record for: {file_curation.file_path}")


def _update_origin_with_imported(
    existing_origin: CodeOriginDetermination,
    imported_origin_data: OriginData,
    file_curation: FileCuration,
    curation_source: CurationSource,
    curation_package: CurationPackage,
    strategy: str,
):
    """Update an existing origin with imported data."""
    # Save previous values
    previous_value = {
        "origin_type": existing_origin.effective_origin_type,
        "origin_identifier": existing_origin.effective_origin_identifier,
    }
    
    # Update as amendment
    existing_origin.amended_origin_type = imported_origin_data.origin_type
    existing_origin.amended_origin_identifier = imported_origin_data.origin_identifier
    existing_origin.amended_origin_notes = (
        f"Updated from import ({strategy}). " + (file_curation.notes or "")
    )
    existing_origin.amended_by = curation_package.curator_name or "Imported"
    existing_origin.is_verified = file_curation.is_verified
    existing_origin.save()
    
    # Create provenance record
    CurationProvenance.objects.create(
        origin_determination=existing_origin,
        action_type="merged",
        curation_source=curation_source,
        actor_name="System",
        action_date=timezone.now(),
        previous_value=previous_value,
        new_value={
            "origin_type": imported_origin_data.origin_type,
            "origin_identifier": imported_origin_data.origin_identifier,
        },
        notes=f"Merged using strategy: {strategy}",
        metadata={
            "strategy": strategy,
            "source_package": curation_package.package_purl,
        },
    )
    
    logger.debug(f"Updated origin from import: {file_curation.file_path}")


def import_curations_from_url(
    project: Project,
    source_url: str,
    source_name: str = "",
    conflict_strategy: str = "manual_review",
    dry_run: bool = False,
) -> Tuple[bool, Dict[str, any]]:
    """
    Import curations from a URL (Git repository or direct file).
    
    Args:
        project: The project to import into
        source_url: URL to the curation source (Git repo or file)
        source_name: Name for the curation source
        conflict_strategy: How to resolve conflicts
        dry_run: If True, don't actually create/update records
    
    Returns:
        tuple: (success, statistics_dict)
    """
    logger.info(f"Importing curations from: {source_url}")
    
    try:
        # Get or create curation source
        curation_source, _ = CurationSource.objects.get_or_create(
            url=source_url,
            defaults={
                "name": source_name or source_url,
                "source_type": "federatedcode_git" if ".git" in source_url else "manual_import",
                "priority": 50,
            },
        )
        
        # Download/fetch curations
        if source_url.endswith(".git") or "github.com" in source_url:
            curation_data = _fetch_curations_from_git(source_url)
        else:
            curation_data = _fetch_curations_from_file(source_url)
        
        # Parse curation package
        curation_package = CurationPackage.from_dict(curation_data)
        
        # Validate
        is_valid, errors = validate_curation_package(curation_data)
        if not is_valid:
            return False, {"error": "Validation failed", "errors": errors}
        
        # Import
        stats = import_curation_package(
            curation_package,
            project,
            curation_source,
            conflict_strategy,
            dry_run,
        )
        
        # Update source sync info
        if not dry_run:
            curation_source.mark_synced(stats)
        
        return True, stats
        
    except Exception as e:
        error_msg = f"Error importing curations: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, {"error": error_msg}


def _fetch_curations_from_git(git_url: str) -> Dict[str, Any]:
    """Fetch curations from a Git repository."""
    import tempfile
    import git
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Clone repository
        repo = git.Repo.clone_from(git_url, temp_path)
        
        # Find curations file
        curations_file = None
        for pattern in ["**/curations/origins.json", "**/curations.json", "**/origins.json"]:
            matches = list(temp_path.glob(pattern))
            if matches:
                curations_file = matches[0]
                break
        
        if not curations_file:
            raise Exception("No curations file found in repository")
        
        # Load and return
        return json.loads(curations_file.read_text(encoding="utf-8"))


def _fetch_curations_from_file(file_url: str) -> Dict[str, Any]:
    """Fetch curations from a file URL."""
    import requests
    
    response = requests.get(file_url, timeout=30)
    response.raise_for_status()
    
    if file_url.endswith(".json"):
        return response.json()
    elif file_url.endswith((".yaml", ".yml")):
        import saneyaml
        return saneyaml.load(response.text)
    else:
        # Try JSON first, then YAML
        try:
            return response.json()
        except:
            import saneyaml
            return saneyaml.load(response.text)

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
Curation schema definitions for FederatedCode integration.

This module defines the standardized schema for sharing origin curations
across ScanCode.io instances and with the broader open-source community.

The schema supports:
- File-level and package-level curations
- Full provenance tracking
- Conflict resolution metadata
- Verification and confidence scores
- License and copyright information
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
import json


CURATION_SCHEMA_VERSION = "1.0.0"


@dataclass
class OriginData:
    """
    Represents origin information for a file or package.
    
    This is the core data structure that captures where code comes from.
    """
    origin_type: str  # package, repository, url, file, unknown
    origin_identifier: str  # PURL, URL, path, etc.
    confidence: float  # 0.0 to 1.0
    detection_method: str  # scancode, manual, hash_match, etc.
    
    # Optional origin metadata
    version: Optional[str] = None
    namespace: Optional[str] = None
    qualifiers: Optional[Dict[str, str]] = None
    subpath: Optional[str] = None
    
    # License and copyright info
    declared_license: Optional[str] = None
    detected_licenses: List[str] = field(default_factory=list)
    copyright_holder: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OriginData":
        """Create OriginData from dictionary."""
        # Handle optional fields
        return cls(
            origin_type=data["origin_type"],
            origin_identifier=data["origin_identifier"],
            confidence=data["confidence"],
            detection_method=data["detection_method"],
            version=data.get("version"),
            namespace=data.get("namespace"),
            qualifiers=data.get("qualifiers"),
            subpath=data.get("subpath"),
            declared_license=data.get("declared_license"),
            detected_licenses=data.get("detected_licenses", []),
            copyright_holder=data.get("copyright_holder"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProvenanceRecord:
    """
    Tracks the provenance (history) of a curation.
    
    Records who created/modified the curation, when, and why.
    """
    action_type: str  # created, amended, verified, imported, merged
    actor_name: str
    action_date: str  # ISO 8601 format
    
    actor_email: Optional[str] = None
    source_instance_url: Optional[str] = None
    source_name: Optional[str] = None
    previous_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    tool_name: Optional[str] = None
    tool_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceRecord":
        """Create ProvenanceRecord from dictionary."""
        return cls(
            action_type=data["action_type"],
            actor_name=data["actor_name"],
            action_date=data["action_date"],
            actor_email=data.get("actor_email"),
            source_instance_url=data.get("source_instance_url"),
            source_name=data.get("source_name"),
            previous_value=data.get("previous_value"),
            new_value=data.get("new_value"),
            notes=data.get("notes"),
            tool_name=data.get("tool_name"),
            tool_version=data.get("tool_version"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FileCuration:
    """
    Represents a curation for a specific file.
    
    This is the atomic unit of curation that can be shared.
    """
    file_path: str
    file_sha256: Optional[str] = None
    file_size: Optional[int] = None
    
    # Origin information
    detected_origin: Optional[OriginData] = None
    amended_origin: Optional[OriginData] = None
    
    # Verification status
    is_verified: bool = False
    is_propagated: bool = False
    propagation_method: Optional[str] = None
    propagation_source_path: Optional[str] = None
    
    # Provenance chain
    provenance: List[ProvenanceRecord] = field(default_factory=list)
    
    # Additional metadata
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def effective_origin(self) -> Optional[OriginData]:
        """Get the effective origin (amended takes precedence over detected)."""
        return self.amended_origin or self.detected_origin
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with nested objects."""
        data = {
            "file_path": self.file_path,
            "is_verified": self.is_verified,
            "is_propagated": self.is_propagated,
        }
        
        if self.file_sha256:
            data["file_sha256"] = self.file_sha256
        if self.file_size:
            data["file_size"] = self.file_size
        
        if self.detected_origin:
            data["detected_origin"] = self.detected_origin.to_dict()
        if self.amended_origin:
            data["amended_origin"] = self.amended_origin.to_dict()
        
        if self.propagation_method:
            data["propagation_method"] = self.propagation_method
        if self.propagation_source_path:
            data["propagation_source_path"] = self.propagation_source_path
        
        if self.provenance:
            data["provenance"] = [p.to_dict() for p in self.provenance]
        
        if self.notes:
            data["notes"] = self.notes
        if self.tags:
            data["tags"] = self.tags
        if self.metadata:
            data["metadata"] = self.metadata
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileCuration":
        """Create FileCuration from dictionary."""
        detected_origin = None
        if "detected_origin" in data:
            detected_origin = OriginData.from_dict(data["detected_origin"])
        
        amended_origin = None
        if "amended_origin" in data:
            amended_origin = OriginData.from_dict(data["amended_origin"])
        
        provenance = []
        if "provenance" in data:
            provenance = [ProvenanceRecord.from_dict(p) for p in data["provenance"]]
        
        return cls(
            file_path=data["file_path"],
            file_sha256=data.get("file_sha256"),
            file_size=data.get("file_size"),
            detected_origin=detected_origin,
            amended_origin=amended_origin,
            is_verified=data.get("is_verified", False),
            is_propagated=data.get("is_propagated", False),
            propagation_method=data.get("propagation_method"),
            propagation_source_path=data.get("propagation_source_path"),
            provenance=provenance,
            notes=data.get("notes"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CurationPackage:
    """
    A package of curations that can be shared via FederatedCode.
    
    This is the top-level container for sharing curations, typically
    corresponding to a single software package or project.
    """
    # Package identification
    package_purl: str  # Package URL
    package_name: str
    package_version: Optional[str] = None
    package_namespace: Optional[str] = None
    
    # Curation metadata
    schema_version: str = CURATION_SCHEMA_VERSION
    created_date: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_date: Optional[str] = None
    
    # Source information
    source_instance_name: Optional[str] = None
    source_instance_url: Optional[str] = None
    source_project_name: Optional[str] = None
    source_project_uuid: Optional[str] = None
    
    # Curator information
    curator_name: Optional[str] = None
    curator_email: Optional[str] = None
    curator_organization: Optional[str] = None
    
    # Curations
    file_curations: List[FileCuration] = field(default_factory=list)
    
    # Package-level origin (if all files share same origin)
    package_origin: Optional[OriginData] = None
    
    # Statistics
    total_files: int = 0
    verified_files: int = 0
    propagated_files: int = 0
    
    # License and legal info
    curation_license: str = "CC0-1.0"  # Default: Public Domain
    notice: Optional[str] = None
    
    # Additional metadata
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_file_curation(self, curation: FileCuration):
        """Add a file curation and update statistics."""
        self.file_curations.append(curation)
        self.total_files = len(self.file_curations)
        self.verified_files = sum(1 for fc in self.file_curations if fc.is_verified)
        self.propagated_files = sum(1 for fc in self.file_curations if fc.is_propagated)
        self.updated_date = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "schema_version": self.schema_version,
            "package": {
                "purl": self.package_purl,
                "name": self.package_name,
                "version": self.package_version,
                "namespace": self.package_namespace,
            },
            "curation_metadata": {
                "created_date": self.created_date,
                "updated_date": self.updated_date,
                "total_files": self.total_files,
                "verified_files": self.verified_files,
                "propagated_files": self.propagated_files,
                "curation_license": self.curation_license,
            },
            "source": {
                "instance_name": self.source_instance_name,
                "instance_url": self.source_instance_url,
                "project_name": self.source_project_name,
                "project_uuid": self.source_project_uuid,
            },
            "curator": {
                "name": self.curator_name,
                "email": self.curator_email,
                "organization": self.curator_organization,
            },
            "package_origin": self.package_origin.to_dict() if self.package_origin else None,
            "file_curations": [fc.to_dict() for fc in self.file_curations],
            "description": self.description,
            "keywords": self.keywords,
            "notice": self.notice,
            "metadata": self.metadata,
        }
    
    def to_json(self, indent=2) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurationPackage":
        """Create CurationPackage from dictionary."""
        package_info = data.get("package", {})
        metadata = data.get("curation_metadata", {})
        source = data.get("source", {})
        curator = data.get("curator", {})
        
        package_origin = None
        if data.get("package_origin"):
            package_origin = OriginData.from_dict(data["package_origin"])
        
        file_curations = []
        if "file_curations" in data:
            file_curations = [FileCuration.from_dict(fc) for fc in data["file_curations"]]
        
        return cls(
            schema_version=data.get("schema_version", CURATION_SCHEMA_VERSION),
            package_purl=package_info["purl"],
            package_name=package_info["name"],
            package_version=package_info.get("version"),
            package_namespace=package_info.get("namespace"),
            created_date=metadata.get("created_date", datetime.utcnow().isoformat()),
            updated_date=metadata.get("updated_date"),
            source_instance_name=source.get("instance_name"),
            source_instance_url=source.get("instance_url"),
            source_project_name=source.get("project_name"),
            source_project_uuid=source.get("project_uuid"),
            curator_name=curator.get("name"),
            curator_email=curator.get("email"),
            curator_organization=curator.get("organization"),
            package_origin=package_origin,
            file_curations=file_curations,
            total_files=metadata.get("total_files", len(file_curations)),
            verified_files=metadata.get("verified_files", 0),
            propagated_files=metadata.get("propagated_files", 0),
            curation_license=metadata.get("curation_license", "CC0-1.0"),
            description=data.get("description"),
            keywords=data.get("keywords", []),
            notice=data.get("notice"),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "CurationPackage":
        """Import from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


def validate_curation_package(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a curation package against the schema.
    
    Returns:
        tuple: (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required top-level fields
    if "schema_version" not in data:
        errors.append("Missing required field: schema_version")
    
    if "package" not in data:
        errors.append("Missing required field: package")
    else:
        package = data["package"]
        if "purl" not in package:
            errors.append("Missing required field: package.purl")
        if "name" not in package:
            errors.append("Missing required field: package.name")
    
    # Check file curations
    if "file_curations" in data:
        for i, fc in enumerate(data["file_curations"]):
            if "file_path" not in fc:
                errors.append(f"File curation {i}: missing required field 'file_path'")
            
            # Validate origin data if present
            for origin_key in ["detected_origin", "amended_origin"]:
                if origin_key in fc:
                    origin = fc[origin_key]
                    required_origin_fields = [
                        "origin_type",
                        "origin_identifier",
                        "confidence",
                        "detection_method"
                    ]
                    for field in required_origin_fields:
                        if field not in origin:
                            errors.append(
                                f"File curation {i}, {origin_key}: "
                                f"missing required field '{field}'"
                            )
                    
                    # Validate confidence range
                    if "confidence" in origin:
                        conf = origin["confidence"]
                        if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
                            errors.append(
                                f"File curation {i}, {origin_key}: "
                                f"confidence must be between 0 and 1"
                            )
    
    return (len(errors) == 0, errors)

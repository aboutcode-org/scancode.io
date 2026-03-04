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
Models for FederatedCode curation sharing and integration.

This module provides models for:
- Tracking external curation sources
- Recording curation provenance (who, when, from where)
- Managing curation conflicts and merge resolutions
- Supporting open digital commons curation sharing
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from scanpipe.models import UUIDPKModel, CodeOriginDetermination, Project


class CurationSource(UUIDPKModel, models.Model):
    """
    Represents an external source of curations (e.g., another ScanCode.io instance,
    a FederatedCode repository, a community curation service).
    
    This model tracks where curations come from to maintain provenance and
    enable periodic synchronization.
    """
    
    SOURCE_TYPE_CHOICES = [
        ("federatedcode_git", "FederatedCode Git Repository"),
        ("scancodeio_api", "ScanCode.io API"),
        ("community_service", "Community Curation Service"),
        ("manual_import", "Manual Import"),
        ("local", "Local (This Instance)"),
    ]
    
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Human-readable name for this curation source"),
    )
    
    source_type = models.CharField(
        max_length=50,
        choices=SOURCE_TYPE_CHOICES,
        help_text=_("Type of curation source"),
    )
    
    url = models.URLField(
        max_length=1024,
        blank=True,
        help_text=_("URL to the curation source (Git repo, API endpoint, etc.)"),
    )
    
    api_key = models.CharField(
        max_length=512,
        blank=True,
        help_text=_("API key or authentication token for accessing this source"),
    )
    
    priority = models.IntegerField(
        default=50,
        help_text=_(
            "Priority for conflict resolution (higher = preferred). "
            "Range: 0-100. Local/manual sources typically have higher priority."
        ),
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this source is currently active for imports"),
    )
    
    auto_sync = models.BooleanField(
        default=False,
        help_text=_("Automatically sync curations from this source periodically"),
    )
    
    sync_frequency_hours = models.IntegerField(
        default=24,
        help_text=_("How often to sync curations (in hours) if auto_sync is enabled"),
    )
    
    last_sync_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Last time curations were synced from this source"),
    )
    
    sync_statistics = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Statistics from the last sync (imported, conflicts, errors)"),
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional metadata about this source (maintainer, license, etc.)"),
    )
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Curation Source")
        verbose_name_plural = _("Curation Sources")
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["source_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["priority"]),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"
    
    @property
    def needs_sync(self):
        """Return True if this source needs synchronization."""
        if not self.is_active or not self.auto_sync:
            return False
        
        if not self.last_sync_date:
            return True
        
        hours_since_sync = (timezone.now() - self.last_sync_date).total_seconds()  / 3600
        return hours_since_sync >= self.sync_frequency_hours
    
    def mark_synced(self, statistics=None):
        """Mark this source as synced with optional statistics."""
        self.last_sync_date = timezone.now()
        if statistics:
            self.sync_statistics = statistics
        self.save(update_fields=["last_sync_date", "sync_statistics", "updated_date"])


class CurationProvenance(UUIDPKModel, models.Model):
    """
    Tracks the provenance (origin and history) of a curation.
    
    Each curation can have multiple provenance records, representing:
    - Original detection/creation
    - Manual amendments by users
    - Imports from external sources
    - Merge operations
    
    This enables full audit trails and understanding of how curations evolved.
    """
    
    ACTION_TYPE_CHOICES = [
        ("created", "Created"),
        ("amended", "Amended"),
        ("verified", "Verified"),
        ("imported", "Imported"),
        ("merged", "Merged"),
        ("propagated", "Propagated"),
        ("rejected", "Rejected"),
    ]
    
    origin_determination = models.ForeignKey(
        CodeOriginDetermination,
        on_delete=models.CASCADE,
        related_name="provenance_records",
        help_text=_("The origin determination this provenance is for"),
    )
    
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPE_CHOICES,
        help_text=_("Type of action that created this provenance record"),
    )
    
    curation_source = models.ForeignKey(
        CurationSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="curation_provenances",
        help_text=_("The source where this curation came from (if imported)"),
    )
    
    actor_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Name of the person/system that performed the action"),
    )
    
    actor_email = models.EmailField(
        blank=True,
        help_text=_("Email of the person who performed the action"),
    )
    
    action_date = models.DateTimeField(
        default=timezone.now,
        help_text=_("When this action was performed"),
    )
    
    previous_value = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Previous values before this action (for amendments/merges)"),
    )
    
    new_value = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("New values after this action"),
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about this provenance record"),
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional metadata (tool version, confidence, etc.)"),
    )
    
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Curation Provenance")
        verbose_name_plural = _("Curation Provenances")
        ordering = ["-action_date"]
        indexes = [
            models.Index(fields=["origin_determination", "-action_date"]),
            models.Index(fields=["action_type"]),
            models.Index(fields=["curation_source"]),
        ]
    
    def __str__(self):
        return f"{self.get_action_type_display()} at {self.action_date} by {self.actor_name or 'System'}"


class CurationConflict(UUIDPKModel, models.Model):
    """
    Tracks conflicts when multiple curations exist for the same file/package.
    
    Conflicts arise when:
    - Importing curations that differ from existing ones
    - Multiple sources provide different curations for the same resource
    - Manual amendments conflict with automated detections
    
    This model helps manage conflict resolution strategies.
    """
    
    CONFLICT_TYPE_CHOICES = [
        ("origin_type_mismatch", "Origin Type Mismatch"),
        ("origin_identifier_mismatch", "Origin Identifier Mismatch"),
        ("confidence_difference", "Significant Confidence Difference"),
        ("multiple_sources", "Multiple Source Conflict"),
        ("manual_vs_automated", "Manual vs Automated Conflict"),
    ]
    
    RESOLUTION_STATUS_CHOICES = [
        ("pending", "Pending Resolution"),
        ("auto_resolved", "Automatically Resolved"),
        ("manual_resolved", "Manually Resolved"),
        ("deferred", "Deferred for Later"),
        ("ignored", "Ignored"),
    ]
    
    RESOLUTION_STRATEGY_CHOICES = [
        ("keep_existing", "Keep Existing"),
        ("use_imported", "Use Imported"),
        ("merge_both", "Merge Both"),
        ("highest_priority", "Highest Priority Source"),
        ("highest_confidence", "Highest Confidence"),
        ("manual_decision", "Manual Decision"),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="curation_conflicts",
        help_text=_("The project this conflict belongs to"),
    )
    
    resource_path = models.CharField(
        max_length=2048,
        help_text=_("Path to the resource with conflicting curations"),
    )
    
    conflict_type = models.CharField(
        max_length=50,
        choices=CONFLICT_TYPE_CHOICES,
        help_text=_("Type of conflict"),
    )
    
    existing_origin = models.ForeignKey(
        CodeOriginDetermination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conflicts_as_existing",
        help_text=_("The existing origin determination"),
    )
    
    imported_origin_data = models.JSONField(
        default=dict,
        help_text=_("The imported/conflicting origin data"),
    )
    
    imported_source = models.ForeignKey(
        CurationSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conflicts",
        help_text=_("The source of the imported curation"),
    )
    
    resolution_status = models.CharField(
        max_length=50,
        choices=RESOLUTION_STATUS_CHOICES,
        default="pending",
        help_text=_("Current status of conflict resolution"),
    )
    
    resolution_strategy = models.CharField(
        max_length=50,
        choices=RESOLUTION_STRATEGY_CHOICES,
        blank=True,
        help_text=_("Strategy used or to be used for resolution"),
    )
    
    resolved_origin = models.ForeignKey(
        CodeOriginDetermination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conflicts_resolved_to",
        help_text=_("The origin determination after conflict resolution"),
    )
    
    resolved_by = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Name of the person/system that resolved the conflict"),
    )
    
    resolved_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the conflict was resolved"),
    )
    
    resolution_notes = models.TextField(
        blank=True,
        help_text=_("Notes about the conflict resolution"),
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional conflict metadata"),
    )
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Curation Conflict")
        verbose_name_plural = _("Curation Conflicts")
        ordering = ["-created_date"]
        indexes = [
            models.Index(fields=["project", "resolution_status"]),
            models.Index(fields=["conflict_type"]),
            models.Index(fields=["resolution_status"]),
        ]
    
    def __str__(self):
        return f"Conflict for {self.resource_path} ({self.get_resolution_status_display()})"
    
    @property
    def is_resolved(self):
        """Return True if conflict has been resolved."""
        return self.resolution_status in ["auto_resolved", "manual_resolved"]
    
    def resolve(self, strategy, resolved_origin=None, resolved_by="System", notes=""):
        """Mark this conflict as resolved."""
        self.resolution_status = "auto_resolved" if resolved_by == "System" else "manual_resolved"
        self.resolution_strategy = strategy
        self.resolved_origin = resolved_origin
        self.resolved_by = resolved_by
        self.resolved_date = timezone.now()
        self.resolution_notes = notes
        self.save()


class CurationExport(UUIDPKModel, models.Model):
    """
    Tracks exports of curations to external FederatedCode sources.
    
    This model records when and what curations were exported, enabling:
    - Audit trails of shared curations
    - Incremental updates (only export new/changed curations)
    - Tracking which curations have been shared with the community
    """
    
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="curation_exports",
        help_text=_("The project whose curations were exported"),
    )
    
    destination_source = models.ForeignKey(
        CurationSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exports",
        help_text=_("The destination source where curations were exported"),
    )
    
    destination_url = models.URLField(
        max_length=1024,
        blank=True,
        help_text=_("URL where the exported curations can be found"),
    )
    
    export_format = models.CharField(
        max_length=50,
        default="json",
        help_text=_("Format of the exported curations (json, yaml, etc.)"),
    )
    
    origin_count = models.IntegerField(
        default=0,
        help_text=_("Number of origin determinations exported"),
    )
    
    verified_only = models.BooleanField(
        default=True,
        help_text=_("Whether only verified curations were exported"),
    )
    
    include_propagated = models.BooleanField(
        default=False,
        help_text=_("Whether propagated origins were included in export"),
    )
    
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="pending",
        help_text=_("Status of the export operation"),
    )
    
    export_file_path = models.CharField(
        max_length=1024,
        blank=True,
        help_text=_("Path to the exported file (if applicable)"),
    )
    
    git_commit_sha = models.CharField(
        max_length=64,
        blank=True,
        help_text=_("Git commit SHA if exported to a Git repository"),
    )
    
    error_message = models.TextField(
        blank=True,
        help_text=_("Error message if export failed"),
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional export metadata"),
    )
    
    created_by = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("User who initiated the export"),
    )
    
    created_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the export completed"),
    )
    
    class Meta:
        verbose_name = _("Curation Export")
        verbose_name_plural = _("Curation Exports")
        ordering = ["-created_date"]
        indexes = [
            models.Index(fields=["project", "-created_date"]),
            models.Index(fields=["status"]),
        ]
    
    def __str__(self):
        return f"Export for {self.project.name} - {self.get_status_display()}"
    
    def mark_completed(self, origin_count, file_path="", commit_sha=""):
        """Mark export as completed."""
        self.status = "completed"
        self.origin_count = origin_count
        self.export_file_path = file_path
        self.git_commit_sha = commit_sha
        self.completed_date = timezone.now()
        self.save()
    
    def mark_failed(self, error_message):
        """Mark export as failed."""
        self.status = "failed"
        self.error_message = error_message
        self.completed_date = timezone.now()
        self.save()

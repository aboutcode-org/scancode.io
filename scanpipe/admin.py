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

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import CodeOriginDetermination
from scanpipe.models_curation import CurationSource
from scanpipe.models_curation import CurationProvenance
from scanpipe.models_curation import CurationConflict
from scanpipe.models_curation import CurationExport


class ScanPipeBaseAdmin(admin.ModelAdmin):
    """Common ModelAdmin attributes."""

    actions_on_top = False
    actions_on_bottom = True
    show_facets = admin.ShowFacets.ALWAYS

    def has_add_permission(self, request):
        return False


class ProjectAdmin(ScanPipeBaseAdmin):
    list_display = [
        "name",
        "label_list",
        "packages_link",
        "dependencies_link",
        "resources_link",
        "is_archived",
    ]
    search_fields = ["uuid", "name"]
    list_filter = ["is_archived", "labels"]
    ordering = ["-created_date"]
    fieldsets = [
        ("", {"fields": ("name", "slug", "notes", "extra_data", "settings", "uuid")}),
        ("Links", {"fields": ("packages_link", "dependencies_link", "resources_link")}),
    ]
    readonly_fields = ["packages_link", "dependencies_link", "resources_link", "uuid"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("labels")
            .with_counts(
                "codebaseresources",
                "discoveredpackages",
                "discovereddependencies",
            )
        )

    @admin.display(description="Labels")
    def label_list(self, obj):
        return ", ".join(label.name for label in obj.labels.all())

    @staticmethod
    def make_filtered_link(obj, value, url_name):
        """Return a link to the provided ``url_name`` filtered by this project."""
        url = reverse(f"admin:scanpipe_{url_name}_changelist")
        return format_html(
            '<a href="{}?project__uuid__exact={}">{}</a>', url, obj.uuid, value
        )

    @admin.display(description="Packages", ordering="discoveredpackages_count")
    def packages_link(self, obj):
        count = obj.discoveredpackages_count
        return self.make_filtered_link(obj, count, "discoveredpackage")

    @admin.display(description="Dependencies", ordering="discovereddependencies_count")
    def dependencies_link(self, obj):
        count = obj.discovereddependencies_count
        return self.make_filtered_link(obj, count, "discovereddependency")

    @admin.display(description="Resources", ordering="codebaseresources_count")
    def resources_link(self, obj):
        count = obj.codebaseresources_count
        return self.make_filtered_link(obj, count, "codebaseresource")


class CodebaseResourceAdmin(ScanPipeBaseAdmin):
    list_display = [
        "path",
        "status",
        "type",
        "name",
        "extension",
        "programming_language",
        "mime_type",
        "tag",
        "detected_license_expression",
        "compliance_alert",
        "project",
    ]
    search_fields = [
        "path",
    ]
    list_filter = ["project", "type", "programming_language", "compliance_alert"]
    ordering = ["project", "path"]


class DiscoveredPackageAdmin(ScanPipeBaseAdmin):
    list_display = [
        "__str__",
        "declared_license_expression",
        "primary_language",
        "project",
    ]
    search_fields = [
        "uuid",
        "package_uid",
        "type",
        "namespace",
        "name",
        "version",
        "filename",
        "declared_license_expression",
        "other_license_expression",
        "tag",
        "keywords",
    ]
    list_filter = ["project", "type", "primary_language", "compliance_alert"]
    exclude = ["codebase_resources"]
    ordering = ["project", "type", "namespace", "name", "version"]


class DiscoveredDependencyAdmin(ScanPipeBaseAdmin):
    list_display = [
        "dependency_uid",
        "type",
        "scope",
        "is_runtime",
        "is_optional",
        "is_pinned",
        "is_direct",
        "project",
    ]
    search_fields = [
        "uuid",
        "dependency_uid",
        "namespace",
        "name",
        "version",
        "datasource_id",
        "extracted_requirement",
    ]
    list_filter = [
        "project",
        "type",
        "scope",
        "is_runtime",
        "is_optional",
        "is_pinned",
        "is_direct",
    ]
    ordering = ["project", "dependency_uid"]


class CodeOriginDeterminationAdmin(ScanPipeBaseAdmin):
    list_display = [
        "codebase_resource_path",
        "effective_origin_type",
        "effective_origin_identifier",
        "is_verified",
        "is_propagated",
        "project",
    ]
    search_fields = [
        "codebase_resource__path",
        "detected_origin_identifier",
        "amended_origin_identifier",
    ]
    list_filter = [
        "codebase_resource__project",
        "detected_origin_type",
        "amended_origin_type",
        "is_verified",
        "is_propagated",
        "propagation_method",
    ]
    ordering = ["codebase_resource__project", "codebase_resource__path"]
    readonly_fields = ["created_date", "updated_date"]

    @admin.display(description="Resource Path")
    def codebase_resource_path(self, obj):
        return obj.codebase_resource.path

    @admin.display(description="Project")
    def project(self, obj):
        return obj.codebase_resource.project


class CurationSourceAdmin(ScanPipeBaseAdmin):
    list_display = [
        "name",
        "source_type",
        "priority",
        "is_active",
        "auto_sync",
        "last_sync_date",
    ]
    search_fields = ["name", "url"]
    list_filter = ["source_type", "is_active", "auto_sync"]
    ordering = ["-priority", "name"]
    fieldsets = [
        ("", {"fields": ("name", "source_type", "url", "api_key")}),
        ("Configuration", {"fields": ("priority", "is_active", "auto_sync", "sync_frequency_hours")}),
        ("Sync Status", {"fields": ("last_sync_date", "sync_statistics")}),
        ("Metadata", {"fields": ("metadata", "created_date", "updated_date")}),
    ]
    readonly_fields = ["created_date", "updated_date"]

    def has_add_permission(self, request):
        """Allow adding new curation sources."""
        return True


class CurationProvenanceAdmin(ScanPipeBaseAdmin):
    list_display = [
        "origin_determination",
        "action_type",
        "actor_name",
        "curation_source",
        "action_date",
    ]
    search_fields = [
        "actor_name",
        "actor_email",
        "notes",
    ]
    list_filter = [
        "action_type",
        "curation_source",
        "action_date",
    ]
    ordering = ["-action_date"]
    readonly_fields = ["created_date"]


class CurationConflictAdmin(ScanPipeBaseAdmin):
    list_display = [
        "resource_path",
        "conflict_type",
        "resolution_status",
        "project",
        "created_date",
    ]
    search_fields = [
        "resource_path",
        "resolved_by",
        "resolution_notes",
    ]
    list_filter = [
        "project",
        "conflict_type",
        "resolution_status",
        "resolution_strategy",
    ]
    ordering = ["-created_date"]
    fieldsets = [
        ("Conflict Details", {
            "fields": ("project", "resource_path", "conflict_type", "imported_origin_data")
        }),
        ("Origins", {
            "fields": ("existing_origin", "imported_source")
        }),
        ("Resolution", {
            "fields": (
                "resolution_status",
                "resolution_strategy",
                "resolved_origin",
                "resolved_by",
                "resolved_date",
                "resolution_notes",
            )
        }),
        ("Metadata", {
            "fields": ("metadata", "created_date", "updated_date"),
            "classes": ("collapse",),
        }),
    ]
    readonly_fields = ["created_date", "updated_date"]
    
    actions = ["resolve_keep_existing", "resolve_use_imported", "resolve_highest_confidence"]
    
    @admin.action(description="Resolve: Keep existing curations")
    def resolve_keep_existing(self, request, queryset):
        count = 0
        for conflict in queryset.filter(resolution_status="pending"):
            if conflict.existing_origin:
                conflict.resolve(
                    strategy="keep_existing",
                    resolved_origin=conflict.existing_origin,
                    resolved_by=request.user.username,
                    notes="Resolved via admin action: keep existing",
                )
                count += 1
        self.message_user(request, f"Resolved {count} conflicts (kept existing)")
    
    @admin.action(description="Resolve: Use imported curations")
    def resolve_use_imported(self, request, queryset):
        from scanpipe.models_curation import CurationProvenance
        from django.utils import timezone
        
        count = 0
        for conflict in queryset.filter(resolution_status="pending"):
            if conflict.existing_origin and conflict.imported_origin_data:
                # Update existing origin with imported data
                imported_data = conflict.imported_origin_data
                conflict.existing_origin.amended_origin_type = imported_data["origin_type"]
                conflict.existing_origin.amended_origin_identifier = imported_data["origin_identifier"]
                conflict.existing_origin.amended_origin_notes = "Resolved via admin action: use imported"
                conflict.existing_origin.amended_by = request.user.username
                conflict.existing_origin.is_verified = imported_data.get("is_verified", False)
                conflict.existing_origin.save()
                
                # Create provenance
                CurationProvenance.objects.create(
                    origin_determination=conflict.existing_origin,
                    action_type="merged",
                    curation_source=conflict.imported_source,
                    actor_name=request.user.username,
                    action_date=timezone.now(),
                    new_value=imported_data,
                    notes="Resolved via admin action: use imported",
                )
                
                # Mark conflict as resolved
                conflict.resolve(
                    strategy="use_imported",
                    resolved_origin=conflict.existing_origin,
                    resolved_by=request.user.username,
                    notes="Resolved via admin action: use imported",
                )
                count += 1
        self.message_user(request, f"Resolved {count} conflicts (used imported)")
    
    @admin.action(description="Resolve: Highest confidence")
    def resolve_highest_confidence(self, request, queryset):
        from scanpipe.models_curation import CurationProvenance
        from django.utils import timezone
        
        count = 0
        for conflict in queryset.filter(resolution_status="pending"):
            if conflict.existing_origin and conflict.imported_origin_data:
                existing_conf = (
                    1.0 if conflict.existing_origin.is_verified
                    else conflict.existing_origin.detected_origin_confidence or 0.5
                )
                imported_conf = conflict.imported_origin_data.get("confidence", 0.5)
                
                if imported_conf > existing_conf:
                    # Use imported
                    imported_data = conflict.imported_origin_data
                    conflict.existing_origin.amended_origin_type = imported_data["origin_type"]
                    conflict.existing_origin.amended_origin_identifier = imported_data["origin_identifier"]
                    conflict.existing_origin.amended_origin_notes = (
                        f"Resolved via admin action: higher confidence "
                        f"(imported: {imported_conf} vs existing: {existing_conf})"
                    )
                    conflict.existing_origin.amended_by = request.user.username
                    conflict.existing_origin.is_verified = imported_data.get("is_verified", False)
                    conflict.existing_origin.save()
                    
                    # Create provenance
                    CurationProvenance.objects.create(
                        origin_determination=conflict.existing_origin,
                        action_type="merged",
                        curation_source=conflict.imported_source,
                        actor_name=request.user.username,
                        action_date=timezone.now(),
                        new_value=imported_data,
                        notes=f"Higher confidence: {imported_conf} vs {existing_conf}",
                    )
                
                # Mark conflict as resolved (whether we kept existing or used imported)
                conflict.resolve(
                    strategy="highest_confidence",
                    resolved_origin=conflict.existing_origin,
                    resolved_by=request.user.username,
                    notes=f"Confidence comparison: imported={imported_conf}, existing={existing_conf}",
                )
                count += 1
        self.message_user(request, f"Resolved {count} conflicts (highest confidence)")


class CurationExportAdmin(ScanPipeBaseAdmin):
    list_display = [
        "project",
        "status",
        "origin_count",
        "verified_only",
        "created_by",
        "created_date",
    ]
    search_fields = [
        "project__name",
        "destination_url",
        "created_by",
        "error_message",
    ]
    list_filter = [
        "status",
        "export_format",
        "verified_only",
        "include_propagated",
    ]
    ordering = ["-created_date"]
    fieldsets = [
        ("Export Details", {
            "fields": ("project", "status", "export_format", "origin_count")
        }),
        ("Options", {
            "fields": ("verified_only", "include_propagated")
        }),
        ("Destination", {
            "fields": ("destination_source", "destination_url", "export_file_path", "git_commit_sha")
        }),
        ("Status", {
            "fields": ("created_by", "created_date", "completed_date", "error_message")
        }),
        ("Metadata", {
            "fields": ("metadata",),
            "classes": ("collapse",),
        }),
    ]
    readonly_fields = ["created_date", "completed_date"]


class ScanCodeIOAdminSite(admin.AdminSite):
    site_header = "ScanCode.io administration"
    site_title = "ScanCode.io administration"


admin_site = ScanCodeIOAdminSite(name="scancodeio_admin")
admin_site.register(Project, ProjectAdmin)
admin_site.register(CodebaseResource, CodebaseResourceAdmin)
admin_site.register(DiscoveredPackage, DiscoveredPackageAdmin)
admin_site.register(DiscoveredDependency, DiscoveredDependencyAdmin)
admin_site.register(CodeOriginDetermination, CodeOriginDeterminationAdmin)
admin_site.register(CurationSource, CurationSourceAdmin)
admin_site.register(CurationProvenance, CurationProvenanceAdmin)
admin_site.register(CurationConflict, CurationConflictAdmin)
admin_site.register(CurationExport, CurationExportAdmin)

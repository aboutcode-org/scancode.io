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

from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredLicense
from scanpipe.models import DiscoveredPackage
from scanpipe.models import OriginDetermination
from scanpipe.models import OriginMatch
from scanpipe.models import Project
from scanpipe.models import ProjectMessage
from scanpipe.models import Run
from scanpipe.models import WebhookSubscription


class ScanPipeBaseAdmin(admin.ModelAdmin):
    """Common ModelAdmin attributes."""

    actions_on_top = False
    actions_on_bottom = True
    show_facets = admin.ShowFacets.ALWAYS

    def has_add_permission(self, request):
        return False

    def lookup_allowed(self, lookup, value, *args, **kwargs):
        if lookup.startswith("project__"):
            return True
        return super().lookup_allowed(lookup, value, *args, **kwargs)


class ProjectAdmin(ScanPipeBaseAdmin):
    list_display = [
        "name",
        "label_list",
        "packages_link",
        "dependencies_link",
        "resources_link",
        "licenses_link",
        "messages_link",
        "relations_link",
        "runs_link",
        "is_archived",
    ]
    search_fields = ["uuid", "name"]
    list_filter = ["is_archived"]
    ordering = ["-created_date"]
    fieldsets = [
        ("", {"fields": ("name", "slug", "notes", "extra_data", "settings", "uuid")}),
        (
            "Links",
            {
                "fields": (
                    "packages_link",
                    "dependencies_link",
                    "resources_link",
                    "licenses_link",
                    "messages_link",
                    "relations_link",
                    "runs_link",
                )
            },
        ),
    ]
    readonly_fields = [
        "packages_link",
        "dependencies_link",
        "resources_link",
        "licenses_link",
        "messages_link",
        "relations_link",
        "runs_link",
        "uuid",
    ]

    @admin.display(description="Labels")
    def label_list(self, obj):
        return ", ".join(obj.labels)

    @staticmethod
    def make_filtered_link(obj, value, url_name):
        """Return a link to the provided ``url_name`` filtered by this project."""
        url = reverse(f"admin:scanpipe_{url_name}_changelist")
        return format_html(
            '<a href="{}?project__uuid__exact={}">{}</a>', url, obj.uuid, value
        )

    @admin.display(description="Packages", ordering="package_count")
    def packages_link(self, obj):
        count = obj.package_count
        return self.make_filtered_link(obj, count, "discoveredpackage")

    @admin.display(description="Dependencies", ordering="dependency_count")
    def dependencies_link(self, obj):
        count = obj.dependency_count
        return self.make_filtered_link(obj, count, "discovereddependency")

    @admin.display(description="Resources", ordering="resource_count")
    def resources_link(self, obj):
        count = obj.resource_count
        return self.make_filtered_link(obj, count, "codebaseresource")

    @admin.display(description="Licenses")
    def licenses_link(self, obj):
        count = obj.discoveredlicenses.count()
        return self.make_filtered_link(obj, count, "discoveredlicense")

    @admin.display(description="Messages", ordering="message_count")
    def messages_link(self, obj):
        count = obj.message_count
        return self.make_filtered_link(obj, count, "projectmessage")

    @admin.display(description="Relations", ordering="relation_count")
    def relations_link(self, obj):
        count = obj.relation_count
        return self.make_filtered_link(obj, count, "codebaserelation")

    @admin.display(description="Runs")
    def runs_link(self, obj):
        count = obj.runs.count()
        return self.make_filtered_link(obj, count, "run")


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


class OriginMatchAdmin(ScanPipeBaseAdmin):
    list_display = [
        "purl",
        "match_type",
        "similarity",
        "tool",
        "resource",
        "project",
    ]
    search_fields = [
        "uuid",
        "purl",
        "origin_path",
        "resource__path",
    ]
    list_filter = ["project", "match_type", "tool"]
    list_select_related = ["resource", "project"]
    ordering = ["project", "resource__path", "-similarity", "purl"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OriginDeterminationAdmin(ScanPipeBaseAdmin):
    list_display = [
        "resource",
        "purl",
        "status",
        "rule",
        "project",
    ]
    search_fields = [
        "uuid",
        "purl",
        "resource__path",
    ]
    list_filter = ["project", "status", "rule"]
    list_select_related = ["resource", "project"]
    ordering = ["project", "resource__path"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DiscoveredLicenseAdmin(ScanPipeBaseAdmin):
    list_display = [
        "identifier",
        "license_expression",
        "detection_count",
        "compliance_alert",
        "project",
    ]
    list_filter = ["compliance_alert", "is_license_clue", "needs_review"]
    search_fields = ["identifier", "license_expression"]


class ProjectMessageAdmin(ScanPipeBaseAdmin):
    list_display = [
        "severity",
        "model",
        "description",
        "created_date",
        "project",
    ]
    list_filter = ["severity", "model"]
    search_fields = ["description", "traceback"]


class CodebaseRelationAdmin(ScanPipeBaseAdmin):
    list_display = [
        "from_resource",
        "to_resource",
        "map_type",
        "project",
    ]
    list_filter = ["map_type"]


class RunStatusFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return Run.Status.choices

    def queryset(self, request, queryset):
        value = self.value()
        if value == Run.Status.SUCCESS:
            return queryset.succeed()
        elif value == Run.Status.FAILURE:
            return queryset.failed().exclude(task_exitcode__in=[88, 99])
        elif value == Run.Status.STOPPED:
            return queryset.filter(task_exitcode=99)
        elif value == Run.Status.STALE:
            return queryset.filter(task_exitcode=88)
        elif value == Run.Status.RUNNING:
            return queryset.running()
        elif value == Run.Status.QUEUED:
            return queryset.queued()
        elif value == Run.Status.NOT_STARTED:
            return queryset.not_started()
        return queryset


class RunAdmin(ScanPipeBaseAdmin):
    list_display = [
        "pipeline_name",
        "status",
        "task_start_date",
        "task_end_date",
        "project",
    ]
    list_filter = [RunStatusFilter, "pipeline_name"]


class WebhookSubscriptionAdmin(ScanPipeBaseAdmin):
    list_display = [
        "target_url",
        "is_active",
        "trigger_on_each_run",
        "project",
    ]


class ScanCodeIOAdminSite(admin.AdminSite):
    site_header = "ScanCode.io administration"
    site_title = "ScanCode.io administration"


admin_site = ScanCodeIOAdminSite(name="scancodeio_admin")
admin_site.register(Project, ProjectAdmin)
admin_site.register(CodebaseResource, CodebaseResourceAdmin)
admin_site.register(DiscoveredPackage, DiscoveredPackageAdmin)
admin_site.register(DiscoveredDependency, DiscoveredDependencyAdmin)
admin_site.register(OriginMatch, OriginMatchAdmin)
admin_site.register(OriginDetermination, OriginDeterminationAdmin)
admin_site.register(DiscoveredLicense, DiscoveredLicenseAdmin)
admin_site.register(ProjectMessage, ProjectMessageAdmin)
admin_site.register(CodebaseRelation, CodebaseRelationAdmin)
admin_site.register(Run, RunAdmin)
admin_site.register(WebhookSubscription, WebhookSubscriptionAdmin)

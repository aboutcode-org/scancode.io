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


class ScanCodeIOAdminSite(admin.AdminSite):
    site_header = "ScanCode.io administration"
    site_title = "ScanCode.io administration"


admin_site = ScanCodeIOAdminSite(name="scancodeio_admin")
admin_site.register(Project, ProjectAdmin)
admin_site.register(CodebaseResource, CodebaseResourceAdmin)
admin_site.register(DiscoveredPackage, DiscoveredPackageAdmin)
admin_site.register(DiscoveredDependency, DiscoveredDependencyAdmin)

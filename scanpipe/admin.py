# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.http import QueryDict
from django.utils.html import format_html

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import ProjectError


class InjectRequestChangeList(ChangeList):
    def get_results(self, request):
        """
        Inject the `request` on each object of the results_list.
        """
        super().get_results(request)
        for obj in self.result_list:
            obj._request = request


class ProjectRelatedModelAdmin(admin.ModelAdmin):
    """
    Regroup the common ModelAdmin values for Project related models.
    """

    list_select_related = True
    actions_on_top = False
    actions_on_bottom = True

    def has_add_permission(self, request):
        return False

    def get_changelist(self, request, **kwargs):
        return InjectRequestChangeList

    def project_filter(self, obj):
        return format_html(
            '<a href="?project__uuid__exact={project_uuid}">{project}</a>',
            project=obj.project,
            project_uuid=obj.project.uuid,
        )

    project_filter.short_description = "Project"
    project_filter.admin_order_field = "project"

    @staticmethod
    def as_filter(obj, field_name):
        field_value = getattr(obj, field_name, None)
        if field_value is None:
            return

        request = getattr(obj, "_request")
        if request:
            query_dict = request.GET.copy()
        else:
            query_dict = QueryDict()
        query_dict[field_name] = field_value

        return format_html(
            '<a href="?{query}">{field_value}</a>',
            query=query_dict.urlencode(),
            field_value=field_value,
        )

    def type_filter(self, obj):
        return self.as_filter(obj, field_name="type")

    type_filter.short_description = "Type"
    type_filter.admin_order_field = "type"

    def status_filter(self, obj):
        return self.as_filter(obj, field_name="status")

    status_filter.short_description = "Status"
    status_filter.admin_order_field = "status"

    def programming_language_filter(self, obj):
        return self.as_filter(obj, field_name="programming_language")

    programming_language_filter.short_description = "Programming language"
    programming_language_filter.admin_order_field = "programming_language"


@admin.register(CodebaseResource)
class CodebaseResourceAdmin(ProjectRelatedModelAdmin):
    list_display = (
        "project_filter",
        "path",
        "status_filter",
        "type_filter",
        "size",
        "name",
        "extension",
        "programming_language_filter",
        "mime_type",
        "file_type",
        "license_expressions",
        "copyrights",
        "for_packages",
    )
    list_display_links = ("path",)
    list_filter = ("project", "status", "type", "programming_language")
    search_fields = ("path", "mime_type", "file_type")


class CodebaseResourceInline(admin.TabularInline):
    model = DiscoveredPackage.codebase_resources.through
    extra = 0
    raw_id_fields = ("codebaseresource",)


@admin.register(DiscoveredPackage)
class DiscoveredPackageAdmin(ProjectRelatedModelAdmin):
    list_display = (
        "project_filter",
        "package_url",
        "type_filter",
        "namespace",
        "name",
        "version",
        "license_expression",
        "copyright",
    )
    list_display_links = ("package_url",)
    list_filter = ("project", "type")
    search_fields = ("name", "namespace", "description", "codebase_resources__path")
    exclude = ("codebase_resources",)
    inlines = (CodebaseResourceInline,)


@admin.register(ProjectError)
class ProjectErrorAdmin(ProjectRelatedModelAdmin):
    list_display = ("project_filter", "model", "message", "created_date", "uuid")
    list_display_links = ("message",)
    list_filter = ("project", "model")
    search_fields = ("uuid", "message")

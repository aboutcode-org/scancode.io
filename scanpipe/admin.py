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
from django.contrib.admin.utils import unquote
from django.contrib.admin.views.main import ChangeList
from django.http import FileResponse
from django.http import Http404
from django.http import QueryDict
from django.urls import path
from django.urls import reverse
from django.utils.html import format_html

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import ProjectError


class ListDisplayField:
    """
    Base class for `list_display` fields customization.
    """

    def __init__(self, name, **kwargs):
        self.name = name
        self.__name__ = name
        self.short_description = kwargs.get("short_description", name.replace("_", " "))
        kwargs.setdefault("admin_order_field", name)
        self.__dict__.update(kwargs)

    def __call__(self, obj):
        if obj:
            field_value = getattr(obj, self.name)
            if field_value:
                return self.to_representation(obj, field_value)

    def __repr__(self):
        return self.name

    def to_representation(self, obj, field_value):
        return field_value


class FilterLink(ListDisplayField):
    """
    Return the field as a link to filter by its value.
    """

    def __init__(self, name, filter_lookup=None, **kwargs):
        self.filter_lookup = filter_lookup
        super().__init__(name, **kwargs)

    def to_representation(self, obj, field_value):
        request = getattr(obj, "_request")
        query_dict = request.GET.copy() if request else QueryDict()
        query_dict[self.filter_lookup or self.name] = field_value

        return format_html(
            '<a href="?{query}">{field_value}</a>',
            query=query_dict.urlencode(),
            field_value=field_value,
        )


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


@admin.register(CodebaseResource)
class CodebaseResourceAdmin(ProjectRelatedModelAdmin):
    list_display = (
        "project_filter",
        "path",
        FilterLink("status"),
        FilterLink("type", filter_lookup="type__exact"),
        "size",
        "name",
        "extension",
        FilterLink("programming_language"),
        "mime_type",
        "file_type",
        "license_expressions",
        "copyrights",
        "for_packages",
        "view_file",
    )
    list_display_links = ("path",)
    list_filter = ("project", "status", "type", "programming_language")
    search_fields = ("path", "mime_type", "file_type")

    def get_urls(self):
        opts = self.model._meta
        urls = [
            path(
                "<path:object_id>/raw/",
                self.admin_site.admin_view(self.raw),
                name=f"{opts.app_label}_{opts.model_name}_raw",
            ),
        ]
        return urls + super().get_urls()

    def raw(self, request, object_id):
        resource = self.get_object(request, unquote(object_id))
        if resource is None:
            raise Http404

        resource_location_path = resource.location_path
        if resource_location_path.is_file():
            as_attachment = request.GET.get("as_attachment", False)
            return FileResponse(
                resource_location_path.open("rb"), as_attachment=as_attachment
            )

        raise Http404

    def view_file(self, obj):
        if obj.type != obj.Type.FILE:
            return

        opts = self.model._meta
        url = reverse(f"admin:{opts.app_label}_{opts.model_name}_raw", args=[obj.pk])
        return format_html(
            f'<a href="{url}" target="_blank">View</a><br>'
            f'<a href="{url}?as_attachment=1">Download</a>',
            url=url,
        )


class CodebaseResourceInline(admin.TabularInline):
    model = DiscoveredPackage.codebase_resources.through
    extra = 0
    raw_id_fields = ("codebaseresource",)


@admin.register(DiscoveredPackage)
class DiscoveredPackageAdmin(ProjectRelatedModelAdmin):
    list_display = (
        "project_filter",
        "package_url",
        FilterLink("type"),
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

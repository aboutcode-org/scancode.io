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

import json

from django import forms
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.admin.views.main import ChangeList
from django.core.serializers.json import DjangoJSONEncoder
from django.http import FileResponse
from django.http import Http404
from django.http import QueryDict
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.urls import path
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView

from scanpipe.api.serializers import get_model_serializer
from scanpipe.api.serializers import get_serializer_fields
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import ProjectError
from scanpipe.pipes.outputs import queryset_to_csv_stream


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


class JoinList(ListDisplayField):
    """
    Return the field value as joined list by provided `sep`.
    """

    def __init__(self, name, sep="<br>", **kwargs):
        self.sep = sep
        kwargs["admin_order_field"] = None
        super().__init__(name, **kwargs)

    def to_representation(self, obj, field_value):
        return mark_safe(self.sep.join(field_value))


class InjectRequestChangeList(ChangeList):
    def get_results(self, request):
        """
        Inject the `request` on each object of the results_list.
        """
        super().get_results(request)
        for obj in self.result_list:
            obj._request = request


class PathListFilter(admin.SimpleListFilter):
    """
    Filter by `path` using the `startswith` lookup.
    Only the provided value is displayed as a choice for visual clue on filter
    activity.
    """

    title = "path"
    parameter_name = "path"

    def lookups(self, request, model_admin):
        value = self.value()
        if value:
            return [(value, value)]
        return []

    def has_output(self):
        return True

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(path__startswith=self.value())


class Echo:
    """
    An object that implements just the write method of the file-like interface.
    """

    def write(self, value):
        """
        Write the value by returning it, instead of storing in a buffer.
        """
        return value


class ExportConfigurationForm(forms.Form):
    """
    Configuration form for exporting data including selected fields.
    """

    include_fields = forms.MultipleChoiceField(
        label="", widget=forms.CheckboxSelectMultiple(attrs={"checked": "checked"})
    )
    pks = forms.CharField(
        widget=forms.widgets.HiddenInput,
    )

    def __init__(self, model_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["include_fields"].choices = [
            (field, field) for field in get_serializer_fields(model_class)
        ]


class AdminExportView(FormView):
    """
    A view to configure an export and download the data.
    """

    template_name = "admin/export.html"
    form_class = ExportConfigurationForm
    model_admin = None
    model_class = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.model_class = self.model_admin.model

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["model_class"] = self.model_class
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial.update({"pks": self.request.GET.get("pks")})
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "title": "Export to CSV",
            "opts": self.model_class._meta,
            "has_view_permission": self.model_admin.has_view_permission(self.request),
            "media": self.model_admin.media,
        }
        return {**context, **extra_context}

    def form_valid(self, form):
        model_name = self.model_class._meta.model_name
        pks = form.cleaned_data["pks"].split(",")
        queryset = self.model_class.objects.filter(pk__in=pks)
        fieldnames = form.cleaned_data["include_fields"]
        output_stream = Echo()

        streaming_content = queryset_to_csv_stream(queryset, fieldnames, output_stream)
        response = StreamingHttpResponse(streaming_content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{model_name}.csv"'
        return response


class ProjectRelatedModelAdmin(admin.ModelAdmin):
    """
    Regroup the common ModelAdmin values for Project related models.
    """

    list_select_related = True
    actions_on_top = True
    actions_on_bottom = True
    prefetch_related = None

    def has_add_permission(self, request):
        return False

    def get_changelist(self, request, **kwargs):
        return InjectRequestChangeList

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if self.prefetch_related:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        return queryset

    def project_filter(self, obj):
        return format_html(
            '<a href="?project__uuid__exact={project_uuid}">{project}</a>',
            project=obj.project,
            project_uuid=obj.project.uuid,
        )

    project_filter.short_description = "Project"
    project_filter.admin_order_field = "project"

    def get_urls(self):
        urls = []
        actions = getattr(self, "actions", [])

        if "export_to_csv" in actions:
            opts = self.model._meta
            export_view = AdminExportView.as_view(model_admin=self)
            urls.append(
                path(
                    "export/",
                    self.admin_site.admin_view(export_view),
                    name=f"{opts.app_label}_{opts.model_name}_export",
                ),
            )
        return urls + super().get_urls()

    def export_to_csv(self, request, queryset):
        opts = self.model._meta
        view_url = reverse(f"admin:{opts.app_label}_{opts.model_name}_export")
        selected = queryset.values_list("pk", flat=True)
        params = urlencode({"pks": ",".join(str(pk) for pk in selected)})
        return redirect(f"{view_url}?{params}")

    export_to_csv.short_description = "Export selected objects to CSV"

    def export_to_json(self, request, queryset):
        model_name = queryset.model._meta.model_name
        serializer_class = get_model_serializer(queryset.model)
        serializer = serializer_class(queryset, many=True)
        json_data = json.dumps(serializer.data, indent=2, cls=DjangoJSONEncoder)

        response = StreamingHttpResponse(json_data, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{model_name}.json"'
        return response

    export_to_json.short_description = "Export selected objects to JSON"


def get_admin_url(obj, view="change"):
    """
    Return an admin URL for the provided `obj`.
    """
    opts = obj._meta
    viewname = f"admin:{opts.app_label}_{opts.model_name}_{view}"
    return reverse(viewname, args=[obj.pk])


@admin.register(CodebaseResource)
class CodebaseResourceAdmin(ProjectRelatedModelAdmin):
    list_display = (
        "project_filter",
        "path_filter",
        FilterLink("status"),
        FilterLink("type", filter_lookup="type__exact"),
        "size",
        "name",
        "extension",
        FilterLink("programming_language"),
        "mime_type",
        "file_type",
        JoinList("license_expressions"),
        "packages",
        "view_file_links",
    )
    list_display_links = None
    list_filter = ("project", "status", "type", "programming_language", PathListFilter)
    search_fields = ("path", "mime_type", "file_type")
    ordering = ["path"]
    prefetch_related = ["discovered_packages"]
    actions = ["export_to_csv", "export_to_json"]

    def path_filter(self, obj):
        """
        Split the `obj.path` into clickable segments.
        Each segments link to a filter by itself.
        The last segment link target the object form view.
        """
        links = []
        segments = obj.path.split("/")
        segments_len = len(segments)

        for index, segment in enumerate(segments, start=1):
            current_path = "/".join(segments[:index])
            last_segment = index == segments_len
            if last_segment:
                links.append(f'<b><a href="{get_admin_url(obj)}">{segment}</a></b>')
            else:
                request = getattr(obj, "_request")
                query_dict = request.GET.copy() if request else QueryDict()
                query_dict["path"] = current_path
                links.append(f'<a href="?{query_dict.urlencode()}">{segment}</a>')

        return mark_safe('<span class="path_separator">/</span>'.join(links))

    path_filter.short_description = "Path"
    path_filter.admin_order_field = "path"

    def packages(self, obj):
        return mark_safe(
            "<br>".join(
                f'<a href="{get_admin_url(package)}">{package}</a>'
                for package in obj.discovered_packages.all()
            )
        )

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

    def view_file_links(self, obj):
        if obj.type == obj.Type.FILE:
            return format_html(
                '<a href="{url}" target="_blank">View</a><br>'
                '<a href="{url}?as_attachment=1">Download</a>',
                url=get_admin_url(obj, view="raw"),
            )

    view_file_links.short_description = "File"


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
        "resources",
    )
    list_display_links = ("package_url",)
    list_filter = ("project", "type")
    search_fields = ("name", "namespace", "description", "codebase_resources__path")
    exclude = ("codebase_resources",)
    inlines = (CodebaseResourceInline,)
    prefetch_related = ["codebase_resources"]
    actions = ["export_to_csv", "export_to_json"]

    def resources(self, obj):
        return mark_safe(
            "<br>".join(
                f'<a href="{get_admin_url(resource)}">{resource.path}</a>'
                for resource in obj.codebase_resources.all()
            )
        )


@admin.register(ProjectError)
class ProjectErrorAdmin(ProjectRelatedModelAdmin):
    list_display = ("project_filter", "model", "message", "created_date", "uuid")
    list_display_links = ("message",)
    list_filter = ("project", "model")
    search_fields = ("uuid", "message")

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

import difflib
import io
import json
import operator
from collections import Counter
from collections import namedtuple
from contextlib import suppress
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage.filesystem import FileSystemStorage
from django.db.models.manager import Manager
from django.http import FileResponse
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.defaultfilters import filesizeformat
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView
from django.views.generic.edit import UpdateView

import saneyaml
import xlsxwriter
from django_filters.views import FilterView

from scancodeio.auth import ConditionalLoginRequired
from scancodeio.auth import conditional_login_required
from scanpipe.api.serializers import DiscoveredDependencySerializer
from scanpipe.filters import PAGE_VAR
from scanpipe.filters import DependencyFilterSet
from scanpipe.filters import ErrorFilterSet
from scanpipe.filters import PackageFilterSet
from scanpipe.filters import ProjectFilterSet
from scanpipe.filters import ResourceFilterSet
from scanpipe.forms import AddInputsForm
from scanpipe.forms import AddPipelineForm
from scanpipe.forms import ArchiveProjectForm
from scanpipe.forms import ProjectForm
from scanpipe.forms import ProjectSettingsForm
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.models import RunInProgressError
from scanpipe.pipes import count_group_by
from scanpipe.pipes import output

scanpipe_app = apps.get_app_config("scanpipe")


LICENSE_CLARITY_FIELDS = [
    (
        "Declared license",
        "declared_license",
        "Indicates that the software package licensing is documented at top-level or "
        "well-known locations in the software project, typically in a package "
        "manifest, NOTICE, LICENSE, COPYING or README file. "
        "Scoring Weight = 40.",
        "+40",
    ),
    (
        "Identification precision",
        "identification_precision",
        "Indicates how well the license statement(s) of the software identify known "
        "licenses that can be designated by precise keys (identifiers) as provided in "
        "a publicly available license list, such as the ScanCode LicenseDB, the SPDX "
        "license list, the OSI license list, or a URL pointing to a specific license "
        "text in a project or organization website. "
        "Scoring Weight = 40.",
        "+40",
    ),
    (
        "License text",
        "has_license_text",
        "Indicates that license texts are provided to support the declared license "
        "expression in files such as a package manifest, NOTICE, LICENSE, COPYING or "
        "README. "
        "Scoring Weight = 10.",
        "+10",
    ),
    (
        "Declared copyrights",
        "declared_copyrights",
        "Indicates that the software package copyright is documented at top-level or "
        "well-known locations in the software project, typically in a package "
        "manifest, NOTICE, LICENSE, COPYING or README file. "
        "Scoring Weight = 10.",
        "+10",
    ),
    (
        "Ambiguous compound licensing",
        "ambiguous_compound_licensing",
        "Indicates that the software has a license declaration that makes it "
        "difficult to construct a reliable license expression, such as in the case "
        "of multiple licenses where the conjunctive versus disjunctive relationship "
        "is not well defined. "
        "Scoring Weight = -10.",
        "-10",
    ),
    (
        "Conflicting license categories",
        "conflicting_license_categories",
        "Indicates the declared license expression of the software is in the "
        "permissive category, but that other potentially conflicting categories, "
        "such as copyleft and proprietary, have been detected in lower level code. "
        "Scoring Weight = -20.",
        "-20",
    ),
    (
        "Score",
        "score",
        "The license clarity score is a value from 0-100 calculated by combining the "
        "weighted values determined for each of the scoring elements: Declared license,"
        " Identification precision, License text, Declared copyrights, Ambiguous "
        "compound licensing, and Conflicting license categories.",
        None,
    ),
]


SCAN_SUMMARY_FIELDS = [
    ("Declared license", "declared_license_expression"),
    ("Declared holder", "declared_holder"),
    ("Primary language", "primary_language"),
    ("Other licenses", "other_license_expressions"),
    ("Other holders", "other_holders"),
    ("Other languages", "other_languages"),
]


class PrefetchRelatedViewMixin:
    prefetch_related = None

    def get_queryset(self):
        return super().get_queryset().prefetch_related(*self.prefetch_related)


def render_as_yaml(value):
    if value:
        return saneyaml.dump(value, indent=2)


def fields_have_no_values(fields_data):
    return not any([field_data.get("value") for field_data in fields_data.values()])


def do_not_disable(*args, **kwargs):
    return False


DISPLAYABLE_IMAGE_MIME_TYPE = [
    "image/apng",
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/webp",
    "image/x-icon",
]


def is_displayable_image_type(resource):
    """Return True if the ``resource`` file is supported by the HTML <img> tag."""
    return resource.mime_type and resource.mime_type in DISPLAYABLE_IMAGE_MIME_TYPE


class TabSetMixin:
    """
    tabset = {
        "<tab_id>": {
            "fields": [
                "<field_name>",
                "<field_name>",
                {
                    "field_name": "<field_name>",
                    "label": None,
                    "template": None,
                    "render_func": None,
                },
            ],
            "verbose_name": "",
            "template": "",
            "icon_class": "",
            "display_condition": <func>,
            "disable_condition": <func>,
        }
    }
    """

    tabset = {}

    def get_tabset_data(self):
        """Return the tabset data structure used in template rendering."""
        tabset_data = {}

        for tab_id, tab_definition in self.tabset.items():
            if tab_data := self.get_tab_data(tab_definition):
                tabset_data[tab_id] = tab_data

        return tabset_data

    def get_tab_data(self, tab_definition):
        """Return the data for a single tab based on the ``tab_definition``."""
        if display_condition := tab_definition.get("display_condition"):
            if not display_condition(self.object):
                return

        fields_data = self.get_fields_data(fields=tab_definition.get("fields", []))

        is_disabled = False
        if disable_condition := tab_definition.get("disable_condition"):
            is_disabled = disable_condition(self.object, fields_data)
        # This can be bypassed by providing ``do_not_disable`` to ``disable_condition``
        elif fields_have_no_values(fields_data):
            is_disabled = True

        tab_data = {
            "verbose_name": tab_definition.get("verbose_name"),
            "icon_class": tab_definition.get("icon_class"),
            "template": tab_definition.get("template"),
            "fields": fields_data,
            "disabled": is_disabled,
            "label_count": self.get_label_count(fields_data),
        }

        return tab_data

    def get_fields_data(self, fields):
        """Return the tab fields including their values for display."""
        fields_data = {}

        for field_definition in fields:
            # Support for single "field_name" entry in fields list.
            if not isinstance(field_definition, dict):
                field_name = field_definition
                field_data = {"field_name": field_name}
            else:
                field_name = field_definition.get("field_name")
                field_data = field_definition.copy()

            if "label" not in field_data:
                field_data["label"] = self.get_field_label(field_name)

            render_func = field_data.get("render_func")
            field_data["value"] = self.get_field_value(field_name, render_func)

            fields_data[field_name] = field_data

        return fields_data

    def get_field_value(self, field_name, render_func=None):
        """Return the formatted value for the given `field_name` of the object."""
        field_value = getattr(self.object, field_name, None)

        if field_value and render_func:
            return render_func(field_value)

        if isinstance(field_value, Manager):
            return list(field_value.all())

        if isinstance(field_value, list):
            with suppress(TypeError):
                field_value = "\n".join(field_value)

        return field_value

    @staticmethod
    def get_field_label(field_name):
        """Return a formatted label for display based on the `field_name`."""
        return field_name.replace("_", " ").capitalize().replace("url", "URL")

    @staticmethod
    def get_label_count(fields_data):
        """
        Return the count of objects to be displayed in the tab label.

        This only support tabs with a single field that has a single `list` for value.
        """
        if len(fields_data.keys()) == 1:
            value = list(fields_data.values())[0].get("value")
            if isinstance(value, list):
                return len(value)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tabset_data"] = self.get_tabset_data()
        return context


class TableColumnsMixin:
    """
    table_columns = [
        "<field_name>",
        "<field_name>",
        {
            "field_name": "<field_name>",
            "label": None,
            "condition": None,
            "sort_name": None,
            "css_class": None,
        },
    ]
    """

    table_columns = []

    def get_columns_data(self):
        """Return the columns data structure used in template rendering."""
        columns_data = []

        sortable_fields = []
        active_sort = ""
        filterset = getattr(self, "filterset", None)
        if filterset and "sort" in filterset.filters:
            sortable_fields = list(filterset.filters["sort"].param_map.keys())
            active_sort = filterset.data.get("sort", "")

        for column_definition in self.table_columns:
            # Support for single "field_name" entry in columns list.
            if not isinstance(column_definition, dict):
                field_name = column_definition
                column_data = {"field_name": field_name}
            else:
                field_name = column_definition.get("field_name")
                column_data = column_definition.copy()

            condition = column_data.get("condition", None)
            if condition is not None and not bool(condition):
                continue

            if "label" not in column_data:
                column_data["label"] = self.get_field_label(field_name)

            sort_name = column_data.get("sort_name") or field_name
            if sort_name in sortable_fields:
                is_sorted = sort_name == active_sort.lstrip("-")

                sort_direction = ""
                if is_sorted and not active_sort.startswith("-"):
                    sort_direction = "-"

                column_data["is_sorted"] = is_sorted
                column_data["sort_direction"] = sort_direction
                query_dict = self.request.GET.copy()
                query_dict["sort"] = f"{sort_direction}{sort_name}"
                column_data["sort_query"] = query_dict.urlencode()

            if filter_fieldname := column_data.get("filter_fieldname"):
                column_data["filter"] = filterset.form[filter_fieldname]

            columns_data.append(column_data)

        return columns_data

    @staticmethod
    def get_field_label(field_name):
        """Return a formatted label for display based on the `field_name`."""
        return field_name.replace("_", " ").capitalize().replace("url", "URL")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns_data"] = self.get_columns_data()
        context["request_query_string"] = self.request.GET.urlencode()
        return context


class ExportXLSXMixin:
    """
    Add the ability to export the current filtered QuerySet of a `FilterView` into
    the XLSX format.
    """

    export_xlsx_query_param = "export_xlsx"

    def export_xlsx_file_response(self):
        filtered_qs = self.filterset.qs
        output_file = io.BytesIO()
        with xlsxwriter.Workbook(output_file) as workbook:
            output.queryset_to_xlsx_worksheet(filtered_qs, workbook)

        filename = f"{self.project.name}_{self.model._meta.model_name}.xlsx"
        output_file.seek(0)
        return FileResponse(output_file, as_attachment=True, filename=filename)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query_dict = self.request.GET.copy()
        query_dict[self.export_xlsx_query_param] = True
        context["export_xlsx_url_query"] = query_dict.urlencode()

        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        if request.GET.get(self.export_xlsx_query_param):
            return self.export_xlsx_file_response()

        return response


class PaginatedFilterView(FilterView):
    """
    Add a `url_params_without_page` value in the template context to include the
    current filtering in the pagination.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query_dict = self.request.GET.copy()
        query_dict.pop(PAGE_VAR, None)
        context["url_params_without_page"] = query_dict.urlencode()

        return context


class AccountProfileView(LoginRequiredMixin, generic.TemplateView):
    template_name = "account/profile.html"


class ProjectListView(
    ConditionalLoginRequired,
    PrefetchRelatedViewMixin,
    TableColumnsMixin,
    PaginatedFilterView,
):
    model = Project
    filterset_class = ProjectFilterSet
    template_name = "scanpipe/project_list.html"
    prefetch_related = ["runs"]
    paginate_by = settings.SCANCODEIO_PAGINATE_BY.get("project", 20)
    table_columns = [
        "name",
        {
            "field_name": "discoveredpackages",
            "label": "Packages",
            "sort_name": "discoveredpackages_count",
        },
        {
            "field_name": "discovereddependencies",
            "label": "Dependencies",
            "sort_name": "discovereddependencies_count",
        },
        {
            "field_name": "codebaseresources",
            "label": "Resources",
            "sort_name": "codebaseresources_count",
        },
        {
            "field_name": "projecterrors",
            "label": "Errors",
            "sort_name": "projecterrors_count",
        },
        {
            "field_name": "runs",
            "label": "Pipelines",
        },
        {
            "label": "",
            "css_class": "is-narrow",
        },
    ]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .with_counts(
                "codebaseresources",
                "discoveredpackages",
                "discovereddependencies",
                "projecterrors",
            )
        )


class ProjectCreateView(ConditionalLoginRequired, generic.CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "scanpipe/project_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pipelines"] = {
            key: pipeline_class.get_info()
            for key, pipeline_class in scanpipe_app.pipelines.items()
        }
        return context

    def is_xhr(self):
        return self.request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.is_xhr():
            return JsonResponse({"redirect_url": self.get_success_url()}, status=201)

        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)

        if self.is_xhr():
            return JsonResponse({"errors": str(form.errors)}, status=400)

        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class ProjectDetailView(ConditionalLoginRequired, generic.DetailView):
    model = Project
    template_name = "scanpipe/project_detail.html"

    @staticmethod
    def get_license_clarity_data(scan_summary_json):
        license_clarity_score = scan_summary_json.get("license_clarity_score", {})
        return [
            {
                "label": label,
                "value": license_clarity_score.get(field),
                "help_text": help_text,
                "weight": weight,
            }
            for label, field, help_text, weight in LICENSE_CLARITY_FIELDS
        ]

    @staticmethod
    def get_scan_summary_data(scan_summary_json):
        summary_data = {}

        for field_label, field_name in SCAN_SUMMARY_FIELDS:
            field_data = scan_summary_json.get(field_name)

            if type(field_data) is list:
                # Do not include `None` entries
                values = [entry for entry in field_data if entry.get("value")]
            else:
                # Converts single value type into common data-structure
                values = [{"value": field_data}]

            summary_data[field_label] = values

        return summary_data

    def check_run_scancode_version(self, pipeline_runs, version_limit="32.2.0"):
        """
        Display a warning message if one of the ``pipeline_runs`` scancodeio_version
        is prior to or currently is ``old_version``.
        """
        run_versions = [
            run.scancodeio_version for run in pipeline_runs if run.scancodeio_version
        ]
        if run_versions and min(run_versions) <= version_limit:
            message = (
                "WARNING: Some this project pipelines have been run with an "
                "out of date ScanCode-toolkit version.\n"
                "The scan data was migrated, but it is recommended to reset the "
                "project and re-run the pipelines to benefit from the latest "
                "scan results improvements."
            )
            messages.warning(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        inputs, missing_inputs = project.inputs_with_source
        if missing_inputs:
            missing_files = "\n- ".join(missing_inputs.keys())
            message = (
                f"The following input files are not available on disk anymore:\n"
                f"- {missing_files}"
            )
            messages.error(self.request, message)

        if project.is_archived:
            message = "WARNING: This project is archived and read-only."
            messages.warning(self.request, message)

        license_clarity = []
        scan_summary = {}
        scan_summary_file = project.get_latest_output(filename="summary")

        if scan_summary_file:
            with suppress(json.decoder.JSONDecodeError):
                scan_summary_json = json.loads(scan_summary_file.read_text())
                license_clarity = self.get_license_clarity_data(scan_summary_json)
                scan_summary = self.get_scan_summary_data(scan_summary_json)

        codebase_root = sorted(
            project.codebase_path.glob("*"),
            key=operator.attrgetter("name"),
        )
        codebase_root.sort(key=operator.methodcaller("is_file"))

        resource_status_summary = count_group_by(project.codebaseresources, "status")

        pipeline_runs = project.runs.all()
        self.check_run_scancode_version(pipeline_runs)

        context.update(
            {
                "inputs_with_source": inputs,
                "add_pipeline_form": AddPipelineForm(),
                "add_inputs_form": AddInputsForm(),
                "archive_form": ArchiveProjectForm(),
                "resource_status_summary": resource_status_summary,
                "license_clarity": license_clarity,
                "scan_summary": scan_summary,
                "pipeline_runs": pipeline_runs,
                "codebase_root": codebase_root,
                "file_filter": self.request.GET.get("file-filter", "all"),
            }
        )

        if project.extra_data:
            context["extra_data_yaml"] = render_as_yaml(project.extra_data)

        return context

    def post(self, request, *args, **kwargs):
        project = self.get_object()

        if "add-inputs-submit" in request.POST:
            form_class = AddInputsForm
            success_message = "Input file(s) added."
            error_message = "Input file addition error."
        else:
            form_class = AddPipelineForm
            success_message = "Pipeline added."
            error_message = "Pipeline addition error."

        form_kwargs = {"data": request.POST, "files": request.FILES}
        form = form_class(**form_kwargs)
        if form.is_valid():
            form.save(project)
            messages.success(request, success_message)
        else:
            messages.error(request, error_message)

        return redirect(project)


class ProjectSettingsView(ConditionalLoginRequired, UpdateView):
    model = Project
    template_name = "scanpipe/project_settings.html"

    form_class = ProjectSettingsForm
    success_message = 'The project "{}" settings have been updated.'

    def form_valid(self, form):
        response = super().form_valid(form)
        project = self.get_object()
        messages.success(self.request, self.success_message.format(project))
        return response

    def get(self, request, *args, **kwargs):
        if request.GET.get("download"):
            return self.download_config_file(project=self.get_object())
        return super().get(request, *args, **kwargs)

    @staticmethod
    def download_config_file(project):
        """
        Download the ``scancode-config.yml`` config file generated from the current
        project settings.
        """
        response = FileResponse(
            streaming_content=project.get_settings_as_yml(),
            content_type="application/x-yaml",
        )
        filename = output.safe_filename(settings.SCANCODEIO_CONFIG_FILE)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ProjectChartsView(ConditionalLoginRequired, generic.DetailView):
    model = Project
    template_name = "scanpipe/project_charts.html"

    @staticmethod
    def get_summary(values_list, limit=settings.SCANCODEIO_MOST_COMMON_LIMIT):
        counter = Counter(values_list)

        has_only_empty_string = list(counter.keys()) == [""]
        if has_only_empty_string:
            return {}

        most_common = dict(counter.most_common(limit))

        other = sum(counter.values()) - sum(most_common.values())
        if other > 0:
            most_common["Other"] = other

        # Set a label for empty string value and move to last entry in the dict
        if "" in most_common:
            most_common["(No value detected)"] = most_common.pop("")

        return most_common

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        file_filter = self.request.GET.get("file-filter", "all")
        context["file_filter"] = file_filter

        files = project.codebaseresources.files()
        if file_filter == "in-a-package":
            files = files.in_package()
        elif file_filter == "not-in-a-package":
            files = files.not_in_package()

        charts = {
            "file": {
                "queryset": files,
                "fields": [
                    "programming_language",
                    "mime_type",
                    "holders",
                    "copyrights",
                    "detected_license_expression",
                    "compliance_alert",
                ],
            },
            "package": {
                "queryset": project.discoveredpackages,
                "fields": ["type", "declared_license_expression"],
            },
            "dependency": {
                "queryset": project.discovereddependencies,
                "fields": ["type", "is_runtime", "is_optional", "is_resolved"],
            },
        }

        for group_name, spec in charts.items():
            fields = spec["fields"]
            # Clear the un-needed ordering to get faster queries
            qs_values = spec["queryset"].values(*fields).order_by()

            for field_name in fields:
                if field_name in ["holders", "copyrights"]:
                    field_values = (
                        data.get(field_name[:-1])
                        for entry in qs_values
                        for data in entry.get(field_name, [])
                        if isinstance(data, dict)
                    )
                else:
                    field_values = (entry[field_name] for entry in qs_values)

                context[f"{group_name}_{field_name}"] = self.get_summary(field_values)

        return context


class ProjectCodebaseView(ConditionalLoginRequired, generic.DetailView):
    model = Project
    template_name = "scanpipe/includes/project_codebase.html"

    @staticmethod
    def get_tree(project, current_dir):
        """
        Return the direct content of the ``current_dir`` as a flat tree.

        The lookups are scoped to the ``project`` codebase/ work directory.
        The security is handled by the FileSystemStorage and will raise a
        SuspiciousFileOperation for attempting to look outside the codebase/ directory.
        """
        codebase_root = project.codebase_path.resolve()
        if not codebase_root.exists():
            raise ValueError("codebase/ work directory not found")

        # Raises ValueError if the codebase_root is not within the workspace_path
        codebase_root.relative_to(scanpipe_app.workspace_path)
        fs_storage = FileSystemStorage(location=codebase_root)
        directories, files = fs_storage.listdir(current_dir)

        def get_node(name, is_dir, location):
            return {
                "name": name,
                "is_dir": is_dir,
                "location": location,
            }

        tree = []
        root_directory = "."
        include_parent = current_dir and current_dir != root_directory
        if include_parent:
            tree.append(
                get_node(name="..", is_dir=True, location=str(Path(current_dir).parent))
            )

        for resources, is_dir in [(sorted(directories), True), (sorted(files), False)]:
            tree.extend(
                get_node(name=name, is_dir=is_dir, location=f"{current_dir}/{name}")
                for name in resources
            )

        return tree

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_dir = self.request.GET.get("current_dir") or "."

        try:
            codebase_tree = self.get_tree(self.object, current_dir)
        except FileNotFoundError:
            raise Http404(f"{current_dir} not found")
        except (ValueError, SuspiciousFileOperation) as error:
            raise Http404(error)

        context["current_dir"] = current_dir
        context["codebase_tree"] = codebase_tree
        return context


class ProjectArchiveView(ConditionalLoginRequired, SingleObjectMixin, FormView):
    model = Project
    http_method_names = ["post"]
    form_class = ArchiveProjectForm
    success_url = reverse_lazy("project_list")
    success_message = 'The project "{}" has been archived.'

    def form_valid(self, form):
        response = super().form_valid(form)

        project = self.get_object()
        try:
            project.archive(
                remove_input=form.cleaned_data["remove_input"],
                remove_codebase=form.cleaned_data["remove_codebase"],
                remove_output=form.cleaned_data["remove_output"],
            )
        except RunInProgressError as error:
            messages.error(self.request, error)
            return redirect(project)

        messages.success(self.request, self.success_message.format(project))
        return response


class ProjectDeleteView(ConditionalLoginRequired, generic.DeleteView):
    model = Project
    success_url = reverse_lazy("project_list")
    success_message = 'The project "{}" and all its related data have been removed.'

    def form_valid(self, form):
        project = self.get_object()
        try:
            response_redirect = super().form_valid(form)
        except RunInProgressError as error:
            messages.error(self.request, error)
            return redirect(project)

        messages.success(self.request, self.success_message.format(project.name))
        return response_redirect


class ProjectResetView(ConditionalLoginRequired, generic.DeleteView):
    model = Project
    success_message = 'All data, except inputs, for the "{}" project have been removed.'

    def form_valid(self, form):
        """Call the reset() method on the project."""
        project = self.get_object()
        try:
            project.reset(keep_input=True)
        except RunInProgressError as error:
            messages.error(self.request, error)
        else:
            messages.success(self.request, self.success_message.format(project.name))

        return redirect(project)


@conditional_login_required
def execute_pipeline_view(request, slug, run_uuid):
    project = get_object_or_404(Project, slug=slug)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status != run.Status.NOT_STARTED:
        raise Http404("Pipeline already queued, started or completed.")

    run.execute_task_async()
    messages.success(request, f"Pipeline {run.pipeline_name} run started.")
    return redirect(project)


@conditional_login_required
def stop_pipeline_view(request, slug, run_uuid):
    project = get_object_or_404(Project, slug=slug)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status != run.Status.RUNNING:
        raise Http404("Pipeline is not running.")

    run.stop_task()
    messages.success(request, f"Pipeline {run.pipeline_name} stopped.")
    return redirect(project)


@conditional_login_required
def delete_pipeline_view(request, slug, run_uuid):
    project = get_object_or_404(Project, slug=slug)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status not in [run.Status.NOT_STARTED, run.Status.QUEUED]:
        raise Http404("Only non started or queued pipelines can be deleted.")

    run.delete_task()
    messages.success(request, f"Pipeline {run.pipeline_name} deleted.")
    return redirect(project)


@require_POST
@conditional_login_required
def delete_input_view(request, slug, input_name):
    project = get_object_or_404(Project, slug=slug)

    if not project.can_change_inputs:
        raise Http404("Inputs cannot be deleted on this project.")

    deleted = project.delete_input(name=input_name)
    if deleted:
        messages.success(request, f"Input {input_name} deleted.")
    else:
        messages.error(request, f"Input {input_name} not found.")
    return redirect(project)


@conditional_login_required
def download_input_view(request, slug, input_name):
    project = get_object_or_404(Project, slug=slug)

    file_path = project.input_path / input_name
    if not file_path.exists():
        raise Http404(f"{file_path} not found")

    return FileResponse(file_path.open("rb"), as_attachment=True)


def project_results_json_response(project, as_attachment=False):
    """
    Return the results as JSON compatible with ScanCode data format.
    The content is returned as a stream of JSON content using the JSONResultsGenerator
    class.
    If `as_attachment` is True, the response will force the download of the file.
    """
    results_generator = output.JSONResultsGenerator(project)
    response = FileResponse(
        streaming_content=results_generator,
        content_type="application/json",
    )

    if as_attachment:
        filename = output.safe_filename(f"scancodeio_{project.name}.json")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


class ProjectResultsView(ConditionalLoginRequired, generic.DetailView):
    model = Project

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        project = self.object
        format = self.kwargs["format"]

        if format == "json":
            return project_results_json_response(project, as_attachment=True)
        elif format == "xlsx":
            output_file = output.to_xlsx(project)
        elif format == "spdx":
            output_file = output.to_spdx(project)
        elif format == "cyclonedx":
            output_file = output.to_cyclonedx(project)
        elif format == "attribution":
            output_file = output.to_attribution(project)
        else:
            raise Http404("Format not supported.")

        filename = output.safe_filename(f"scancodeio_{project.name}_{output_file.name}")

        return FileResponse(
            output_file.open("rb"),
            filename=filename,
            as_attachment=True,
        )


class ProjectRelatedViewMixin:
    model_label = None

    def get_project(self):
        if not getattr(self, "project", None):
            self.project = get_object_or_404(Project, slug=self.kwargs["slug"])
        return self.project

    def get_queryset(self):
        return (
            super().get_queryset().select_related("project").project(self.get_project())
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        context["model_label"] = self.model_label
        return context


class CodebaseResourceListView(
    ConditionalLoginRequired,
    PrefetchRelatedViewMixin,
    ProjectRelatedViewMixin,
    TableColumnsMixin,
    ExportXLSXMixin,
    PaginatedFilterView,
):
    model = CodebaseResource
    filterset_class = ResourceFilterSet
    template_name = "scanpipe/resource_list.html"
    paginate_by = settings.SCANCODEIO_PAGINATE_BY.get("resource", 100)
    prefetch_related = ["discovered_packages"]
    table_columns = [
        "path",
        {
            "field_name": "status",
            "filter_fieldname": "status",
        },
        {
            "field_name": "type",
            "filter_fieldname": "type",
        },
        "size",
        "name",
        "extension",
        "programming_language",
        "mime_type",
        "tag",
        {
            "field_name": "detected_license_expression",
            "filter_fieldname": "detected_license_expression",
        },
        {
            "field_name": "compliance_alert",
            "condition": scanpipe_app.policies_enabled,
            "filter_fieldname": "compliance_alert",
            "filter_is_right": True,
        },
        {
            "field_name": "packages",
            "filter_fieldname": "in_package",
            "filter_is_right": True,
        },
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["display_compliance_alert"] = scanpipe_app.policies_enabled
        return context


class DiscoveredPackageListView(
    ConditionalLoginRequired,
    PrefetchRelatedViewMixin,
    ProjectRelatedViewMixin,
    TableColumnsMixin,
    ExportXLSXMixin,
    PaginatedFilterView,
):
    model = DiscoveredPackage
    filterset_class = PackageFilterSet
    template_name = "scanpipe/package_list.html"
    paginate_by = settings.SCANCODEIO_PAGINATE_BY.get("package", 100)
    prefetch_related = ["codebase_resources"]
    table_columns = [
        {
            "field_name": "package_url",
            "filter_fieldname": "is_vulnerable",
        },
        {
            "field_name": "declared_license_expression",
            "filter_fieldname": "declared_license_expression",
        },
        {
            "field_name": "compliance_alert",
            "condition": scanpipe_app.policies_enabled,
            "filter_fieldname": "compliance_alert",
        },
        {
            "field_name": "copyright",
            "filter_fieldname": "copyright",
        },
        "primary_language",
        "resources",
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["display_compliance_alert"] = scanpipe_app.policies_enabled
        return context


class DiscoveredDependencyListView(
    ConditionalLoginRequired,
    PrefetchRelatedViewMixin,
    ProjectRelatedViewMixin,
    TableColumnsMixin,
    ExportXLSXMixin,
    PaginatedFilterView,
):
    model = DiscoveredDependency
    filterset_class = DependencyFilterSet
    template_name = "scanpipe/dependency_list.html"
    paginate_by = settings.SCANCODEIO_PAGINATE_BY.get("dependency", 100)
    prefetch_related = ["for_package", "datafile_resource"]
    table_columns = [
        "package_url",
        {
            "field_name": "type",
            "label": "Package type",
            "filter_fieldname": "type",
        },
        "extracted_requirement",
        {
            "field_name": "scope",
            "filter_fieldname": "scope",
        },
        {
            "field_name": "is_runtime",
            "filter_fieldname": "is_runtime",
        },
        {
            "field_name": "is_optional",
            "filter_fieldname": "is_optional",
        },
        {
            "field_name": "is_resolved",
            "filter_fieldname": "is_resolved",
        },
        "for_package",
        "datafile_resource",
        {
            "field_name": "datasource_id",
            "filter_fieldname": "datasource_id",
            "filter_is_right": True,
        },
    ]


class ProjectErrorListView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    TableColumnsMixin,
    ExportXLSXMixin,
    FilterView,
):
    model = ProjectError
    filterset_class = ErrorFilterSet
    template_name = "scanpipe/error_list.html"
    paginate_by = settings.SCANCODEIO_PAGINATE_BY.get("error", 50)
    table_columns = [
        "model",
        "message",
        "details",
        "traceback",
    ]


RelationRow = namedtuple(
    "RelationRow",
    field_names=["to_resource", "status", "map_type", "score", "from_resource"],
)


class CodebaseRelationListView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    TableColumnsMixin,
    ExportXLSXMixin,
    PaginatedFilterView,
):
    model = CodebaseResource
    filterset_class = ResourceFilterSet
    template_name = "scanpipe/relation_list.html"
    paginate_by = settings.SCANCODEIO_PAGINATE_BY.get("relation", 100)
    table_columns = [
        {
            "field_name": "path",
            "label": "To resource",
        },
        {
            "field_name": "status",
            "filter_fieldname": "status",
        },
        {
            "field_name": "related_from__map_type",
            "label": "Map type",
            "filter_fieldname": "relation_map_type",
        },
        {
            "field_name": "related_from__from_resource__path",
            "label": "From resource",
        },
    ]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .files()
            .to_codebase()
            .prefetch_related("related_from__from_resource__project")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["relation_count"] = context["filter"].qs.has_relation().count()
        return context

    @staticmethod
    def get_rows(qs):
        for resource in qs:
            relations = resource.related_from.all()
            if not relations:
                yield RelationRow(resource.path, resource.status, "", "", "")
            else:
                for relation in resource.related_from.all():
                    score = relation.extra_data.get("path_score", "")
                    if diff_ratio := relation.extra_data.get("diff_ratio", ""):
                        score += f" diff_ratio: {diff_ratio}"
                    yield RelationRow(
                        resource.path,
                        resource.status,
                        relation.map_type,
                        score,
                        relation.from_resource.path,
                    )

    def export_xlsx_file_response(self):
        filtered_qs = self.filterset.qs
        output_file = io.BytesIO()

        with xlsxwriter.Workbook(output_file) as workbook:
            output._add_xlsx_worksheet(
                workbook=workbook,
                worksheet_name="RELATIONS",
                rows=self.get_rows(qs=filtered_qs),
                fields=RelationRow._fields,
            )

        filename = f"{self.project.name}_{self.model._meta.model_name}.xlsx"
        output_file.seek(0)
        return FileResponse(output_file, as_attachment=True, filename=filename)


class CodebaseResourceDetailsView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    PrefetchRelatedViewMixin,
    TabSetMixin,
    generic.DetailView,
):
    model = CodebaseResource
    model_label = "resources"
    slug_field = "path"
    slug_url_kwarg = "path"
    template_name = "scanpipe/resource_detail.html"
    annotation_types = {
        CodebaseResource.Compliance.OK: "ok",
        CodebaseResource.Compliance.WARNING: "warning",
        CodebaseResource.Compliance.ERROR: "error",
        CodebaseResource.Compliance.MISSING: "missing",
        "": "ok",
        None: "info",
    }
    prefetch_related = [
        "discovered_packages",
        "related_from__from_resource__project",
        "related_to__to_resource__project",
    ]
    tabset = {
        "essentials": {
            "fields": [
                "path",
                "status",
                "type",
                "name",
                "extension",
                "programming_language",
                "mime_type",
                "file_type",
                "tag",
                "rootfs_path",
            ],
            "icon_class": "fa-solid fa-info-circle",
        },
        "others": {
            "fields": [
                {"field_name": "size", "render_func": filesizeformat},
                "md5",
                "sha1",
                "sha256",
                "sha512",
                "is_binary",
                "is_text",
                "is_archive",
                "is_key_file",
                "is_media",
            ],
            "icon_class": "fa-solid fa-plus-square",
        },
        "viewer": {
            "icon_class": "fa-solid fa-file-code",
            "template": "scanpipe/tabset/tab_content_viewer.html",
            "disable_condition": do_not_disable,
        },
        "image": {
            "icon_class": "fa-solid fa-image",
            "template": "scanpipe/tabset/tab_image.html",
            "disable_condition": do_not_disable,
            "display_condition": is_displayable_image_type,
        },
        "detection": {
            "fields": [
                "detected_license_expression",
                {
                    "field_name": "detected_license_expression_spdx",
                    "label": "Detected license expression (SPDX)",
                },
                {"field_name": "license_detections", "render_func": render_as_yaml},
                {"field_name": "license_clues", "render_func": render_as_yaml},
                "percentage_of_license_text",
                {"field_name": "copyrights", "render_func": render_as_yaml},
                {"field_name": "holders", "render_func": render_as_yaml},
                {"field_name": "authors", "render_func": render_as_yaml},
                {"field_name": "emails", "render_func": render_as_yaml},
                {"field_name": "urls", "render_func": render_as_yaml},
            ],
            "icon_class": "fa-solid fa-search",
        },
        "packages": {
            "fields": ["discovered_packages"],
            "icon_class": "fa-solid fa-layer-group",
            "template": "scanpipe/tabset/tab_packages.html",
        },
        "relations": {
            "fields": ["related_from", "related_to"],
            "icon_class": "fa-solid fa-link",
            "template": "scanpipe/tabset/tab_relations.html",
        },
        "extra_data": {
            "fields": [
                {"field_name": "extra_data", "render_func": render_as_yaml},
            ],
            "verbose_name": "Extra",
            "icon_class": "fa-solid fa-database",
        },
    }

    @staticmethod
    def get_annotations(entries, value_key):
        annotations = []
        annotation_type = "info"

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            annotations.append(
                {
                    "start_line": entry.get("start_line"),
                    "end_line": entry.get("end_line"),
                    "text": entry.get(value_key),
                    "className": f"ace_{annotation_type}",
                }
            )

        return annotations

    def get_license_annotations(self, field_name):
        annotations = []

        for entry in getattr(self.object, field_name):
            matches = entry.get("matches", [])
            annotations.extend(self.get_annotations(matches, "license_expression"))

        return annotations

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource = self.object

        try:
            context["file_content"] = resource.file_content
        except OSError:
            context["missing_file_content"] = True
            message = "WARNING: This resource is not available on disk."
            messages.warning(self.request, message)

        license_annotations = self.get_license_annotations("license_detections")
        context["detected_values"] = {
            "licenses": license_annotations,
        }

        fields = [
            ("copyrights", "copyright"),
            ("holders", "holder"),
            ("authors", "author"),
            ("emails", "email"),
            ("urls", "url"),
        ]
        for field_name, value_key in fields:
            annotations = self.get_annotations(getattr(resource, field_name), value_key)
            context["detected_values"][field_name] = annotations

        return context


@conditional_login_required
def codebase_resource_diff_view(request, slug):
    project = get_object_or_404(Project, slug=slug)

    project_files = project.codebaseresources.files()
    from_path = request.GET.get("from_path")
    to_path = request.GET.get("to_path")
    from_resource = get_object_or_404(project_files, path=from_path)
    to_resource = get_object_or_404(project_files, path=to_path)

    if not (from_resource.is_text and to_resource.is_text):
        raise Http404("Cannot diff on binary files")

    from_lines = from_resource.location_path.read_text().splitlines()
    to_lines = to_resource.location_path.read_text().splitlines()
    html = difflib.HtmlDiff().make_file(from_lines, to_lines)

    return HttpResponse(html)


class DiscoveredPackageDetailsView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    TabSetMixin,
    PrefetchRelatedViewMixin,
    generic.DetailView,
):
    model = DiscoveredPackage
    model_label = "packages"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "scanpipe/package_detail.html"
    prefetch_related = ["codebase_resources__project", "dependencies__project"]
    tabset = {
        "essentials": {
            "fields": [
                "package_url",
                "declared_license_expression",
                {
                    "field_name": "declared_license_expression_spdx",
                    "label": "Declared license expression (SPDX)",
                },
                "primary_language",
                "homepage_url",
                "download_url",
                "bug_tracking_url",
                "code_view_url",
                "vcs_url",
                "api_data_url",
                "repository_homepage_url",
                "repository_download_url",
                "source_packages",
                "keywords",
                "description",
            ],
            "icon_class": "fa-solid fa-info-circle",
        },
        "others": {
            "fields": [
                {"field_name": "size", "render_func": filesizeformat},
                "release_date",
                "md5",
                "sha1",
                "sha256",
                "sha512",
                "datasource_id",
                "file_references",
                {"field_name": "parties", "render_func": render_as_yaml},
                "missing_resources",
                "modified_resources",
                "package_uid",
            ],
            "icon_class": "fa-solid fa-plus-square",
        },
        "terms": {
            "fields": [
                "declared_license_expression",
                {
                    "field_name": "declared_license_expression_spdx",
                    "label": "Declared license expression (SPDX)",
                },
                "other_license_expression",
                {
                    "field_name": "other_license_expression_spdx",
                    "label": "Other license expression (SPDX)",
                },
                "extracted_license_statement",
                "copyright",
                "holder",
                "notice_text",
                {"field_name": "license_detections", "render_func": render_as_yaml},
                {
                    "field_name": "other_license_detections",
                    "render_func": render_as_yaml,
                },
            ],
            "icon_class": "fa-solid fa-file-contract",
        },
        "resources": {
            "fields": ["codebase_resources"],
            "icon_class": "fa-solid fa-folder-open",
            "template": "scanpipe/tabset/tab_resources.html",
        },
        "dependencies": {
            "fields": ["dependencies"],
            "icon_class": "fa-solid fa-layer-group",
            "template": "scanpipe/tabset/tab_dependencies.html",
        },
        "vulnerabilities": {
            "fields": ["affected_by_vulnerabilities"],
            "icon_class": "fa-solid fa-bug",
            "template": "scanpipe/tabset/tab_vulnerabilities.html",
        },
        "extra_data": {
            "fields": [
                {"field_name": "extra_data", "render_func": render_as_yaml},
            ],
            "verbose_name": "Extra",
            "icon_class": "fa-solid fa-database",
        },
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vulnerablecode_url"] = settings.VULNERABLECODE_URL
        return context


class DiscoveredDependencyDetailsView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    TabSetMixin,
    PrefetchRelatedViewMixin,
    generic.DetailView,
):
    model = DiscoveredDependency
    model_label = "dependencies"
    slug_field = "dependency_uid"
    slug_url_kwarg = "dependency_uid"
    template_name = "scanpipe/dependency_detail.html"
    prefetch_related = ["for_package", "datafile_resource"]
    tabset = {
        "essentials": {
            "fields": [
                "package_url",
                {
                    "field_name": "for_package",
                    "template": "scanpipe/tabset/field_for_package.html",
                },
                {
                    "field_name": "datafile_resource",
                    "template": "scanpipe/tabset/field_datafile_resource.html",
                },
                "package_type",
                "extracted_requirement",
                "scope",
                "datasource_id",
            ],
            "icon_class": "fa-solid fa-info-circle",
        },
        "others": {
            "fields": [
                "dependency_uid",
                "for_package_uid",
                "is_runtime",
                "is_optional",
                "is_resolved",
            ],
            "icon_class": "fa-solid fa-plus-square",
        },
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dependency_data"] = DiscoveredDependencySerializer(self.object).data
        return context


@conditional_login_required
def run_detail_view(request, uuid):
    template = "scanpipe/includes/run_modal_content.html"
    run_qs = Run.objects.select_related("project").prefetch_related(
        "project__webhooksubscriptions",
    )
    run = get_object_or_404(run_qs, uuid=uuid)
    project = run.project

    context = {
        "run": run,
        "project": project,
        "webhook_subscriptions": project.webhooksubscriptions.all(),
    }

    return render(request, template, context)


@conditional_login_required
def run_status_view(request, uuid):
    template = "scanpipe/includes/run_status_tag.html"
    run = get_object_or_404(Run, uuid=uuid)
    context = {"run": run}

    current_status = request.GET.get("current_status")
    if current_status and current_status != run.status:
        context["status_changed"] = True

    context["display_current_step"] = request.GET.get("display_current_step")

    return render(request, template, context)


class CodebaseResourceRawView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    generic.detail.SingleObjectMixin,
    generic.base.View,
):
    model = CodebaseResource
    slug_field = "path"
    slug_url_kwarg = "path"

    def get(self, request, *args, **kwargs):
        resource = self.get_object()
        resource_location_path = resource.location_path

        if resource_location_path.is_file():
            return FileResponse(
                resource_location_path.open("rb"),
                as_attachment=request.GET.get("as_attachment", False),
            )

        raise Http404

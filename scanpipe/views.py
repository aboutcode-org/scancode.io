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
from collections import Counter
from contextlib import suppress

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

import saneyaml
from django_filters.views import FilterView

from scancodeio.auth import ConditionalLoginRequired
from scancodeio.auth import conditional_login_required
from scanpipe.api.serializers import DiscoveredDependencySerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.filters import DependencyFilterSet
from scanpipe.filters import ErrorFilterSet
from scanpipe.filters import PackageFilterSet
from scanpipe.filters import ProjectFilterSet
from scanpipe.filters import ResourceFilterSet
from scanpipe.forms import AddInputsForm
from scanpipe.forms import AddPipelineForm
from scanpipe.forms import ArchiveProjectForm
from scanpipe.forms import ProjectForm
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.models import RunInProgressError
from scanpipe.pipes import codebase
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


class ProjectViewMixin:
    model = Project
    slug_url_kwarg = "uuid"
    slug_field = "uuid"


class PaginatedFilterView(FilterView):
    """
    Adds a `url_params_without_page` value in the template context to include the
    current filtering in the pagination.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query_dict = self.request.GET.copy()
        query_dict.pop("page", None)
        context["url_params_without_page"] = query_dict.urlencode()

        return context


class AccountProfileView(LoginRequiredMixin, generic.TemplateView):
    template_name = "account/profile.html"


class ProjectListView(
    ConditionalLoginRequired, PrefetchRelatedViewMixin, PaginatedFilterView
):
    model = Project
    filterset_class = ProjectFilterSet
    template_name = "scanpipe/project_list.html"
    prefetch_related = ["runs"]
    paginate_by = 20


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
        return reverse_lazy("project_detail", kwargs={"uuid": self.object.pk})


class ProjectDetailView(ConditionalLoginRequired, ProjectViewMixin, generic.DetailView):
    template_name = "scanpipe/project_detail.html"

    @staticmethod
    def get_summary(values_list, limit=7):
        most_common = dict(Counter(values_list).most_common(limit))

        other = len(values_list) - sum(most_common.values())
        if other > 0:
            most_common["Other"] = other

        # Set a label for empty string value and move to last entry in the dict
        if "" in most_common:
            most_common["(No value detected)"] = most_common.pop("")

        return most_common

    @staticmethod
    def data_from_model_field(queryset, model_field, data_field):
        results = []
        for model_values in queryset.values_list(model_field, flat=True):
            if not model_values:
                results.append("")
            else:
                results.extend(entry.get(data_field) for entry in model_values)
        return results

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        files_qs = project.codebaseresources.files()

        file_filter = self.request.GET.get("file-filter", "all")
        if file_filter == "in-a-package":
            files_qs = files_qs.in_package()
        elif file_filter == "not-in-a-package":
            files_qs = files_qs.not_in_package()

        files = files_qs.only(
            "programming_language",
            "mime_type",
            "holders",
            "copyrights",
            "license_expressions",
        )
        packages = project.discoveredpackages.all().only(
            "type",
            "license_expression",
        )
        dependencies = project.discovereddependencys.all().only(
            "is_runtime",
            "is_optional",
            "is_resolved",
        )

        file_languages = files.values_list("programming_language", flat=True)
        file_mime_types = files.values_list("mime_type", flat=True)
        file_holders = self.data_from_model_field(files, "holders", "value")
        file_copyrights = self.data_from_model_field(files, "copyrights", "value")
        file_license_keys = self.data_from_model_field(files, "licenses", "key")
        file_license_categories = self.data_from_model_field(
            files, "licenses", "category"
        )

        file_compliance_alert = []
        if scanpipe_app.policies_enabled:
            file_compliance_alert = files.values_list("compliance_alert", flat=True)

        package_licenses = packages.values_list("license_expression", flat=True)
        package_types = packages.values_list("type", flat=True)

        dependency_is_runtime = dependencies.values_list("is_runtime", flat=True)
        dependency_is_optional = dependencies.values_list("is_optional", flat=True)
        dependency_is_resolved = dependencies.values_list("is_resolved", flat=True)

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

        context.update(
            {
                "inputs_with_source": inputs,
                "programming_languages": self.get_summary(file_languages),
                "mime_types": self.get_summary(file_mime_types),
                "holders": self.get_summary(file_holders),
                "copyrights": self.get_summary(file_copyrights),
                "file_license_keys": self.get_summary(file_license_keys),
                "file_license_categories": self.get_summary(file_license_categories),
                "file_compliance_alert": self.get_summary(file_compliance_alert),
                "package_licenses": self.get_summary(package_licenses),
                "package_types": self.get_summary(package_types),
                "dependency_is_runtime": self.get_summary(dependency_is_runtime),
                "dependency_is_optional": self.get_summary(dependency_is_optional),
                "dependency_is_resolved": self.get_summary(dependency_is_resolved),
                "file_filter": file_filter,
                "add_pipeline_form": AddPipelineForm(),
                "add_inputs_form": AddInputsForm(),
                "archive_form": ArchiveProjectForm(),
                "license_clarity": license_clarity,
                "scan_summary": scan_summary,
            }
        )

        if project.extra_data:
            context["extra_data_yaml"] = saneyaml.dump(project.extra_data, indent=2)

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


class ProjectArchiveView(
    ConditionalLoginRequired, ProjectViewMixin, SingleObjectMixin, FormView
):
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


class ProjectDeleteView(ConditionalLoginRequired, ProjectViewMixin, generic.DeleteView):
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


class ProjectResetView(ConditionalLoginRequired, ProjectViewMixin, generic.DeleteView):
    success_message = 'All data, except inputs, for the "{}" project have been removed.'

    def form_valid(self, form):
        """
        Call the reset() method on the project.
        """
        project = self.get_object()
        try:
            project.reset(keep_input=True)
        except RunInProgressError as error:
            messages.error(self.request, error)
        else:
            messages.success(self.request, self.success_message.format(project.name))

        return redirect(project)


class ProjectTreeView(ConditionalLoginRequired, ProjectViewMixin, generic.DetailView):
    template_name = "scanpipe/project_tree.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        fields = ["name", "path"]
        project_codebase = codebase.ProjectCodebase(self.object)
        context["tree_data"] = [codebase.get_tree(project_codebase.root, fields)]

        return context


@conditional_login_required
def execute_pipeline_view(request, uuid, run_uuid):
    project = get_object_or_404(Project, uuid=uuid)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status != run.Status.NOT_STARTED:
        raise Http404("Pipeline already queued, started or completed.")

    run.execute_task_async()
    messages.success(request, f"Pipeline {run.pipeline_name} run started.")
    return redirect(project)


@conditional_login_required
def stop_pipeline_view(request, uuid, run_uuid):
    project = get_object_or_404(Project, uuid=uuid)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status != run.Status.RUNNING:
        raise Http404("Pipeline is not running.")

    run.stop_task()
    messages.success(request, f"Pipeline {run.pipeline_name} stopped.")
    return redirect(project)


@conditional_login_required
def delete_pipeline_view(request, uuid, run_uuid):
    project = get_object_or_404(Project, uuid=uuid)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status not in [run.Status.NOT_STARTED, run.Status.QUEUED]:
        raise Http404("Only non started or queued pipelines can be deleted.")

    run.delete_task()
    messages.success(request, f"Pipeline {run.pipeline_name} deleted.")
    return redirect(project)


def project_results_json_response(project, as_attachment=False):
    """
    Returns the results as JSON compatible with ScanCode data format.
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
        response["Content-Disposition"] = f'attachment; filename="{project.name}.json"'

    return response


class ProjectResultsView(
    ConditionalLoginRequired, ProjectViewMixin, generic.DetailView
):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        project = self.object
        format = self.kwargs["format"]

        if format == "json":
            return project_results_json_response(project, as_attachment=True)

        elif format == "xlsx":
            output_file = output.to_xlsx(project)
            filename = f"{project.name}_{output_file.name}"
            return FileResponse(output_file.open("rb"), filename=filename)

        raise Http404("Format not supported.")


class ProjectRelatedViewMixin:
    def get_project(self):
        if not getattr(self, "project", None):
            project_uuid = self.kwargs["uuid"]
            self.project = get_object_or_404(Project, uuid=project_uuid)
        return self.project

    def get_queryset(self):
        return super().get_queryset().project(self.get_project())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context


class CodebaseResourceListView(
    ConditionalLoginRequired,
    PrefetchRelatedViewMixin,
    ProjectRelatedViewMixin,
    PaginatedFilterView,
):
    model = CodebaseResource
    filterset_class = ResourceFilterSet
    template_name = "scanpipe/resource_list.html"
    paginate_by = 100
    prefetch_related = ["discovered_packages"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query_dict = self.request.GET.copy()
        query_dict.pop("page", None)
        context["url_params_without_page"] = query_dict.urlencode()

        context["include_compliance_alert"] = scanpipe_app.policies_enabled
        return context


class DiscoveredPackageListView(
    ConditionalLoginRequired,
    PrefetchRelatedViewMixin,
    ProjectRelatedViewMixin,
    PaginatedFilterView,
):
    model = DiscoveredPackage
    filterset_class = PackageFilterSet
    template_name = "scanpipe/package_list.html"
    paginate_by = 100
    prefetch_related = ["codebase_resources"]


class DiscoveredDependencyListView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    PaginatedFilterView,
):
    model = DiscoveredDependency
    filterset_class = DependencyFilterSet
    template_name = "scanpipe/dependency_list.html"
    paginate_by = 100
    prefetch_related = ["discovered_packages"]


class ProjectErrorListView(
    ConditionalLoginRequired, ProjectRelatedViewMixin, FilterView
):
    model = ProjectError
    filterset_class = ErrorFilterSet
    template_name = "scanpipe/error_list.html"
    paginate_by = 50


class CodebaseResourceDetailsView(
    ConditionalLoginRequired, ProjectRelatedViewMixin, generic.DetailView
):
    model = CodebaseResource
    template_name = "scanpipe/resource_detail.html"

    @staticmethod
    def get_annotation_text(entry, field_name, value_key):
        """
        A workaround to get the license_expression until the data structure is
        updated on the ScanCode-toolkit side.
        https://github.com/nexB/scancode-results-analyzer/blob/6c132bc20153d5c96929c
        f378bd0f06d83db9005/src/results_analyze/analyzer_plugin.py#L131-L198
        """
        if field_name == "licenses":
            return entry.get("matched_rule", {}).get("license_expression")
        return entry.get(value_key)

    def get_annotations(self, field_name, value_key="value"):
        annotations = []

        for entry in getattr(self.object, field_name):
            annotation_type = "info"

            # Customize the annotation icon based on the policy compliance_alert
            policy = entry.get("policy")
            if policy:
                annotation_type = policy.get("compliance_alert")

            annotations.append(
                {
                    "start_line": entry.get("start_line"),
                    "end_line": entry.get("end_line"),
                    "text": self.get_annotation_text(entry, field_name, value_key),
                    "type": annotation_type,
                }
            )

        return annotations

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            context["file_content"] = self.object.file_content
        except OSError:
            raise Http404("File not found.")

        context["detected_values"] = {
            "licenses": self.get_annotations("licenses"),
            "copyrights": self.get_annotations("copyrights"),
            "holders": self.get_annotations("holders"),
            "authors": self.get_annotations("authors"),
            "emails": self.get_annotations("emails", value_key="email"),
            "urls": self.get_annotations("urls", value_key="url"),
        }

        return context


class DiscoveredPackageDetailsView(
    ConditionalLoginRequired, ProjectRelatedViewMixin, generic.DetailView
):
    model = DiscoveredPackage
    template_name = "scanpipe/package_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["package_data"] = DiscoveredPackageSerializer(self.object).data
        return context


class DiscoveredDependencyDetailsView(
    ConditionalLoginRequired, ProjectRelatedViewMixin, generic.DetailView
):
    model = DiscoveredDependency
    template_name = "scanpipe/dependency_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dependency_data"] = DiscoveredDependencySerializer(self.object).data
        return context


@conditional_login_required
def run_detail_view(request, uuid):
    template = "scanpipe/includes/run_modal_content.html"
    run = get_object_or_404(Run, uuid=uuid)
    status_summary = count_group_by(run.project.codebaseresources, "status")

    context = {
        "run": run,
        "status_summary": status_summary,
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

    return render(request, template, context)


class CodebaseResourceRawView(
    ConditionalLoginRequired,
    ProjectRelatedViewMixin,
    generic.detail.SingleObjectMixin,
    generic.base.View,
):
    model = CodebaseResource

    def get(self, request, *args, **kwargs):
        resource = self.get_object()
        resource_location_path = resource.location_path

        if resource_location_path.is_file():
            return FileResponse(
                resource_location_path.open("rb"),
                as_attachment=request.GET.get("as_attachment", False),
            )

        raise Http404

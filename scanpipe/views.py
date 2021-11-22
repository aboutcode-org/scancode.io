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

from collections import Counter

from django.apps import apps
from django.contrib import messages
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

from scanpipe.filters import ErrorFilterSet
from scanpipe.filters import PackageFilterSet
from scanpipe.filters import ProjectFilterSet
from scanpipe.filters import ResourceFilterSet
from scanpipe.forms import AddInputsForm
from scanpipe.forms import AddPipelineForm
from scanpipe.forms import ArchiveProjectForm
from scanpipe.forms import ProjectForm
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.models import RunInProgressError
from scanpipe.pipes import codebase
from scanpipe.pipes import count_group_by
from scanpipe.pipes import output

scanpipe_app = apps.get_app_config("scanpipe")


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


class ProjectListView(PrefetchRelatedViewMixin, PaginatedFilterView):
    model = Project
    filterset_class = ProjectFilterSet
    template_name = "scanpipe/project_list.html"
    prefetch_related = ["runs"]
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_count"] = Project.objects.filter(is_archived=False).count()
        context["archived_count"] = Project.objects.filter(is_archived=True).count()
        return context


class ProjectCreateView(generic.CreateView):
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


class ProjectDetailView(ProjectViewMixin, generic.DetailView):
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
                "file_filter": file_filter,
                "add_pipeline_form": AddPipelineForm(),
                "add_inputs_form": AddInputsForm(),
                "archive_form": ArchiveProjectForm(),
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


class ProjectArchiveView(ProjectViewMixin, SingleObjectMixin, FormView):
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


class ProjectDeleteView(ProjectViewMixin, generic.DeleteView):
    success_url = reverse_lazy("project_list")
    success_message = 'The project "{}" and all its related data have been removed.'

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        try:
            response_redirect = super().delete(request, *args, **kwargs)
        except RunInProgressError as error:
            messages.error(self.request, error)
            return redirect(project)

        messages.success(self.request, self.success_message.format(project.name))
        return response_redirect


class ProjectResetView(ProjectViewMixin, generic.DeleteView):
    success_message = 'All data, except inputs, for the "{}" project have been removed.'

    def delete(self, request, *args, **kwargs):
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


class ProjectTreeView(ProjectViewMixin, generic.DetailView):
    template_name = "scanpipe/project_tree.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        fields = ["name", "path"]
        project_codebase = codebase.ProjectCodebase(self.object)
        context["tree_data"] = [codebase.get_tree(project_codebase.root, fields)]

        return context


def execute_pipeline_view(request, uuid, run_uuid):
    project = get_object_or_404(Project, uuid=uuid)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status != run.Status.NOT_STARTED:
        raise Http404("Pipeline already queued, started or completed.")

    run.execute_task_async()
    messages.success(request, f"Pipeline {run.pipeline_name} run started.")
    return redirect(project)


def stop_pipeline_view(request, uuid, run_uuid):
    project = get_object_or_404(Project, uuid=uuid)
    run = get_object_or_404(Run, uuid=run_uuid, project=project)

    if run.status != run.Status.RUNNING:
        raise Http404("Pipeline is not running.")

    run.stop_task()
    messages.success(request, f"Pipeline {run.pipeline_name} stopped.")
    return redirect(project)


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


class ProjectResultsView(ProjectViewMixin, generic.DetailView):
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
    PrefetchRelatedViewMixin,
    ProjectRelatedViewMixin,
    PaginatedFilterView,
):
    model = DiscoveredPackage
    filterset_class = PackageFilterSet
    template_name = "scanpipe/package_list.html"
    paginate_by = 100
    prefetch_related = ["codebase_resources"]


class ProjectErrorListView(ProjectRelatedViewMixin, FilterView):
    model = ProjectError
    filterset_class = ErrorFilterSet
    template_name = "scanpipe/error_list.html"
    paginate_by = 50


class CodebaseResourceDetailsView(ProjectRelatedViewMixin, generic.DetailView):
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


def run_detail_view(request, uuid):
    template = "scanpipe/includes/run_modal_content.html"
    run = get_object_or_404(Run, uuid=uuid)
    status_summary = count_group_by(run.project.codebaseresources, "status")

    context = {
        "run": run,
        "status_summary": status_summary,
    }

    return render(request, template, context)


class CodebaseResourceRawView(
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

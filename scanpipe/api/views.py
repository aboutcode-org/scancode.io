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

import json

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse

import django_filters
from rest_framework import mixins
from rest_framework import renderers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from scanpipe.api.serializers import CodebaseRelationSerializer
from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredDependencySerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import PipelineSerializer
from scanpipe.api.serializers import ProjectMessageSerializer
from scanpipe.api.serializers import ProjectSerializer
from scanpipe.api.serializers import RunSerializer
from scanpipe.filters import DependencyFilterSet
from scanpipe.filters import PackageFilterSet
from scanpipe.filters import ProjectMessageFilterSet
from scanpipe.filters import RelationFilterSet
from scanpipe.filters import ResourceFilterSet
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.models import RunInProgressError
from scanpipe.pipes import output
from scanpipe.pipes.compliance import get_project_compliance_alerts
from scanpipe.views import project_results_json_response

scanpipe_app = apps.get_app_config("scanpipe")


class ProjectFilterSet(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter()
    name__contains = django_filters.CharFilter(
        field_name="name",
        lookup_expr="contains",
    )
    name__startswith = django_filters.CharFilter(
        field_name="name",
        lookup_expr="startswith",
    )
    name__endswith = django_filters.CharFilter(
        field_name="name",
        lookup_expr="endswith",
    )
    names = django_filters.filters.CharFilter(
        label="Names (multi-values)",
        field_name="name",
        method="filter_names",
    )
    uuid = django_filters.CharFilter()

    class Meta:
        model = Project
        fields = [
            "name",
            "name__contains",
            "name__startswith",
            "name__endswith",
            "names",
            "uuid",
            "is_archived",
        ]

    def filter_names(self, qs, name, value):
        names = value.split(",")

        lookups = Q()
        for name in names:
            name = name.strip()
            if name:
                lookups |= Q(name__contains=name)

        return qs.filter(lookups)


class ProjectViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides the ability to list, get, create, and destroy projects.
    Multiple actions are available to manage project instances.
    """

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filterset_class = ProjectFilterSet

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "labels",
                "runs",
                "inputsources",
            )
        )

    @action(detail=True, renderer_classes=[renderers.JSONRenderer])
    def results(self, request, *args, **kwargs):
        """
        Return the results compatible with ScanCode data format.
        The content is returned as a stream of JSON content using the
        JSONResultsGenerator class.
        """
        return project_results_json_response(self.get_object())

    @action(detail=True, name="Results (download)")
    def results_download(self, request, *args, **kwargs):
        """Return the results in the provided `output_format` as an attachment."""
        project = self.get_object()
        format = request.query_params.get("output_format", "json")
        version = request.query_params.get("version")
        output_kwargs = {}

        if format == "json":
            return project_results_json_response(project, as_attachment=True)
        elif format == "xlsx":
            output_file = output.to_xlsx(project)
        elif format == "spdx":
            output_file = output.to_spdx(project)
        elif format == "cyclonedx":
            if version:
                output_kwargs["version"] = version
            output_file = output.to_cyclonedx(project, **output_kwargs)
        elif format == "attribution":
            output_file = output.to_attribution(project)
        else:
            message = {"status": f"Format {format} not supported."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        filename = output.safe_filename(f"scancodeio_{project.name}_{output_file.name}")
        return FileResponse(
            output_file.open("rb"),
            filename=filename,
            as_attachment=True,
        )

    @action(detail=True)
    def summary(self, request, *args, **kwargs):
        """
        Return a summary of the results from the latest summary file found in the
        project's `output` directory.
        """
        project = self.get_object()
        summary_file = project.get_latest_output(filename="summary")

        if not summary_file:
            message = {"error": "Summary file not available"}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        summary_json = json.loads(summary_file.read_text())
        return Response(summary_json)

    @action(detail=False)
    def pipelines(self, request, *args, **kwargs):
        pipeline_data = [
            {"name": name, **pipeline_class.get_info()}
            for name, pipeline_class in scanpipe_app.pipelines.items()
        ]
        return Response(pipeline_data)

    def get_filtered_response(
        self, request, queryset, filterset_class, serializer_class
    ):
        """
        Handle filtering, pagination, and serialization of a "detail" action.
        This requires to set filterset_class=None in the @action decorator parameter
        to bypass the Project filterset.
        """
        filterset = filterset_class(data=request.GET, queryset=queryset)
        if not filterset.is_valid():
            message = {"errors": filterset.errors}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        queryset = filterset.qs
        paginated_qs = self.paginate_queryset(queryset)
        serializer = serializer_class(paginated_qs, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, filterset_class=None)
    def resources(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.codebaseresources.prefetch_related("discovered_packages")
        return self.get_filtered_response(
            request, queryset, ResourceFilterSet, CodebaseResourceSerializer
        )

    @action(detail=True, filterset_class=None)
    def packages(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.discoveredpackages.all()
        return self.get_filtered_response(
            request, queryset, PackageFilterSet, DiscoveredPackageSerializer
        )

    @action(detail=True, filterset_class=None)
    def dependencies(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.discovereddependencies.prefetch_for_serializer()
        return self.get_filtered_response(
            request, queryset, DependencyFilterSet, DiscoveredDependencySerializer
        )

    @action(detail=True, filterset_class=None)
    def relations(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.codebaserelations.select_related(
            "from_resource", "to_resource"
        )
        return self.get_filtered_response(
            request, queryset, RelationFilterSet, CodebaseRelationSerializer
        )

    @action(detail=True, filterset_class=None)
    def messages(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.projectmessages.all()
        return self.get_filtered_response(
            request, queryset, ProjectMessageFilterSet, ProjectMessageSerializer
        )

    @action(detail=True, methods=["get"])
    def file_content(self, request, *args, **kwargs):
        project = self.get_object()
        path = request.query_params.get("path")
        codebase_resources = project.codebaseresources.all()

        try:
            codebase_resource = codebase_resources.get(path=path)
        except ObjectDoesNotExist:
            message = {"status": "Resource not found. Use ?path=<resource_path>"}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_content = codebase_resource.file_content
        except OSError:
            message = {"status": "File not available"}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        return Response({"file_content": file_content})

    @action(detail=True, methods=["get", "post"], serializer_class=PipelineSerializer)
    def add_pipeline(self, request, *args, **kwargs):
        project = self.get_object()

        pipeline = request.data.get("pipeline")
        if pipeline:
            pipeline_name, groups = scanpipe_app.extract_group_from_pipeline(pipeline)
            pipeline_name = scanpipe_app.get_new_pipeline_name(pipeline_name)
            if pipeline_name in scanpipe_app.pipelines:
                execute_now = request.data.get("execute_now")
                project.add_pipeline(pipeline_name, execute_now, selected_groups=groups)
                return Response({"status": "Pipeline added."})

            message = {"status": f"{pipeline} is not a valid pipeline."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        message = {
            "status": "Pipeline required.",
            "pipelines": list(scanpipe_app.pipelines.keys()),
        }
        return Response(message, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get", "post"])
    def add_input(self, request, *args, **kwargs):
        project = self.get_object()

        if not project.can_change_inputs:
            message = {
                "status": "Cannot add inputs once a pipeline has started to execute."
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        upload_file = request.data.get("upload_file")
        upload_file_tag = request.data.get("upload_file_tag", "")
        input_urls = request.data.get("input_urls", [])

        if not (upload_file or input_urls):
            message = {"status": "upload_file or input_urls required."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        if upload_file:
            project.add_upload(upload_file, tag=upload_file_tag)

        # Add support for providing multiple URLs in a single string.
        if isinstance(input_urls, str):
            input_urls = input_urls.split()
        input_urls = [url for entry in input_urls for url in entry.split()]

        for url in input_urls:
            project.add_input_source(download_url=url)

        return Response({"status": "Input(s) added."})

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except RunInProgressError as error:
            return Response({"status": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get", "post"])
    def archive(self, request, *args, **kwargs):
        project = self.get_object()

        if self.request.method == "GET":
            message = (
                "POST on this URL to archive the project. "
                "You can choose to remove workspace directories by providing the "
                "following parameters: `remove_input=True`, `remove_codebase=True`, "
                "`remove_output=True`."
            )
            return Response({"status": message})

        try:
            project.archive(
                remove_input=request.data.get("remove_input"),
                remove_codebase=request.data.get("remove_codebase"),
                remove_output=request.data.get("remove_output"),
            )
        except RunInProgressError as error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"status": f"The project {project} has been archived."})

    @action(detail=True, methods=["get", "post"])
    def reset(self, request, *args, **kwargs):
        project = self.get_object()

        if self.request.method == "GET":
            message = "POST on this URL to reset the project."
            return Response({"status": message})

        try:
            project.reset(keep_input=True)
        except RunInProgressError as error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        else:
            message = (
                f"All data, except inputs, for the {project} project have been removed."
            )
            return Response({"status": message})

    @action(detail=True, methods=["get"])
    def outputs(self, request, *args, **kwargs):
        project = self.get_object()

        if filename := request.query_params.get("filename"):
            file_path = project.output_path / filename
            if file_path.exists():
                return FileResponse(file_path.open("rb"))

            message = {"status": f"Output file {filename} not found"}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        action_url = self.reverse_action(self.outputs.url_name, args=[project.pk])
        output_data = [
            {"filename": output, "download_url": f"{action_url}?filename={output}"}
            for output in project.output_root
        ]
        return Response(output_data)

    @action(detail=True, methods=["get"])
    def compliance(self, request, *args, **kwargs):
        """
        Retrieve compliance alerts for a project.

        This endpoint returns a list of compliance alerts for the given project,
        filtered by severity level. The severity level can be customized using the
        `fail_level` query parameter.

        Query Parameters:
        `fail_level`: Specifies the severity level of the alerts to be retrieved.
        Accepted values are: "ERROR", "WARNING", and "MISSING".
        Defaults to "ERROR" if not provided.

        Example:
          GET /api/projects/{project_id}/compliance/?fail_level=WARNING

        """
        project = self.get_object()
        fail_level = request.query_params.get("fail_level", "error")
        compliance_alerts = get_project_compliance_alerts(project, fail_level)
        return Response({"compliance_alerts": compliance_alerts})


class RunViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Add actions to the Run viewset."""

    queryset = Run.objects.all()
    serializer_class = RunSerializer

    @action(detail=True, methods=["post"])
    def start_pipeline(self, request, *args, **kwargs):
        run = self.get_object()
        if run.task_end_date:
            message = {"status": "Pipeline already executed."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
        elif run.task_start_date:
            message = {"status": "Pipeline already started."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
        elif run.task_id:
            message = {"status": "Pipeline already queued."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        transaction.on_commit(run.start)

        return Response({"status": f"Pipeline {run.pipeline_name} started."})

    @action(detail=True, methods=["post"])
    def stop_pipeline(self, request, *args, **kwargs):
        run = self.get_object()

        if run.status != run.Status.RUNNING:
            message = {"status": "Pipeline is not running."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        run.stop_task()
        return Response({"status": f"Pipeline {run.pipeline_name} stopped."})

    @action(detail=True, methods=["post"])
    def delete_pipeline(self, request, *args, **kwargs):
        run = self.get_object()

        if run.status not in [run.Status.NOT_STARTED, run.Status.QUEUED]:
            message = {"status": "Only non started or queued pipelines can be deleted."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        run.delete_task()
        return Response({"status": f"Pipeline {run.pipeline_name} deleted."})

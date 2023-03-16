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

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q

import django_filters
from rest_framework import mixins
from rest_framework import renderers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from scanpipe.api.serializers import CodebaseResourceSerializer
from scanpipe.api.serializers import DiscoveredDependencySerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import PipelineSerializer
from scanpipe.api.serializers import ProjectErrorSerializer
from scanpipe.api.serializers import ProjectSerializer
from scanpipe.api.serializers import RunSerializer
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.models import RunInProgressError
from scanpipe.pipes.fetch import fetch_urls
from scanpipe.views import project_results_json_response

scanpipe_app = apps.get_app_config("scanpipe")


class PassThroughRenderer(renderers.BaseRenderer):
    media_type = ""

    def render(self, data, **kwargs):
        return data


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

    @action(detail=True, renderer_classes=[renderers.JSONRenderer])
    def results(self, request, *args, **kwargs):
        """
        Return the results compatible with ScanCode data format.
        The content is returned as a stream of JSON content using the
        JSONResultsGenerator class.
        """
        return project_results_json_response(self.get_object())

    @action(
        detail=True, name="Results (download)", renderer_classes=[PassThroughRenderer]
    )
    def results_download(self, request, *args, **kwargs):
        """Return the results as an attachment."""
        return project_results_json_response(self.get_object(), as_attachment=True)

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

    @action(detail=True)
    def resources(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.codebaseresources.prefetch_related("discovered_packages")

        paginated_qs = self.paginate_queryset(queryset)
        serializer = CodebaseResourceSerializer(paginated_qs, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=True)
    def packages(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.discoveredpackages.all()

        paginated_qs = self.paginate_queryset(queryset)
        serializer = DiscoveredPackageSerializer(paginated_qs, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=True)
    def dependencies(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.discovereddependencies.all()

        paginated_qs = self.paginate_queryset(queryset)
        serializer = DiscoveredDependencySerializer(paginated_qs, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=True)
    def errors(self, request, *args, **kwargs):
        project = self.get_object()
        queryset = project.projecterrors.all()

        paginated_qs = self.paginate_queryset(queryset)
        serializer = ProjectErrorSerializer(paginated_qs, many=True)

        return self.get_paginated_response(serializer.data)

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
            if pipeline in scanpipe_app.pipelines:
                execute_now = request.data.get("execute_now")
                project.add_pipeline(pipeline, execute_now)
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

        if not project.can_add_input:
            message = {
                "status": "Cannot add inputs once a pipeline has started to execute."
            }
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        upload_file = request.data.get("upload_file")
        input_urls = request.data.get("input_urls", [])

        if not (upload_file or input_urls):
            message = {"status": "upload_file or input_urls required."}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        downloads, errors = fetch_urls(input_urls)
        if errors:
            message = {"status": ("Could not fetch: " + ", ".join(errors))}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        if upload_file:
            project.add_uploads([upload_file])

        if downloads:
            project.add_downloads(downloads)

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
            message = "POST on this URL to reset the project. " ""
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

        transaction.on_commit(run.execute_task_async)

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

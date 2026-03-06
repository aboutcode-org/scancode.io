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
import logging

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
from scanpipe.api.serializers import CodeOriginDeterminationSerializer
from scanpipe.api.serializers import DiscoveredDependencySerializer
from scanpipe.api.serializers import DiscoveredPackageSerializer
from scanpipe.api.serializers import InputSerializer
from scanpipe.api.serializers import PipelineSerializer
from scanpipe.api.serializers import ProjectArchiveSerializer
from scanpipe.api.serializers import ProjectMessageSerializer
from scanpipe.api.serializers import ProjectResetSerializer
from scanpipe.api.serializers import ProjectSerializer
from scanpipe.api.serializers import RunSerializer
from scanpipe.api.serializers import WebhookSubscriptionSerializer
from scanpipe.filters import DependencyFilterSet
from scanpipe.filters import PackageFilterSet
from scanpipe.filters import ProjectMessageFilterSet
from scanpipe.filters import RelationFilterSet
from scanpipe.filters import ResourceFilterSet
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.models import RunInProgressError
from scanpipe.models import CodeOriginDetermination
from scanpipe.models_curation import CurationSource
from scanpipe.models_curation import CurationConflict
from scanpipe.models_curation import CurationExport
from scanpipe.pipes import filename_now
from scanpipe.pipes import output
from scanpipe.pipes.compliance import get_project_compliance_alerts
from scanpipe.views import project_results_json_response
from scanpipe import curation_utils

logger = logging.getLogger(__name__)
scanpipe_app = apps.get_app_config("scanpipe")


class ErrorResponse(Response):
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
        # If message is already a dict, use it as-is
        if isinstance(message, dict):
            data = message
        else:
            # Otherwise, wrap string in {"status": message}
            data = {"status": message}

        super().__init__(data=data, status=status_code, **kwargs)


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
    label = django_filters.CharFilter(
        label="Label",
        field_name="labels__slug",
        distinct=True,
    )

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
            "label",
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
        if version:
            output_kwargs["version"] = version

        if format == "json":
            return project_results_json_response(project, as_attachment=True)
        elif format == "xlsx":
            output_file = output.to_xlsx(project)
        elif format == "spdx":
            output_file = output.to_spdx(project, **output_kwargs)
        elif format == "cyclonedx":
            output_file = output.to_cyclonedx(project, **output_kwargs)
        elif format == "attribution":
            output_file = output.to_attribution(project)
        elif format == "ort-package-list":
            output_file = output.to_ort_package_list_yml(project)
        elif format == "all_formats":
            output_file = output.to_all_formats(project)
        elif format == "all_outputs":
            output_file = output.to_all_outputs(project)
        else:
            return ErrorResponse(f"Format {format} not supported.")

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
            return ErrorResponse({"error": "Summary file not available"})

        summary_json = json.loads(summary_file.read_text())
        return Response(summary_json)

    @action(detail=False)
    def pipelines(self, request, *args, **kwargs):
        pipeline_data = [
            {"name": name, **pipeline_class.get_info()}
            for name, pipeline_class in scanpipe_app.pipelines.items()
        ]
        return Response(pipeline_data)

    @action(detail=False)
    def report(self, request, *args, **kwargs):
        project_qs = self.filter_queryset(self.get_queryset())

        model_choices = list(output.object_type_to_model_name.keys())
        model = request.GET.get("model")
        if not model:
            message = {
                "error": (
                    "Specifies the model to include in the XLSX report. "
                    "Using: ?model=MODEL"
                ),
                "choices": ", ".join(model_choices),
            }
            return ErrorResponse(message)

        if model not in model_choices:
            message = {
                "error": f"{model} is not on of the valid choices",
                "choices": ", ".join(model_choices),
            }
            return ErrorResponse(message)

        output_file = output.get_xlsx_report(
            project_qs=project_qs,
            model_short_name=model,
        )
        output_file.seek(0)
        return FileResponse(
            output_file,
            filename=f"scancodeio-report-{filename_now()}.xlsx",
            as_attachment=True,
        )

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
            return ErrorResponse({"errors": filterset.errors})

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
            return ErrorResponse("Resource not found. Use ?path=<resource_path>")

        try:
            file_content = codebase_resource.file_content
        except OSError:
            return ErrorResponse("File not available")

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
                return Response(
                    {"status": "Pipeline added."}, status=status.HTTP_201_CREATED
                )

            return ErrorResponse(f"{pipeline} is not a valid pipeline.")

        message = {
            "status": "Pipeline required.",
            "pipelines": list(scanpipe_app.pipelines.keys()),
        }
        return ErrorResponse(message)

    @action(detail=True, methods=["get", "post"], serializer_class=InputSerializer)
    def add_input(self, request, *args, **kwargs):
        project = self.get_object()

        if not project.can_change_inputs:
            return ErrorResponse(
                "Cannot add inputs once a pipeline has started to execute."
            )

        # Validate input using the action serializer
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(serializer.errors)

        # Extract validated data
        upload_file = serializer.validated_data.get("upload_file")
        upload_file_tag = serializer.validated_data.get("upload_file_tag", "")
        input_urls = serializer.validated_data.get("input_urls", [])

        if not (upload_file or input_urls):
            return ErrorResponse("upload_file or input_urls required.")

        if upload_file:
            project.add_upload(upload_file, tag=upload_file_tag)

        # Add support for providing multiple URLs in a single string.
        if isinstance(input_urls, str):
            input_urls = input_urls.split()
        input_urls = [url for entry in input_urls for url in entry.split()]

        for url in input_urls:
            project.add_input_source(download_url=url)

        return Response({"status": "Input(s) added."}, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        serializer_class=WebhookSubscriptionSerializer,
    )
    def add_webhook(self, request, *args, **kwargs):
        project = self.get_object()

        # Validate input using the action serializer
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(serializer.errors)

        project.add_webhook_subscription(**serializer.validated_data)
        return Response({"status": "Webhook added."}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except RunInProgressError:
            return ErrorResponse("Cannot delete project while a run is in progress.")

    @action(
        detail=True,
        methods=["get", "post"],
        serializer_class=ProjectArchiveSerializer,
    )
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

        # Validate input using the action serializer
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(serializer.errors)

        try:
            project.archive(**serializer.validated_data)
        except RunInProgressError:
            return ErrorResponse("Cannot archive project while a run is in progress.")

        return Response({"status": f"The project {project} has been archived."})

    @action(
        detail=True,
        methods=["get", "post"],
        serializer_class=ProjectResetSerializer,
    )
    def reset(self, request, *args, **kwargs):
        project = self.get_object()

        if self.request.method == "GET":
            message = "POST on this URL to reset the project."
            return Response({"status": message})

        # Validate input using the action serializer
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(serializer.errors)

        try:
            project.reset(**serializer.validated_data)
        except RunInProgressError:
            return ErrorResponse("Cannot reset project while a run is in progress.")

        return Response({"status": f"The {project} project has been reset."})

    @action(detail=True, methods=["get"])
    def outputs(self, request, *args, **kwargs):
        project = self.get_object()

        if filename := request.query_params.get("filename"):
            file_path = project.output_path / filename
            if file_path.exists():
                return FileResponse(file_path.open("rb"))

            return ErrorResponse(f"Output file {filename} not found")

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

    @action(detail=True, methods=["get"])
    def license_clarity_compliance(self, request, *args, **kwargs):
        """
        Retrieve the license clarity compliance alert for a project.

        This endpoint returns the license clarity compliance alert stored in the
        project's extra_data.

        Example:
          GET /api/projects/{project_id}/license_clarity_compliance/

        """
        project = self.get_object()
        clarity_alert = project.get_license_clarity_compliance_alert()
        return Response({"license_clarity_compliance_alert": clarity_alert})

    @action(detail=True, methods=["get"])
    def scorecard_compliance(self, request, *args, **kwargs):
        """
        Retrieve the scorecard compliance alert for a project.

        This endpoint returns the scorecard compliance alert stored in the
        project's extra_data.

        Example:
        GET /api/projects/{project_id}/scorecard_compliance/

        """
        project = self.get_object()
        scorecard_alert = project.get_scorecard_compliance_alert()
        return Response({"scorecard_compliance_alert": scorecard_alert})


class RunViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Add actions to the Run viewset."""

    queryset = Run.objects.all()
    serializer_class = RunSerializer

    @action(detail=True, methods=["post"])
    def start_pipeline(self, request, *args, **kwargs):
        run = self.get_object()
        if run.task_end_date:
            return ErrorResponse("Pipeline already executed.")
        elif run.task_start_date:
            return ErrorResponse("Pipeline already started.")
        elif run.task_id:
            return ErrorResponse("Pipeline already queued.")

        transaction.on_commit(run.start)

        return Response({"status": f"Pipeline {run.pipeline_name} started."})

    @action(detail=True, methods=["post"])
    def stop_pipeline(self, request, *args, **kwargs):
        run = self.get_object()

        if run.status != run.Status.RUNNING:
            return ErrorResponse("Pipeline is not running.")

        run.stop_task()
        return Response({"status": f"Pipeline {run.pipeline_name} stopped."})

    @action(detail=True, methods=["post"])
    def delete_pipeline(self, request, *args, **kwargs):
        run = self.get_object()

        if run.status not in [run.Status.NOT_STARTED, run.Status.QUEUED]:
            return ErrorResponse("Only non started or queued pipelines can be deleted.")

        run.delete_task()
        return Response({"status": f"Pipeline {run.pipeline_name} deleted."})


class CodeOriginDeterminationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for CodeOriginDetermination.
    Supports listing, retrieving, creating, and updating origin determinations.
    """

    queryset = CodeOriginDetermination.objects.select_related("codebase_resource")
    serializer_class = CodeOriginDeterminationSerializer

    def get_queryset(self):
        """Filter by project if project_slug is provided."""
        queryset = super().get_queryset()
        project_slug = self.request.query_params.get("project")
        if project_slug:
            queryset = queryset.filter(codebase_resource__project__slug=project_slug)
        return queryset

    @action(detail=False, methods=["post"])
    def bulk_update(self, request, *args, **kwargs):
        """
        Bulk update multiple origin determinations.
        Expects a list of objects with uuid and fields to update.
        """
        updates = request.data.get("updates", [])
        if not isinstance(updates, list):
            return ErrorResponse("'updates' must be a list")

        updated_count = 0
        errors = []

        for update_data in updates:
            uuid_str = update_data.get("uuid")
            if not uuid_str:
                errors.append({"error": "Missing uuid"})
                continue

            try:
                origin = CodeOriginDetermination.objects.get(uuid=uuid_str)
                serializer = self.get_serializer(origin, data=update_data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    updated_count += 1
                else:
                    errors.append({"uuid": uuid_str, "errors": serializer.errors})
            except CodeOriginDetermination.DoesNotExist:
                errors.append({"uuid": uuid_str, "error": "Not found"})

        return Response(
            {
                "updated_count": updated_count,
                "errors": errors,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_verify(self, request, *args, **kwargs):
        """
        Bulk verify multiple origin determinations.
        Expects a list of UUIDs.
        """
        uuids = request.data.get("uuids", [])
        if not isinstance(uuids, list):
            return ErrorResponse("'uuids' must be a list")

        updated = CodeOriginDetermination.objects.filter(uuid__in=uuids).update(
            is_verified=True
        )

        return Response({"updated_count": updated})

    @action(detail=False, methods=["post"])
    def propagate(self, request, *args, **kwargs):
        """
        Propagate origins for a project.
        Expects project slug and optional parameters.
        """
        from scanpipe import origin_utils
        from scanpipe.models import Project
        
        project_slug = request.data.get("project")
        if not project_slug:
            return ErrorResponse("'project' slug is required")
        
        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist:
            return ErrorResponse(f"Project '{project_slug}' not found")
        
        methods = request.data.get("methods", None)
        min_confidence = request.data.get("min_confidence", 0.8)
        max_targets = request.data.get("max_targets", 50)
        
        try:
            stats = origin_utils.propagate_origins_for_project(
                project,
                methods=methods,
                min_source_confidence=min_confidence,
                max_targets_per_source=max_targets,
            )
            
            return Response(stats)
        except Exception as e:
            return ErrorResponse(str(e))

    @action(detail=True, methods=["post"])
    def propagate_single(self, request, pk=None):
        """
        Propagate a single origin determination to related files.
        """
        from scanpipe import origin_utils
        
        origin = self.get_object()
        
        if not origin.can_be_propagation_source:
            return ErrorResponse(
                "This origin cannot be used as a propagation source. "
                "It must be verified, non-propagated, and have confidence >= 0.8"
            )
        
        methods = request.data.get("methods", ["package_membership", "path_pattern"])
        max_targets = request.data.get("max_targets", 50)
        
        propagated_origins = []
        
        try:
            if "package_membership" in methods:
                propagated = origin_utils.propagate_origin_by_package_membership(
                    origin, max_targets
                )
                propagated_origins.extend(propagated)
            
            if "path_pattern" in methods:
                propagated = origin_utils.propagate_origin_by_path_pattern(
                    origin, max_targets
                )
                propagated_origins.extend(propagated)
            
            if "license_similarity" in methods:
                propagated = origin_utils.propagate_origin_by_license_similarity(
                    origin, max_targets=max_targets
                )
                propagated_origins.extend(propagated)
            
            # Serialize the results
            serializer = self.get_serializer(propagated_origins, many=True)
            
            return Response({
                "propagated_count": len(propagated_origins),
                "propagated_origins": serializer.data,
            })
        except Exception as e:
            return ErrorResponse(str(e))

    @action(detail=False, methods=["post"])
    def export_curations(self, request, *args, **kwargs):
        """
        Export origin curations for a project to FederatedCode or a file.
        
        Expects:
        - project: Project slug (required)
        - destination: "federatedcode" or "file" (default: "federatedcode")
        - verified_only: bool (default: True)
        - include_propagated: bool (default: False)
        - curator_name: string (optional)
        - curator_email: string (optional)
        - format: "json" or "yaml" (for file destination, default: "json")
        """
        project_slug = request.data.get("project")
        if not project_slug:
            return ErrorResponse("'project' slug is required")
        
        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist:
            return ErrorResponse(f"Project '{project_slug}' not found")
        
        destination = request.data.get("destination", "federatedcode")
        verified_only = request.data.get("verified_only", True)
        include_propagated = request.data.get("include_propagated", False)
        curator_name = request.data.get("curator_name", "")
        curator_email = request.data.get("curator_email", "")
        
        try:
            if destination == "federatedcode":
                success, message = curation_utils.export_curations_to_federatedcode(
                    project=project,
                    curator_name=curator_name,
                    curator_email=curator_email,
                    verified_only=verified_only,
                    include_propagated=include_propagated,
                )
                
                if success:
                    return Response({"status": "success", "message": message})
                else:
                    return ErrorResponse(message)
            
            elif destination == "file":
                from pathlib import Path
                
                output_format = request.data.get("format", "json")
                output_path = project.project_work_directory / "curations" / f"origins.{output_format}"
                
                success, result = curation_utils.export_curations_to_file(
                    project=project,
                    output_path=Path(output_path),
                    format=output_format,
                    verified_only=verified_only,
                    include_propagated=include_propagated,
                    include_provenance=True,
                    curator_name=curator_name,
                    curator_email=curator_email,
                )
                
                if success:
                    return Response({
                        "status": "success",
                        "file_path": result,
                    })
                else:
                    return ErrorResponse(result)
            
            else:
                return ErrorResponse(
                    f"Invalid destination: {destination}. "
                    "Must be 'federatedcode' or 'file'"
                )
        
        except Exception as e:
            logger.error(f"Export error: {str(e)}", exc_info=True)
            return ErrorResponse(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def import_curations(self, request, *args, **kwargs):
        """
        Import origin curations from an external FederatedCode source.
        
        Expects:
        - project: Project slug (required)
        - source_url: URL to curation source (required)
        - source_name: Name for the source (optional)
        - conflict_strategy: Resolution strategy (default: "manual_review")
          Options: manual_review, keep_existing, use_imported, 
                   highest_confidence, highest_priority
        - dry_run: bool (default: False)
        """
        project_slug = request.data.get("project")
        if not project_slug:
            return ErrorResponse("'project' slug is required")
        
        source_url = request.data.get("source_url")
        if not source_url:
            return ErrorResponse("'source_url' is required")
        
        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist:
            return ErrorResponse(f"Project '{project_slug}' not found")
        
        source_name = request.data.get("source_name", "")
        conflict_strategy = request.data.get("conflict_strategy", "manual_review")
        dry_run = request.data.get("dry_run", False)
        
        # Validate conflict strategy
        valid_strategies = [
            "manual_review",
            "keep_existing",
            "use_imported",
            "highest_confidence",
            "highest_priority",
        ]
        if conflict_strategy not in valid_strategies:
            return ErrorResponse(
                f"Invalid conflict_strategy: {conflict_strategy}. "
                f"Valid options: {', '.join(valid_strategies)}"
            )
        
        try:
            success, stats = curation_utils.import_curations_from_url(
                project=project,
                source_url=source_url,
                source_name=source_name,
                conflict_strategy=conflict_strategy,
                dry_run=dry_run,
            )
            
            if success:
                return Response({
                    "status": "success",
                    "dry_run": dry_run,
                    "statistics": stats,
                })
            else:
                return ErrorResponse(stats)
        
        except Exception as e:
            logger.error(f"Import error: {str(e)}", exc_info=True)
            return ErrorResponse(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CurationSourceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing curation sources.
    
    Curation sources represent external origins of curations (e.g., other
    ScanCode.io instances, community repositories) and track synchronization status.
    """
    
    queryset = CurationSource.objects.all()
    
    from rest_framework import serializers
    
    class CurationSourceSerializer(serializers.ModelSerializer):
        class Meta:
            model = CurationSource
            fields = [
                "uuid",
                "name",
                "source_type",
                "url",
                "priority",
                "is_active",
                "auto_sync",
                "sync_frequency_hours",
                "last_sync_date",
                "sync_statistics",
                "metadata",
                "created_date",
                "updated_date",
            ]
            read_only_fields = ["uuid", "created_date", "updated_date", "last_sync_date", "sync_statistics"]
    
    serializer_class = CurationSourceSerializer
    
    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """
        Manually trigger synchronization for a curation source.
        
        This will import curations from the source into all active projects
        or a specified project.
        """
        source = self.get_object()
        project_slug = request.data.get("project")
        conflict_strategy = request.data.get("conflict_strategy", "manual_review")
        
        if not project_slug:
            return ErrorResponse("'project' slug is required for sync")
        
        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist:
            return ErrorResponse(f"Project '{project_slug}' not found")
        
        try:
            success, stats = curation_utils.import_curations_from_url(
                project=project,
                source_url=source.url,
                source_name=source.name,
                conflict_strategy=conflict_strategy,
                dry_run=False,
            )
            
            if success:
                source.mark_synced(stats)
                return Response({
                    "status": "success",
                    "statistics": stats,
                })
            else:
                return ErrorResponse(stats)
        
        except Exception as e:
            logger.error(f"Sync error: {str(e)}", exc_info=True)
            return ErrorResponse(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CurationConflictViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for viewing and resolving curation conflicts.
    
    Conflicts occur when importing curations that differ from existing ones.
    """
    
    queryset = CurationConflict.objects.select_related(
        "project",
        "existing_origin",
        "imported_source",
        "resolved_origin",
    )
    
    from rest_framework import serializers
    
    class CurationConflictSerializer(serializers.ModelSerializer):
        project_name = serializers.CharField(source="project.name", read_only=True)
        existing_origin_type = serializers.CharField(
            source="existing_origin.effective_origin_type",
            read_only=True,
        )
        existing_origin_identifier = serializers.CharField(
            source="existing_origin.effective_origin_identifier",
            read_only=True,
        )
        source_name = serializers.CharField(
            source="imported_source.name",
            read_only=True,
        )
        
        class Meta:
            model = CurationConflict
            fields = [
                "uuid",
                "project",
                "project_name",
                "resource_path",
                "conflict_type",
                "existing_origin",
                "existing_origin_type",
                "existing_origin_identifier",
                "imported_origin_data",
                "imported_source",
                "source_name",
                "resolution_status",
                "resolution_strategy",
                "resolved_origin",
                "resolved_by",
                "resolved_date",
                "resolution_notes",
                "created_date",
                "updated_date",
            ]
            read_only_fields = [
                "uuid",
                "created_date",
                "updated_date",
                "project_name",
                "existing_origin_type",
                "existing_origin_identifier",
                "source_name",
            ]
    
    serializer_class = CurationConflictSerializer
    
    def get_queryset(self):
        """Filter by project if provided."""
        queryset = super().get_queryset()
        project_slug = self.request.query_params.get("project")
        if project_slug:
            queryset = queryset.filter(project__slug=project_slug)
        
        resolution_status = self.request.query_params.get("resolution_status")
        if resolution_status:
            queryset = queryset.filter(resolution_status=resolution_status)
        
        return queryset
    
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """
        Resolve a conflict using a specific strategy.
        
        Expects:
        - strategy: Resolution strategy (required)
          Options: keep_existing, use_imported, highest_confidence, manual_decision
        - notes: Resolution notes (optional)
        """
        conflict = self.get_object()
        
        if conflict.is_resolved:
            return ErrorResponse("Conflict is already resolved")
        
        strategy = request.data.get("strategy")
        if not strategy:
            return ErrorResponse("'strategy' is required")
        
        valid_strategies = [
            "keep_existing",
            "use_imported",
            "highest_confidence",
            "manual_decision",
        ]
        if strategy not in valid_strategies:
            return ErrorResponse(
                f"Invalid strategy: {strategy}. "
                f"Valid options: {', '.join(valid_strategies)}"
            )
        
        notes = request.data.get("notes", "")
        resolved_by = request.user.username if request.user.is_authenticated else "API"
        
        try:
            if strategy == "keep_existing":
                conflict.resolve(
                    strategy="keep_existing",
                    resolved_origin=conflict.existing_origin,
                    resolved_by=resolved_by,
                    notes=notes or "Kept existing curation via API",
                )
            
            elif strategy == "use_imported":
                # Update existing origin with imported data
                from scanpipe.models_curation import CurationProvenance
                from django.utils import timezone
                
                imported_data = conflict.imported_origin_data
                conflict.existing_origin.amended_origin_type = imported_data["origin_type"]
                conflict.existing_origin.amended_origin_identifier = imported_data["origin_identifier"]
                conflict.existing_origin.amended_origin_notes = notes or "Used imported curation via API"
                conflict.existing_origin.amended_by = resolved_by
                conflict.existing_origin.is_verified = imported_data.get("is_verified", False)
                conflict.existing_origin.save()
                
                # Create provenance
                CurationProvenance.objects.create(
                    origin_determination=conflict.existing_origin,
                    action_type="merged",
                    curation_source=conflict.imported_source,
                    actor_name=resolved_by,
                    action_date=timezone.now(),
                    new_value=imported_data,
                    notes=notes or "Used imported curation via API",
                )
                
                conflict.resolve(
                    strategy="use_imported",
                    resolved_origin=conflict.existing_origin,
                    resolved_by=resolved_by,
                    notes=notes or "Used imported curation via API",
                )
            
            elif strategy == "highest_confidence":
                # Compare confidence scores
                existing_conf = (
                    1.0 if conflict.existing_origin.is_verified
                    else conflict.existing_origin.detected_origin_confidence or 0.5
                )
                imported_conf = conflict.imported_origin_data.get("confidence", 0.5)
                
                if imported_conf > existing_conf:
                    # Use imported (same as above)
                    from scanpipe.models_curation import CurationProvenance
                    from django.utils import timezone
                    
                    imported_data = conflict.imported_origin_data
                    conflict.existing_origin.amended_origin_type = imported_data["origin_type"]
                    conflict.existing_origin.amended_origin_identifier = imported_data["origin_identifier"]
                    conflict.existing_origin.amended_origin_notes = (
                        f"Higher confidence: {imported_conf} vs {existing_conf}. {notes}"
                    )
                    conflict.existing_origin.amended_by = resolved_by
                    conflict.existing_origin.is_verified = imported_data.get("is_verified", False)
                    conflict.existing_origin.save()
                    
                    CurationProvenance.objects.create(
                        origin_determination=conflict.existing_origin,
                        action_type="merged",
                        curation_source=conflict.imported_source,
                        actor_name=resolved_by,
                        action_date=timezone.now(),
                        new_value=imported_data,
                        notes=f"Higher confidence: {imported_conf} vs {existing_conf}",
                    )
                
                conflict.resolve(
                    strategy="highest_confidence",
                    resolved_origin=conflict.existing_origin,
                    resolved_by=resolved_by,
                    notes=notes or f"Confidence comparison: imported={imported_conf}, existing={existing_conf}",
                )
            
            elif strategy == "manual_decision":
                # User makes manual decision - just mark as resolved
                conflict.resolve(
                    strategy="manual_decision",
                    resolved_origin=conflict.existing_origin,
                    resolved_by=resolved_by,
                    notes=notes or "Manual decision via API",
                )
            
            serializer = self.get_serializer(conflict)
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"Resolution error: {str(e)}", exc_info=True)
            return ErrorResponse(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

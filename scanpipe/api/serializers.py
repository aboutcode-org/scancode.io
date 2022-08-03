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

from django.apps import apps

from rest_framework import serializers

from scanpipe.api import ExcludeFromListViewMixin
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.pipes import count_group_by
from scanpipe.pipes.fetch import fetch_urls

scanpipe_app = apps.get_app_config("scanpipe")


class SerializerExcludeFieldsMixin:
    """
    A Serializer mixin that takes an additional `exclude_fields` argument to
    exclude specific fields from the serialized content.

    Inspired by https://www.django-rest-framework.org/api-guide/serializers/#example
    """

    def __init__(self, *args, **kwargs):
        exclude_fields = kwargs.pop("exclude_fields", [])

        super().__init__(*args, **kwargs)

        for field_name in exclude_fields:
            self.fields.pop(field_name)


class PipelineChoicesMixin:
    def __init__(self, *args, **kwargs):
        """
        Loads the pipeline field choices on the init class instead of the module
        import, which ensures all pipelines are first properly loaded.
        """
        super().__init__(*args, **kwargs)
        self.fields["pipeline"].choices = scanpipe_app.get_pipeline_choices()


class RunSerializer(SerializerExcludeFieldsMixin, serializers.ModelSerializer):
    project = serializers.HyperlinkedRelatedField(
        view_name="project-detail", read_only=True
    )

    class Meta:
        model = Run
        fields = [
            "url",
            "pipeline_name",
            "status",
            "description",
            "project",
            "uuid",
            "created_date",
            "scancodeio_version",
            "task_id",
            "task_start_date",
            "task_end_date",
            "task_exitcode",
            "task_output",
            "log",
            "execution_time",
        ]


class ProjectSerializer(
    ExcludeFromListViewMixin, PipelineChoicesMixin, serializers.ModelSerializer
):
    pipeline = serializers.ChoiceField(
        choices=(),
        required=False,
        write_only=True,
    )
    execute_now = serializers.BooleanField(
        write_only=True,
        help_text=("Execute pipeline now"),
    )
    upload_file = serializers.FileField(write_only=True, required=False)
    input_urls = serializers.CharField(
        write_only=True,
        required=False,
        style={"base_template": "textarea.html"},
    )
    webhook_url = serializers.CharField(write_only=True, required=False)
    next_run = serializers.CharField(source="get_next_run", read_only=True)
    runs = RunSerializer(many=True, read_only=True)
    input_sources = serializers.JSONField(source="input_sources_list", read_only=True)
    codebase_resources_summary = serializers.SerializerMethodField()
    discovered_package_summary = serializers.SerializerMethodField()
    discovered_dependency_summary = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "name",
            "url",
            "uuid",
            "upload_file",
            "input_urls",
            "webhook_url",
            "created_date",
            "is_archived",
            "pipeline",
            "execute_now",
            "input_sources",
            "input_root",
            "output_root",
            "next_run",
            "runs",
            "extra_data",
            "error_count",
            "resource_count",
            "package_count",
            "dependency_count",
            "codebase_resources_summary",
            "discovered_package_summary",
            "discovered_dependency_summary",
        )

        exclude_from_list_view = [
            "input_root",
            "output_root",
            "extra_data",
            "error_count",
            "resource_count",
            "package_count",
            "dependency_count",
            "codebase_resources_summary",
            "discovered_package_summary",
            "discovered_dependency_summary",
        ]

    def get_codebase_resources_summary(self, project):
        queryset = project.codebaseresources.all()
        return count_group_by(queryset, "status")

    def get_discovered_package_summary(self, project):
        base_qs = project.discoveredpackages
        return {
            "total": base_qs.count(),
            "with_missing_resources": base_qs.exclude(missing_resources=[]).count(),
            "with_modified_resources": base_qs.exclude(modified_resources=[]).count(),
        }

    def get_discovered_dependency_summary(self, project):
        base_qs = project.discovereddependencys
        return {
            "total": base_qs.count(),
            "is_runtime": base_qs.filter(is_runtime=True).count(),
            "is_optional": base_qs.filter(is_optional=True).count(),
            "is_resolved": base_qs.filter(is_resolved=True).count(),
        }

    def create(self, validated_data):
        """
        Creates a new `project` with `upload_file` and `pipeline` as optional.
        The `execute_now` parameter can be set to execute the Pipeline on creation.
        """
        upload_file = validated_data.pop("upload_file", None)
        input_urls = validated_data.pop("input_urls", [])
        pipeline = validated_data.pop("pipeline", None)
        execute_now = validated_data.pop("execute_now", False)
        webhook_url = validated_data.pop("webhook_url", None)

        downloads, errors = fetch_urls(input_urls)
        if errors:
            raise serializers.ValidationError("Could not fetch: " + "\n".join(errors))

        project = super().create(validated_data)

        if upload_file:
            project.add_uploads([upload_file])

        if downloads:
            project.add_downloads(downloads)

        if pipeline:
            project.add_pipeline(pipeline, execute_now)

        if webhook_url:
            project.add_webhook_subscription(webhook_url)

        return project


class CodebaseResourceSerializer(serializers.ModelSerializer):
    for_packages = serializers.JSONField()
    compliance_alert = serializers.CharField()

    class Meta:
        model = CodebaseResource
        exclude = ["id", "project", "rootfs_path", "sha256", "sha512"]


class DiscoveredPackageSerializer(serializers.ModelSerializer):
    purl = serializers.CharField(source="package_url")

    class Meta:
        model = DiscoveredPackage
        exclude = [
            "id",
            "uuid",
            "project",
            "filename",
            "last_modified_date",
            "codebase_resources",
            "dependencies",
        ]


class DiscoveredDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscoveredDependency
        exclude = [
            "id",
            "project",
        ]


class ProjectErrorSerializer(serializers.ModelSerializer):
    traceback = serializers.SerializerMethodField()

    class Meta:
        model = ProjectError
        fields = ["uuid", "model", "message", "details", "traceback", "created_date"]

    def get_traceback(self, project_error):
        return project_error.traceback.split("\n")


class PipelineSerializer(PipelineChoicesMixin, serializers.ModelSerializer):
    """
    Serializer used in the `ProjectViewSet.add_pipeline` action.
    """

    pipeline = serializers.ChoiceField(
        choices=(),
        required=True,
        write_only=True,
    )
    execute_now = serializers.BooleanField(write_only=True)

    class Meta:
        model = Run
        fields = [
            "pipeline",
            "execute_now",
        ]


def get_model_serializer(model_class):
    """
    Returns a Serializer class that ia related to a given `model_class`.
    """
    serializer = {
        CodebaseResource: CodebaseResourceSerializer,
        DiscoveredPackage: DiscoveredPackageSerializer,
        DiscoveredDependency: DiscoveredDependencySerializer,
        ProjectError: ProjectErrorSerializer,
    }.get(model_class, None)

    if not serializer:
        raise LookupError(f"No Serializer found for {model_class}")

    return serializer


def get_serializer_fields(model_class):
    """
    Returns a list of fields declared on the Serializer that are related to the
    a given `model_class`.
    """
    serializer = get_model_serializer(model_class)
    fields = list(serializer().get_fields().keys())
    return fields

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
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError
from scanpipe.models import Run
from scanpipe.pipes import count_group_by

scanpipe_app_config = apps.get_app_config("scanpipe")


class SerializerExcludeFieldsMixin:
    """
    A Serializer mixin that takes an additional `exclude_fields` argument to
    exclude provided fields from the serialized content.

    Inspired by https://www.django-rest-framework.org/api-guide/serializers/#example
    """

    def __init__(self, *args, **kwargs):
        exclude_fields = kwargs.pop("exclude_fields", [])

        super().__init__(*args, **kwargs)

        for field_name in exclude_fields:
            self.fields.pop(field_name)


class RunSerializer(SerializerExcludeFieldsMixin, serializers.ModelSerializer):
    project = serializers.HyperlinkedRelatedField(
        view_name="project-detail", read_only=True
    )
    task_output = serializers.SerializerMethodField()
    run_id = serializers.CharField(source="get_run_id", read_only=True)

    class Meta:
        model = Run
        fields = [
            "url",
            "pipeline",
            "description",
            "project",
            "uuid",
            "run_id",
            "created_date",
            "task_id",
            "task_start_date",
            "task_end_date",
            "task_exitcode",
            "task_output",
            "execution_time",
        ]

    def get_task_output(self, project):
        return project.task_output.split("\n")[1:]


class ProjectSerializer(ExcludeFromListViewMixin, serializers.ModelSerializer):
    pipeline = serializers.ChoiceField(
        choices=scanpipe_app_config.pipelines,
        allow_blank=True,
        required=False,
        write_only=True,
        help_text=(
            "If provided, the selected pipeline will start on project creation. "
            "Requires an input file."
        ),
    )
    upload_file = serializers.FileField(write_only=True, required=False)
    next_run = serializers.CharField(source="get_next_run", read_only=True)
    runs = RunSerializer(many=True, read_only=True)
    codebase_resources_summary = serializers.SerializerMethodField()
    discovered_package_summary = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "name",
            "url",
            "uuid",
            "upload_file",
            "created_date",
            "pipeline",
            "input_root",
            "output_root",
            "next_run",
            "runs",
            "extra_data",
            "codebase_resources_summary",
            "discovered_package_summary",
        )
        exclude_from_list_view = [
            "input_root",
            "output_root",
            "extra_data",
            "codebase_resources_summary",
            "discovered_package_summary",
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

    def create(self, validated_data):
        """
        Create a new `project` with optionally provided `upload_file` and `pipeline`.
        If both are provided, the pipeline run is automatically started.
        """
        upload_file = validated_data.pop("upload_file", None)
        pipeline = validated_data.pop("pipeline", None)

        project = super().create(validated_data)

        if upload_file:
            project.add_input_file(upload_file)

        if pipeline:
            project.add_pipeline(pipeline, start_run=bool(upload_file))

        return project


class CodebaseResourceSerializer(serializers.ModelSerializer):
    for_packages = serializers.JSONField()

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
        ]


class ProjectErrorSerializer(serializers.ModelSerializer):
    traceback = serializers.SerializerMethodField()

    class Meta:
        model = ProjectError
        fields = ["uuid", "model", "details", "message", "traceback", "created_date"]

    def get_traceback(self, project_error):
        return project_error.traceback.split("\n")


def get_model_serializer(model_class):
    """
    Return the Serializer class related to the provided `model_class`.
    """
    serializer = {
        DiscoveredPackage: DiscoveredPackageSerializer,
        CodebaseResource: CodebaseResourceSerializer,
    }.get(model_class, None)

    if not serializer:
        raise LookupError(f"No Serializer found for {model_class}")

    return serializer


def get_serializer_fields(model_class):
    """
    Return the list of fields declared on the Serializer related to the
    provided `model_class`.
    """
    serializer = get_model_serializer(model_class)
    fields = list(serializer().get_fields().keys())
    return fields

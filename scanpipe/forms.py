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

from django import forms
from django.apps import apps
from django.db.models import BLANK_CHOICE_DASH

import django_filters

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project

scanpipe_app_config = apps.get_app_config("scanpipe")


def get_pipeline_choices(include_blank=True):
    choices = list(BLANK_CHOICE_DASH) if include_blank else []
    choices.extend([(name, name) for name in scanpipe_app_config.pipelines.keys()])
    return choices


class ProjectForm(forms.ModelForm):
    inputs = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"multiple": True}),
    )
    pipeline = forms.ChoiceField(
        choices=get_pipeline_choices(),
        required=False,
    )
    run_pipeline = forms.BooleanField(
        label="Run the selected pipeline",
        initial=True,
        required=False,
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "inputs",
            "pipeline",
            "run_pipeline",
        ]

    def save(self, *args, **kwargs):
        project = super().save(*args, **kwargs)

        pipeline = self.cleaned_data["pipeline"]
        run_pipeline = self.cleaned_data["run_pipeline"]

        inputs = self.files.getlist("inputs")
        for upload_file in inputs:
            project.add_input_file(upload_file)

        if pipeline:
            project.add_pipeline(pipeline, start_run=run_pipeline)

        return project


class AddPipelineForm(forms.Form):
    pipeline = forms.ChoiceField(
        choices=get_pipeline_choices(),
        required=True,
    )
    run_pipeline = forms.BooleanField(
        label="Run the selected pipeline",
        initial=True,
        required=False,
    )


class ProjectFilterSet(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Project
        fields = ["search"]


class ResourceFilterSet(django_filters.FilterSet):
    class Meta:
        model = CodebaseResource
        fields = [
            "programming_language",
            "mime_type",
        ]


class PackageFilterSet(django_filters.FilterSet):
    class Meta:
        model = DiscoveredPackage
        fields = ["type", "license_expression"]

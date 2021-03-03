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
from django.core.exceptions import ValidationError

import django_filters

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes.fetch import fetch_urls

scanpipe_app_config = apps.get_app_config("scanpipe")


class ProjectForm(forms.ModelForm):
    input_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": "file-input", "multiple": True},
        ),
    )
    input_urls = forms.CharField(
        label="Download URLs",
        required=False,
        help_text="Provide one or more URLs to download, one per line.",
        widget=forms.Textarea(
            attrs={
                "class": "textarea",
                "rows": 2,
                "placeholder": "https://domain.com/archive.zip",
            },
        ),
    )
    pipeline = forms.ChoiceField(
        choices=scanpipe_app_config.get_pipeline_choices(),
        required=False,
    )
    execute_now = forms.BooleanField(
        label="Execute pipeline now",
        initial=True,
        required=False,
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "input_files",
            "input_urls",
            "pipeline",
            "execute_now",
        ]

    class Media:
        js = ("add-inputs.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._input_errors = []

        name_field = self.fields["name"]
        name_field.widget.attrs["class"] = "input"
        name_field.help_text = "The unique name of your project."

    def clean_input_urls(self):
        """
        Fetch the `input_urls` and set the `downloads` objects in the cleaned_data.
        A validation error is raised if at least one URL could not be fetched.
        """
        input_urls = self.cleaned_data.get("input_urls", [])

        self.cleaned_data["downloads"], errors = fetch_urls(input_urls)
        if errors:
            raise ValidationError("Could not fetch: " + "\n".join(errors))

        return input_urls

    def save(self, *args, **kwargs):
        project = super().save(*args, **kwargs)

        input_files = self.files.getlist("input_files")
        downloads = self.cleaned_data.get("downloads")
        pipeline = self.cleaned_data["pipeline"]
        execute_now = self.cleaned_data["execute_now"]

        if input_files:
            project.add_uploads(input_files)

        if downloads:
            project.add_downloads(downloads)

        if pipeline:
            project.add_pipeline(pipeline, execute_now)

        return project


class AddPipelineForm(forms.Form):
    pipeline = forms.ChoiceField(
        choices=scanpipe_app_config.get_pipeline_choices(),
        required=True,
    )
    execute_now = forms.BooleanField(
        label="Execute pipeline now",
        initial=True,
        required=False,
    )

    def save(self, project):
        pipeline = self.cleaned_data["pipeline"]
        execute_now = self.cleaned_data["execute_now"]
        project.add_pipeline(pipeline, execute_now)

        return project


# TODO: Remove duplication with ProjectForm
class AddInputsForm(forms.Form):
    input_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": "file-input", "multiple": True},
        ),
    )
    input_urls = forms.CharField(
        label="Download URLs",
        required=False,
        help_text="Provide one or more URLs to download, one per line.",
        widget=forms.Textarea(
            attrs={
                "class": "textarea",
                "rows": 2,
                "placeholder": "https://domain.com/archive.zip",
            },
        ),
    )

    class Media:
        js = ("add-inputs.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._input_errors = []

    def clean_input_urls(self):
        """
        Fetch the `input_urls` and set the `downloads` objects in the cleaned_data.
        A validation error is raised if at least one URL could not be fetched.
        """
        input_urls = self.cleaned_data.get("input_urls", [])

        self.cleaned_data["downloads"], errors = fetch_urls(input_urls)
        if errors:
            raise ValidationError("Could not fetch: " + "\n".join(errors))

        return input_urls

    def save(self, project):
        input_files = self.files.getlist("input_files")
        downloads = self.cleaned_data.get("downloads")

        if input_files:
            project.add_uploads(input_files)

        if downloads:
            project.add_downloads(downloads)

        return project


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

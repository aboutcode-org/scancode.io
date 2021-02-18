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
from django.db.models import BLANK_CHOICE_DASH

import django_filters

from scanner.tasks import download
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
    download_urls = forms.CharField(
        label="Download URLs",
        required=False,
        help_text=(
            "You can provide multiple URLs separated by a new-line. "
            "A download URL is one that will immediately initiate the download of a "
            "file."
        ),
    )
    pipeline = forms.ChoiceField(
        choices=get_pipeline_choices(),
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
            "inputs",
            "download_urls",
            "pipeline",
            "execute_now",
        ]

    def clean_download_urls(self):
        download_urls = self.cleaned_data["download_urls"]
        download_urls = [url.strip() for url in download_urls.strip().split()]

        downloads = []
        for download_url in download_urls:
            try:
                downloaded = download(download_url)
            except Exception:
                raise ValidationError(f'Could not fetch URL: "{download_url}"')
            downloads.append(downloaded)

        self.cleaned_data["downloads"] = downloads
        return "\n".join(download_urls)

    def save(self, *args, **kwargs):
        project = super().save(*args, **kwargs)

        inputs = self.files.getlist("inputs")
        for upload_file in inputs:
            project.add_input_file(upload_file)

        downloads = self.cleaned_data.get("downloads", [])
        for downloaded in downloads:
            project.move_input_from(downloaded.file_path)

        pipeline = self.cleaned_data["pipeline"]
        execute_now = self.cleaned_data["execute_now"]
        if pipeline:
            project.add_pipeline(pipeline, execute_now)

        return project


class AddPipelineForm(forms.Form):
    pipeline = forms.ChoiceField(
        choices=get_pipeline_choices(),
        required=True,
    )
    execute_now = forms.BooleanField(
        label="Execute pipeline now",
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

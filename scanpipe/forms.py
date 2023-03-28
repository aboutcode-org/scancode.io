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

from scanpipe.models import Project
from scanpipe.pipes.fetch import fetch_urls

scanpipe_app = apps.get_app_config("scanpipe")


class InputsBaseForm(forms.Form):
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
                "placeholder": (
                    "https://domain.com/archive.zip\n"
                    "docker://docker-reference (e.g.: docker://postgres:13)"
                ),
            },
        ),
    )

    class Media:
        js = ("add-inputs.js",)

    def clean_input_urls(self):
        """
        Fetch the `input_urls` and sets the `downloads` objects in the cleaned_data.
        A validation error is raised, if at least one URL can't be fetched.
        """
        input_urls = self.cleaned_data.get("input_urls", [])

        self.cleaned_data["downloads"], errors = fetch_urls(input_urls)
        if errors:
            raise ValidationError("Could not fetch: " + "\n".join(errors))

        return input_urls

    def handle_inputs(self, project):
        input_files = self.files.getlist("input_files")
        downloads = self.cleaned_data.get("downloads")

        if input_files:
            project.add_uploads(input_files)

        if downloads:
            project.add_downloads(downloads)


class PipelineBaseForm(forms.Form):
    pipeline = forms.ChoiceField(
        choices=scanpipe_app.get_pipeline_choices(),
        required=False,
    )
    execute_now = forms.BooleanField(
        label="Execute pipeline now",
        initial=True,
        required=False,
    )

    def handle_pipeline(self, project):
        pipeline = self.cleaned_data["pipeline"]
        execute_now = self.cleaned_data["execute_now"]
        if pipeline:
            project.add_pipeline(pipeline, execute_now)


class ProjectForm(InputsBaseForm, PipelineBaseForm, forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "input_files",
            "input_urls",
            "pipeline",
            "execute_now",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        name_field = self.fields["name"]
        name_field.widget.attrs["class"] = "input"
        name_field.widget.attrs["autofocus"] = True
        name_field.help_text = "The unique name of your project."

    def clean_name(self):
        name = self.cleaned_data["name"]
        return " ".join(name.split())

    def save(self, *args, **kwargs):
        project = super().save(*args, **kwargs)
        self.handle_inputs(project)
        self.handle_pipeline(project)
        return project


class AddInputsForm(InputsBaseForm, forms.Form):
    def save(self, project):
        self.handle_inputs(project)
        return project


class AddPipelineForm(PipelineBaseForm):
    pipeline = forms.ChoiceField(
        choices=[
            (name, pipeline_class.get_summary())
            for name, pipeline_class in scanpipe_app.pipelines.items()
        ],
        widget=forms.RadioSelect(),
        required=True,
    )

    def save(self, project):
        self.handle_pipeline(project)
        return project


class ArchiveProjectForm(forms.Form):
    remove_input = forms.BooleanField(
        label="Remove inputs",
        initial=True,
        required=False,
    )
    remove_codebase = forms.BooleanField(
        label="Remove codebase",
        initial=True,
        required=False,
    )
    remove_output = forms.BooleanField(
        label="Remove outputs",
        initial=False,
        required=False,
    )

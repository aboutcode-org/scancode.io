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
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError

from taggit.forms import TagField
from taggit.forms import TagWidget

from scanpipe.models import Project
from scanpipe.pipes import fetch

scanpipe_app = apps.get_app_config("scanpipe")


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"class": "file-input"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(entry, initial) for entry in data]
        else:
            result = single_file_clean(data, initial)
        return result


class InputsBaseForm(forms.Form):
    input_files = MultipleFileField(required=False)
    input_urls = forms.CharField(
        label="Download URLs",
        required=False,
        help_text=(
            "Provide one or more URLs to download, one per line. "
            "Files are fetched at the beginning of the pipeline run execution."
        ),
        widget=forms.Textarea(
            attrs={
                "class": "textarea is-dynamic",
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

    @staticmethod
    def validate_scheme(input_urls):
        """
        Raise a validation error if some of the `input_urls` have a scheme that is not
        supported.
        """
        errors = []

        for url in input_urls:
            try:
                fetch.get_fetcher(url)
            except ValueError as e:
                errors.append(str(e))

        if errors:
            raise ValidationError("\n".join(errors))

    def clean_input_urls(self):
        """
        Fetch the `input_urls` and sets the `downloads` objects in the cleaned_data.
        A validation error is raised if at least one URL can't be fetched.
        """
        input_urls_str = self.cleaned_data.get("input_urls", "")
        input_urls = input_urls_str.split()

        self.validate_scheme(input_urls)

        if errors := fetch.check_urls_availability(input_urls):
            raise ValidationError("Could not fetch:\n" + "\n".join(errors))

        return input_urls

    def handle_inputs(self, project):
        input_files = self.files.getlist("input_files")
        if input_files:
            project.add_uploads(input_files)

        input_urls = self.cleaned_data.get("input_urls", [])
        for url in input_urls:
            project.add_input_source(download_url=url)


class GroupChoiceField(forms.MultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def valid_value(self, value):
        """Accept all values."""
        return True


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
    selected_groups = GroupChoiceField(required=False)

    def handle_pipeline(self, project):
        pipeline = self.cleaned_data["pipeline"]
        execute_now = self.cleaned_data["execute_now"]
        selected_groups = self.cleaned_data.get("selected_groups", [])
        if pipeline:
            project.add_pipeline(pipeline, execute_now, selected_groups)


class ProjectForm(InputsBaseForm, PipelineBaseForm, forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "input_files",
            "input_urls",
            "pipeline",
            "execute_now",
            "selected_groups",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        name_field = self.fields["name"]
        name_field.widget.attrs["class"] = "input"
        name_field.widget.attrs["autofocus"] = True
        name_field.help_text = "The unique name of your project."

        # Do not include "add-on" pipelines in the context of the create Project form
        pipeline_choices = scanpipe_app.get_pipeline_choices(include_addon=False)
        self.fields["pipeline"].choices = pipeline_choices

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

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
        choices=scanpipe_app.get_pipeline_choices(),
        widget=forms.RadioSelect(),
        required=True,
    )

    def save(self, project):
        self.handle_pipeline(project)
        return project


class AddLabelsForm(forms.Form):
    labels = TagField(
        label="Add labels to this project:",
        widget=TagWidget(
            attrs={"class": "input", "placeholder": "Comma-separated list of labels"}
        ),
    )

    def save(self, project):
        project.labels.add(*self.cleaned_data["labels"])
        return project


class EditInputSourceTagForm(forms.Form):
    input_source_uuid = forms.CharField(
        max_length=50,
        widget=forms.widgets.HiddenInput,
        required=True,
    )
    tag = forms.CharField(
        widget=forms.TextInput(attrs={"class": "input"}),
    )

    def save(self, project):
        input_source_uuid = self.cleaned_data.get("input_source_uuid")
        try:
            input_source = project.inputsources.get(uuid=input_source_uuid)
        except (ValidationError, ObjectDoesNotExist):
            return

        input_source.update(tag=self.cleaned_data.get("tag", ""))
        return input_source


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


class ListTextarea(forms.CharField):
    """
    A Django form field that displays as a textarea and converts each line of input
    into a list of items.

    This field extends the `CharField` and uses the `Textarea` widget to display the
    input as a textarea.
    Each line of the textarea input is split into items, removing leading/trailing
    whitespace and empty lines.
    The resulting list of items is then stored as the field value.
    """

    widget = forms.Textarea

    def to_python(self, value):
        """Split the textarea input into lines and remove empty lines."""
        if value:
            return [line.strip() for line in value.splitlines() if line.strip()]

    def prepare_value(self, value):
        """Join the list items into a string with newlines."""
        if value is not None:
            value = "\n".join(value)
        return value


class ProjectSettingsForm(forms.ModelForm):
    settings_fields = [
        "extract_recursively",
        "ignored_patterns",
        "scancode_license_score",
        "attribution_template",
    ]
    extract_recursively = forms.BooleanField(
        label="Extract recursively",
        required=False,
        initial=True,
        help_text="Extract nested archives-in-archives recursively",
        widget=forms.CheckboxInput(attrs={"class": "checkbox mr-1"}),
    )
    ignored_patterns = ListTextarea(
        label="Ignored patterns",
        required=False,
        help_text="Provide one or more path patterns to be ignored, one per line.",
        widget=forms.Textarea(
            attrs={
                "class": "textarea is-dynamic",
                "rows": 3,
                "placeholder": "*.xml\ntests/*\n*docs/*.rst",
            },
        ),
    )
    scancode_license_score = forms.IntegerField(
        label="License score",
        min_value=0,
        max_value=100,
        required=False,
        help_text=(
            "Do not return license matches with a score lower than this score. "
            "A number between 0 and 100."
        ),
        widget=forms.NumberInput(attrs={"class": "input"}),
    )
    attribution_template = forms.CharField(
        label="Attribution template",
        required=False,
        help_text="Custom attribution template.",
        widget=forms.Textarea(attrs={"class": "textarea is-dynamic", "rows": 3}),
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "textarea is-dynamic"}),
        }

    def __init__(self, *args, **kwargs):
        """Load initial values from Project ``settings`` field."""
        super().__init__(*args, **kwargs)
        for field_name in self.settings_fields:
            field = self.fields[field_name]
            # Do not override the field ``initial`` if the key is not in the settings
            if field_name in self.instance.settings:
                field.initial = self.instance.settings.get(field_name)

    def save(self, *args, **kwargs):
        project = super().save(*args, **kwargs)
        self.update_project_settings(project)
        return project

    def update_project_settings(self, project):
        """Update Project ``settings`` field values from form data."""
        config = {
            field_name: self.cleaned_data[field_name]
            for field_name in self.settings_fields
        }
        project.settings.update(config)
        project.save(update_fields=["settings"])


class ProjectCloneForm(forms.Form):
    clone_name = forms.CharField(widget=forms.TextInput(attrs={"class": "input"}))
    copy_inputs = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Input files located in the input/ work directory will be copied.",
        widget=forms.CheckboxInput(attrs={"class": "checkbox mr-1"}),
    )
    copy_pipelines = forms.BooleanField(
        initial=True,
        required=False,
        help_text="All pipelines assigned to the original project will be copied over.",
        widget=forms.CheckboxInput(attrs={"class": "checkbox mr-1"}),
    )
    copy_settings = forms.BooleanField(
        initial=True,
        required=False,
        help_text="All project settings will be copied.",
        widget=forms.CheckboxInput(attrs={"class": "checkbox mr-1"}),
    )
    copy_subscriptions = forms.BooleanField(
        initial=True,
        required=False,
        help_text="All project webhook subscription will be copied.",
        widget=forms.CheckboxInput(attrs={"class": "checkbox mr-1"}),
    )
    execute_now = forms.BooleanField(
        label="Execute copied pipeline(s) now",
        initial=False,
        required=False,
        help_text="Copied pipelines will be directly executed.",
    )

    def __init__(self, instance, *args, **kwargs):
        self.project = instance
        super().__init__(*args, **kwargs)
        self.fields["clone_name"].initial = f"{self.project.name} clone"

    def clean_clone_name(self):
        clone_name = self.cleaned_data.get("clone_name")
        if Project.objects.filter(name=clone_name).exists():
            raise ValidationError("Project with this name already exists.")
        return clone_name

    def save(self, *args, **kwargs):
        return self.project.clone(**self.cleaned_data)

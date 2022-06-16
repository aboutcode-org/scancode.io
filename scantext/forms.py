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


class EditorForm(forms.Form):
    input_text = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 30,
                "class": "textarea has-fixed-size",
                "placeholder": "Paste your license text here.",
            }
        ),
        required=True,
    )

    # def clean_input_text(self):
    #     input_text = self.cleaned_data.get("input_text")
    #     return " ".join(input_text.split())

    # def save(self, *args, **kwargs):
    #     license = super().save(*args, **kwargs)
    #     self.handle_input(license)
    #     return license

    # class Media:
    #     js = ("add-inputs.js",)

    # def handle_inputs(self, project):
    #     input_file = self.files.getlist("input_files")
    #     input_text = self.cleaned_data.get("input_text")
    #     print(input_text)
    #     if input_file:
    #         license.add_uploads(input_file)
    #     elif input_text:
    #         license.add_license(input_text)

    # input_files = forms.FileField(
    #     required=False,
    #     widget=forms.ClearableFileInput(
    #         attrs={"class": "file-input", "multiple": False},
    #     ),
    # )

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

import tempfile

from django import forms


class LicenseScanForm(forms.Form):
    input_text = forms.CharField(
        strip=False,
        widget=forms.Textarea(
            attrs={
                "rows": 15,
                "class": "textarea has-fixed-size",
                "placeholder": "Paste your license text here.",
            }
        ),
        required=False,
    )
    input_file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": "file-input", "multiple": False},
        ),
    )


def handle_input_text(input_text, temp_dir):
    # The flush in tempfile is required to ensure that the content is
    # written to the disk before it's read by get_licenses function
    with tempfile.NamedTemporaryFile(mode="w", dir=temp_dir, delete=False) as temp_file:
        temp_file.write(input_text)
        temp_file.flush()

    return temp_file.name


def handle_input_file(input_file, temp_dir):
    # Save the input file to the temporary directory
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=temp_dir, delete=False
    ) as temp_file:
        for chunk in input_file.chunks():
            temp_file.write(chunk)

    return temp_file.name

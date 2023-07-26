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

from django.contrib import messages
from django.shortcuts import render

from scantext.forms import LicenseScanForm
from scantext.forms import handle_input_file
from scantext.forms import handle_input_text
from scantext.match_text import get_licenses


def license_scanview(request):
    if request.method != "POST":
        return render(
            request, "scantext/license_scan_form.html", {"form": LicenseScanForm()}
        )

    form = LicenseScanForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request, "scantext/license_scan_form.html", {"form": LicenseScanForm()}
        )

    input_text = form.cleaned_data["input_text"]
    input_file = request.FILES.get("input_file", False)

    if input_text and input_file:
        message = "Provide text or a text file but not both."
        messages.warning(request, message)
        return render(
            request,
            "scantext/license_scan_form.html",
            {
                "form": LicenseScanForm(),
            },
        )

    if not input_text and not input_file:
        message = "Provide text or a text file to scan."
        messages.warning(request, message)
        return render(
            request,
            "scantext/license_scan_form.html",
            {
                "form": LicenseScanForm(),
            },
        )

    from commoncode.fileutils import get_temp_dir

    temp_dir = get_temp_dir(prefix="scantext_")
    if input_text:
        file_path = handle_input_text(input_text, temp_dir)
    elif input_file:
        file_path = handle_input_file(input_file, temp_dir)

    expressions = get_licenses(location=file_path)

    if not expressions:
        message = "Could not detect any license."
        messages.warning(request, message)
        return render(
            request,
            "scantext/license_scan_form.html",
            {
                "form": LicenseScanForm(),
            },
        )

    return render(
        request,
        "scantext/license_summary.html",
        {
            "text": input_text,
            "detected_licenses": expressions,
        },
    )

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

from functools import lru_cache

from django.http import HttpResponse
from django.urls import path
from django.urls import reverse

import saneyaml
from licensedcode.models import load_licenses


@lru_cache(maxsize=None)
def get_licenses():
    """
    Load the licenses from the ScanCode-toolkit `licensedcode` data and
    return a mapping of `key` to `license` objects.
    The result is cached in memory so the load_licenses() process is only
    executed once on the first `get_licenses()` call.
    """
    return load_licenses()


def license_list_view(request):
    """
    Display a list of all the licenses linked to their details.
    """
    licenses = get_licenses()
    license_links = [
        f'<a href="{reverse("license_details", args=[key])}">{key}</a>'
        for key in licenses.keys()
    ]
    return HttpResponse("<br>".join(license_links))


def license_details_view(request, key):
    """
    Display all the information available about the provided license `key`
    followed by the full license text.
    """
    licenses = get_licenses()
    try:
        data = saneyaml.dump(licenses[key].to_dict())
        text = licenses[key].text
    except KeyError:
        return HttpResponse(f"License {key} not found.")
    return HttpResponse(f"<pre>{data}</pre><hr><pre>{text}</pre>")


urls = [
    path("", license_list_view, name="license_list"),
    path("<path:key>/", license_details_view, name="license_details"),
]

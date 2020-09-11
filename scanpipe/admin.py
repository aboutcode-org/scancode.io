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

from django.contrib import admin

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import ProjectError


class ProjectRelatedModelAdmin(admin.ModelAdmin):
    """
    Regroup the common ModelAdmin values for Project related models.
    """

    list_select_related = True
    actions_on_top = False
    actions_on_bottom = True

    def has_add_permission(self, request):
        return False


@admin.register(CodebaseResource)
class CodebaseResourceAdmin(ProjectRelatedModelAdmin):
    list_display = (
        "project",
        "path",
        "status",
        "type",
        "size",
        "name",
        "extension",
        "programming_language",
        "mime_type",
        "file_type",
        "license_expressions",
        "copyrights",
        "for_packages",
    )
    list_filter = ("project", "status", "type", "programming_language")
    search_fields = ("path", "mime_type", "file_type")


class CodebaseResourceInline(admin.TabularInline):
    model = DiscoveredPackage.codebase_resources.through
    extra = 0
    raw_id_fields = ("codebaseresource",)


@admin.register(DiscoveredPackage)
class DiscoveredPackageAdmin(ProjectRelatedModelAdmin):
    list_display = (
        "project",
        "package_url",
        "type",
        "namespace",
        "name",
        "version",
        "license_expression",
        "copyright",
    )
    list_filter = ("project", "type")
    search_fields = ("name", "namespace", "description", "codebase_resources__path")
    exclude = ("codebase_resources",)
    inlines = (CodebaseResourceInline,)


@admin.register(ProjectError)
class ProjectErrorAdmin(ProjectRelatedModelAdmin):
    list_display = ("project", "model", "message", "created_date", "uuid")
    list_filter = ("project", "model")
    search_fields = ("uuid", "message")

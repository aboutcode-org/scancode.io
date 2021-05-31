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

from django.db import models
from django.utils.translation import gettext_lazy as _

import django_filters
from packageurl.contrib.django.filters import PackageURLFilter

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectError


class FilterSetUtilsMixin:
    @staticmethod
    def remove_field_from_query_dict(query_dict, field_name, remove_value=None):
        """
        Returns an encoded URL without the value for given `field_name`.
        For multi-value filters, a single value can be removed using `remove_value`.
        This URL can be used to remove a filter value from the active filters.
        """
        if not query_dict:
            return ""

        data = query_dict.copy()
        field_data = data.pop(field_name, [])

        if remove_value and len(field_data) > 1 and remove_value in field_data:
            for item in field_data:
                if item != remove_value:
                    data.update({field_name: item})

        return data.urlencode()

    def is_active(self):
        """
        Returns True if any of the filter is active, except the 'sort' filter.
        """
        return bool(
            [
                field_name
                for field_name in self.form.changed_data
                if field_name not in ["sort"]
            ]
        )

    def get_query_no_sort(self):
        return self.remove_field_from_query_dict(self.data, "sort")

    def get_filters_breadcrumb(self):
        return [
            {
                "label": self.filters[field_name].label,
                "value": value,
                "remove_url": self.remove_field_from_query_dict(
                    self.data, field_name, value
                ),
            }
            for field_name in self.form.changed_data
            for value in self.data.getlist(field_name)
        ]

    @classmethod
    def verbose_name_plural(cls):
        return cls.Meta.model._meta.verbose_name_plural


class ProjectFilterSet(FilterSetUtilsMixin, django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Project
        fields = ["search"]


class JSONContainsFilter(django_filters.CharFilter):
    """
    Allow "contains" lookup on a JSONField converted to text.
    This is useful for datastructures stored as list of dictionaries, where  Django's
    default lookups are not available.
    Require the implementation of "json_field_contains" method on the QuerySet.
    """

    def filter(self, qs, value):
        if value:
            return qs.json_field_contains(self.field_name, value)
        return qs


class InPackageFilter(django_filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = (
            ("true", _("Yes")),
            ("false", _("No")),
        )
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value == "true":
            return qs.in_package()
        elif value == "false":
            return qs.not_in_package()
        return qs


class ResourceFilterSet(FilterSetUtilsMixin, django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="path", lookup_expr="icontains")
    in_package = InPackageFilter()

    class Meta:
        model = CodebaseResource
        fields = [
            "search",
            "path",
            "rootfs_path",
            "md5",
            "sha1",
            "sha256",
            "sha512",
            "size",
            "status",
            "type",
            "name",
            "extension",
            "programming_language",
            "mime_type",
            "file_type",
            "compliance_alert",
            "copyrights",
            "holders",
            "authors",
            "licenses",
            "license_expressions",
            "emails",
            "urls",
            "in_package",
        ]

    @classmethod
    def filter_for_lookup(cls, field, lookup_type):
        """
        Add support for JSONField storing "list" using the JSONListFilter.
        """
        if isinstance(field, models.JSONField) and field.default == list:
            return JSONContainsFilter, {}

        return super().filter_for_lookup(field, lookup_type)


class PackageFilterSet(FilterSetUtilsMixin, django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    purl = PackageURLFilter()

    class Meta:
        model = DiscoveredPackage
        fields = [
            "search",
            "purl",
            "type",
            "namespace",
            "name",
            "version",
            "qualifiers",
            "subpath",
            "filename",
            "primary_language",
            "release_date",
            "homepage_url",
            "download_url",
            "size",
            "md5",
            "sha1",
            "bug_tracking_url",
            "code_view_url",
            "vcs_url",
            "type",
            "license_expression",
            "declared_license",
            "copyright",
            "manifest_path",
            "contains_source_code",
        ]


class ErrorFilterSet(FilterSetUtilsMixin, django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="message", lookup_expr="icontains")

    class Meta:
        model = ProjectError
        fields = [
            "search",
            "model",
            "message",
        ]

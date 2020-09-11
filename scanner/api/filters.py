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
from django.forms import widgets
from django.forms.fields import MultipleChoiceField

import django_filters

from scanner.models import Scan


class CharMultipleWidget(widgets.TextInput):
    """
    Enables the support for `MultiValueDict` `?field=a&field=b`
    reusing the `SelectMultiple.value_from_datadict()` but render as a `TextInput`.
    """

    def value_from_datadict(self, data, files, name):
        value = widgets.SelectMultiple().value_from_datadict(data, files, name)

        if not value or value == [""]:
            return ""

        return value

    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        return ", ".join(value)


class MultipleCharField(MultipleChoiceField):
    """
    Overrides `MultipleChoiceField` to fit in `MultipleCharFilter`.
    """

    widget = CharMultipleWidget

    def valid_value(self, value):
        return True


class MultipleCharFilter(django_filters.MultipleChoiceFilter):
    """
    Filters on multiple values for a CharField type using `?field=a&field=b` URL syntax.
    """

    field_class = MultipleCharField


class ScanStatusFilter(django_filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs["empty_label"] = "All"
        kwargs["choices"] = (
            ("completed", "Completed"),
            ("completed-with-issues", "Completed with issues"),
            ("failed", "Failed"),
            ("download-failed", "Download failed"),
            ("scan-failed", "Scan failed"),
            ("in-progress", "In progress"),
            ("not-started-yet", "Not started yet"),
        )
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        scan_done_lookup = {"task_output__contains": "Scanning done."}
        lookups = {
            "completed": qs.succeed(),
            "completed-with-issues": qs.failed().filter(**scan_done_lookup),
            "failed": qs.failed().exclude(**scan_done_lookup),
            "download-failed": qs.download_failed(),
            "scan-failed": qs.scan_failed().exclude(**scan_done_lookup),
            "in-progress": qs.started(),
            "not-started-yet": qs.not_started(),
        }

        return lookups.get(value, qs).distinct()


class ScanFilterSet(django_filters.rest_framework.FilterSet):
    uri = MultipleCharFilter(
        help_text="Exact URI. Multi-value supported.",
    )
    status = ScanStatusFilter(label="Status")
    scancode_version = django_filters.CharFilter(
        lookup_expr="icontains",
    )
    scancode_version__lt = django_filters.CharFilter(
        field_name="scancode_version",
        lookup_expr="lt",
    )
    scancode_version__gt = django_filters.CharFilter(
        field_name="scancode_version",
        lookup_expr="gt",
    )

    class Meta:
        model = Scan
        fields = (
            "uuid",
            "uri",
            "status",
            "filename",
            "scancode_version",
            "scancode_version__lt",
            "scancode_version__gt",
            "task_id",
            "task_exitcode",
            "created_by",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["created_by"].extra["widget"] = widgets.HiddenInput

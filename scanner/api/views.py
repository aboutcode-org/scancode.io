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

from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from scanner.api.filters import ScanFilterSet
from scanner.api.serializers import ScanSerializer
from scanner.models import Scan


# A ViewSet that provides default `create()`, `retrieve()`, `destroy()` and
# `list()` actions.
# `update()`, `partial_update()` are not available since it does not make sense
# to change the URI of a Scan once created.
class ScanViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Scan.objects.all()
    serializer_class = ScanSerializer
    filterset_class = ScanFilterSet
    search_fields = ("uri",)

    def get_data_response(self, as_summary=False):
        scan = self.get_object()

        if not scan.has_output_file:
            return Response({"error": "Scan data not available"}, status=400)

        scan_data = scan.data
        if not scan_data:
            return Response({"error": "Scan data not ready"}, status=400)

        if as_summary:
            return Response(scan.summary)

        return Response(scan_data)

    @action(detail=False)
    def status(self, request, *args, **kwargs):
        queryset_methods = [
            "not_started",
            "started",
            "completed",
            "succeed",
            "failed",
            "scan_failed",
            "task_failed",
            "task_timeout",
            "download_failed",
        ]
        status = {
            method_name: getattr(Scan.objects, method_name)().count()
            for method_name in queryset_methods
        }
        return Response(status)

    @action(detail=True)
    def data(self, request, *args, **kwargs):
        return self.get_data_response()

    @action(detail=True)
    def summary(self, request, *args, **kwargs):
        return self.get_data_response(as_summary=True)

    @action(detail=True)
    def rescan(self, request, *args, **kwargs):
        scan = self.get_object()
        scan.rescan()
        return Response({"message": "Re-scan requested."})

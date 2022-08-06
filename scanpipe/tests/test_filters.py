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

from django.test import TestCase

from scanpipe.filters import ResourceFilterSet
from scanpipe.models import CodebaseResource
from scanpipe.models import Project


class ScanPipeFiltersTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_filters_filter_queryset_empty_values(self):
        resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path="r1",
            # CharField blank=True null=False
            programming_language="Python",
            # JSONField default=list
            copyrights=[{"copyright": "Copyright (c)"}],
        )
        resource2 = CodebaseResource.objects.create(
            project=self.project1,
            path="r2",
        )

        data = {"programming_language": ""}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1, resource2], list(filterset.qs))

        data = {"programming_language": "Python"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"programming_language": "EMPTY"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource2], list(filterset.qs))

        data = {"copyrights": ""}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1, resource2], list(filterset.qs))

        data = {"copyrights": "Copyright"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"copyrights": "EMPTY"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource2], list(filterset.qs))

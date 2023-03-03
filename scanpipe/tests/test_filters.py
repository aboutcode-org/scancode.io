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

import uuid

from django.test import TestCase
from django.utils import timezone

from scanpipe.filters import FilterSetUtilsMixin
from scanpipe.filters import ProjectFilterSet
from scanpipe.filters import ResourceFilterSet
from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.models import Run


class ScanPipeFilterTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_filters_project_filterset_status(self):
        now = timezone.now()
        not_started = Project.objects.create(name="not_started")
        Run.objects.create(project=not_started)
        queued = Project.objects.create(name="queued")
        Run.objects.create(project=queued, task_id=uuid.uuid4())
        running = Project.objects.create(name="running")
        Run.objects.create(project=running, task_start_date=now, task_id=uuid.uuid4())
        succeed = Project.objects.create(name="succeed")
        Run.objects.create(
            project=succeed, task_start_date=now, task_end_date=now, task_exitcode=0
        )
        failed = Project.objects.create(name="failed")
        Run.objects.create(
            project=failed, task_start_date=now, task_end_date=now, task_exitcode=1
        )

        filterset = ProjectFilterSet(data={"status": ""})
        self.assertEqual(6, len(filterset.qs))

        filterset = ProjectFilterSet(data={"status": "not_started"})
        self.assertEqual([not_started], list(filterset.qs))

        filterset = ProjectFilterSet(data={"status": "queued"})
        self.assertEqual([queued], list(filterset.qs))

        filterset = ProjectFilterSet(data={"status": "running"})
        self.assertEqual([running], list(filterset.qs))

        filterset = ProjectFilterSet(data={"status": "succeed"})
        self.assertEqual([succeed], list(filterset.qs))

        filterset = ProjectFilterSet(data={"status": "failed"})
        self.assertEqual([failed], list(filterset.qs))

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

        data = {"programming_language": FilterSetUtilsMixin.empty_value}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource2], list(filterset.qs))

        data = {"copyrights": ""}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1, resource2], list(filterset.qs))

        data = {"copyrights": "Copyright"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"copyrights": FilterSetUtilsMixin.empty_value}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource2], list(filterset.qs))

    def test_scanpipe_filters_params_for_search(self):
        data = {
            "status": "succeed",
            "search": "query",
            "page": 2,
        }
        filterset = ProjectFilterSet(data)

        self.assertEqual(
            {"page": 2, "search": "query", "status": "succeed"},
            filterset.params,
        )
        self.assertEqual(
            {"status": "succeed"},
            filterset.params_for_search,
        )

        data = {
            "search": FilterSetUtilsMixin.empty_value,
        }
        filterset = ProjectFilterSet(data)
        self.assertEqual([], list(filterset.qs))

        data = {
            "search": FilterSetUtilsMixin.other_value,
        }
        filterset = ProjectFilterSet(data)
        self.assertEqual([], list(filterset.qs))

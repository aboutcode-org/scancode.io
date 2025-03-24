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

from scanpipe.filters import DependencyFilterSet
from scanpipe.filters import FilterSetUtilsMixin
from scanpipe.filters import PackageFilterSet
from scanpipe.filters import ProjectFilterSet
from scanpipe.filters import ResourceFilterSet
from scanpipe.filters import parse_query_string_to_lookups
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.tests import dependency_data1
from scanpipe.tests import dependency_data2
from scanpipe.tests import make_resource_file
from scanpipe.tests import package_data1
from scanpipe.tests import package_data2


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

    def test_scanpipe_filters_project_filterset_labels(self):
        Project.objects.create(name="project2")
        self.project1.labels.add("label1")

        filterset = ProjectFilterSet(data={"label": ""})
        self.assertEqual(2, len(filterset.qs))

        filterset = ProjectFilterSet(data={"label": "label1"})
        self.assertEqual([self.project1], list(filterset.qs))

        filterset = ProjectFilterSet(data={"label": "label2"})
        self.assertEqual(0, len(filterset.qs))

        filterset = ProjectFilterSet(data={"search": "label1"})
        self.assertEqual([self.project1], list(filterset.qs))
        filterset = ProjectFilterSet(data={"search": "lab"})
        self.assertEqual([self.project1], list(filterset.qs))

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

    def test_scanpipe_filters_resource_filterset_tag(self):
        resource1 = CodebaseResource.objects.create(
            project=self.project1,
            path="r1",
            tag="tag1",
        )
        resource2 = CodebaseResource.objects.create(
            project=self.project1,
            path="r2",
            tag="tag2",
        )

        data = {"tag": ""}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1, resource2], list(filterset.qs))

        data = {"tag": "tag1"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"tag": "tag2"}
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

    def test_scanpipe_filters_package_filterset_is_vulnerable(self):
        p1 = DiscoveredPackage.create_from_data(self.project1, package_data1)
        p2 = DiscoveredPackage.create_from_data(self.project1, package_data2)
        p2.update(
            affected_by_vulnerabilities=[{"vulnerability_id": "VCID-cah8-awtr-aaad"}]
        )

        filterset = PackageFilterSet(data={"is_vulnerable": ""})
        self.assertEqual(2, len(filterset.qs))

        filterset = PackageFilterSet(data={"is_vulnerable": "no"})
        self.assertEqual([p1], list(filterset.qs))

        filterset = PackageFilterSet(data={"is_vulnerable": "yes"})
        self.assertEqual([p2], list(filterset.qs))

    def test_scanpipe_filters_package_filterset_search(self):
        p1 = DiscoveredPackage.create_from_data(self.project1, package_data1)
        DiscoveredPackage.create_from_data(self.project1, package_data2)

        filterset = PackageFilterSet(data={})
        self.assertEqual(2, len(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.package_url})
        self.assertEqual([p1], list(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.version})
        self.assertEqual([p1], list(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.name})
        self.assertEqual(2, len(filterset.qs))

        filterset = PackageFilterSet(data={"search": p1.type})
        self.assertEqual(2, len(filterset.qs))

    def test_scanpipe_filters_package_filterset_sort(self):
        p1 = DiscoveredPackage.create_from_data(self.project1, package_data1)
        p2 = DiscoveredPackage.create_from_data(self.project1, package_data2)

        filterset = PackageFilterSet(data={"sort": "package_url"})
        self.assertQuerySetEqual([p1, p2], filterset.qs)

        filterset = PackageFilterSet(data={"sort": "-package_url"})
        self.assertQuerySetEqual([p2, p1], filterset.qs)

    def test_scanpipe_filters_dependency_filterset(self):
        DiscoveredPackage.create_from_data(self.project1, package_data1)
        CodebaseResource.objects.create(
            project=self.project1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        CodebaseResource.objects.create(
            project=self.project1,
            path="data.tar.gz-extract/Gemfile.lock",
        )
        d1 = DiscoveredDependency.create_from_data(self.project1, dependency_data1)
        d2 = DiscoveredDependency.create_from_data(self.project1, dependency_data2)

        filterset = DependencyFilterSet(data={"is_pinned": ""})
        self.assertEqual(2, len(filterset.qs))
        filterset = DependencyFilterSet(data={"is_pinned": True})
        self.assertEqual([d2], list(filterset.qs))
        filterset = DependencyFilterSet(data={"is_pinned": False})
        self.assertEqual([d1], list(filterset.qs))

        filterset = DependencyFilterSet(data={"type": ""})
        self.assertEqual(2, len(filterset.qs))
        filterset = DependencyFilterSet(data={"type": "pypi"})
        self.assertEqual([d1], list(filterset.qs))
        filterset = DependencyFilterSet(data={"type": "gem"})
        self.assertEqual([d2], list(filterset.qs))

        filterset = DependencyFilterSet(data={"scope": ""})
        self.assertEqual(2, len(filterset.qs))
        filterset = DependencyFilterSet(data={"scope": "install"})
        self.assertEqual([d1], list(filterset.qs))
        filterset = DependencyFilterSet(data={"scope": "dependencies"})
        self.assertEqual([d2], list(filterset.qs))

        filterset = DependencyFilterSet(data={"datasource_id": ""})
        self.assertEqual(2, len(filterset.qs))
        filterset = DependencyFilterSet(data={"datasource_id": "pypi_sdist_pkginfo"})
        self.assertEqual([d1], list(filterset.qs))
        filterset = DependencyFilterSet(data={"datasource_id": "gemfile_lock"})
        self.assertEqual([d2], list(filterset.qs))

    def test_scanpipe_filters_parse_query_string_to_lookups(self):
        inputs = {
            "LICENSE": "(AND: ('name__icontains', 'LICENSE'))",
            "two words": (
                "(OR: ('name__icontains', 'two'), ('name__icontains', 'words'))"
            ),
            "'two words'": "(AND: ('name__icontains', 'two words'))",
            "na me:LICENSE": (
                "(AND: ('name__icontains', 'na'), ('me__icontains', 'LICENSE'))"
            ),
            "name:LICENSE": "(AND: ('name__icontains', 'LICENSE'))",
            "default_value name:LICENSE": (
                "(AND: ('name__icontains', 'default_value'), "
                "('name__icontains', 'LICENSE'))"
            ),
            'name:"name with spaces"': "(AND: ('name__icontains', 'name with spaces'))",
            "name:'name with spaces'": "(AND: ('name__icontains', 'name with spaces'))",
            "-name:LICENSE -name:NOTICE": (
                "(AND: (NOT (AND: ('name__icontains', 'LICENSE'))), "
                "(NOT (AND: ('name__icontains', 'NOTICE'))))"
            ),
            "name:LICENSE status:scanned": (
                "(AND: ('name__icontains', 'LICENSE'), "
                "('status__icontains', 'scanned'))"
            ),
            'name^:"file"': "(AND: ('name__istartswith', 'file'))",
            'name$:".zip"': "(AND: ('name__iendswith', '.zip'))",
            'name=:"LICENSE"': "(AND: ('name__iexact', 'LICENSE'))",
            'name~:"LIC"': "(AND: ('name__icontains', 'LIC'))",
            'count<:"100"': "(AND: ('count__lt', '100'))",
            'count>:"10"': "(AND: ('count__gt', '10'))",
        }

        for query_string, expected in inputs.items():
            lookups = parse_query_string_to_lookups(query_string, "icontains", ["name"])
            self.assertEqual(expected, str(lookups))

    def test_scanpipe_filters_filter_advanced_search_query_string(self):
        resource1 = make_resource_file(self.project1, path="dir/readme.html")
        resource2 = make_resource_file(self.project1, path="dir/archive.zip")

        data = {"search": "README"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"search": "name:readme.html"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"search": "extension:.html"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"search": "-name:readme.html"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource2], list(filterset.qs))

        data = {"search": "not_a_field:value"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([], list(filterset.qs))

        data = {"search": "discovered_packages:m2m"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([], list(filterset.qs))

        data = {"search": "name^:read name$:html"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual([resource1], list(filterset.qs))

        data = {"search": "path^:dir"}
        filterset = ResourceFilterSet(data=data)
        self.assertEqual(2, len(filterset.qs))

        data = {"search": "'"}  # No closing quotation
        filterset = ResourceFilterSet(data=data)
        self.assertFalse(filterset.is_valid())
        expected_errors = {
            "search": ["The provided search value is invalid: No closing quotation"]
        }
        self.assertEqual(expected_errors, filterset.errors)
        self.assertEqual(2, len(filterset.qs))

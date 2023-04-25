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

import datetime
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.test import TransactionTestCase

from scanpipe import pipes
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_input
from scanpipe.tests import dependency_data1
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1
from scanpipe.tests import resource_data1


class ScanPipePipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_strip_root(self):
        input_paths = [
            "/root/dir/file",
            "/root/dir/file/",
            "//root/dir/file",
            "//root/dir/file/",
            "root/dir/file",
            "root/dir/file/",
        ]
        expected = "dir/file"

        for path in input_paths:
            self.assertEqual(expected, pipes.strip_root(path))
            self.assertEqual(expected, pipes.strip_root(Path(path)))

    def test_scanpipe_pipes_tag_not_analyzed_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="filename1.ext",
            status="scanned",
        )

        pipes.tag_not_analyzed_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("not-analyzed", resource1.status)
        self.assertEqual("scanned", resource2.status)

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_pipes_filename_now(self):
        self.assertEqual("2010-10-10-10-10-10", pipes.filename_now())

    def test_scanpipe_pipes_update_or_create_resource(self):
        p1 = Project.objects.create(name="Analysis")
        package = pipes.update_or_create_package(p1, package_data1)
        resource_data = dict(resource_data1)
        resource_data["for_packages"] = [package.package_uid]

        resource = pipes.update_or_create_resource(p1, resource_data)
        for field_name, value in resource_data.items():
            self.assertEqual(value, getattr(resource, field_name), msg=field_name)

        resource_data["status"] = "scanned"
        resource = pipes.update_or_create_resource(p1, resource_data)
        self.assertEqual("scanned", resource.status)

        resource_data["for_packages"] = ["does_not_exists"]
        with self.assertRaises(DiscoveredPackage.DoesNotExist):
            pipes.update_or_create_resource(p1, resource_data)

    def test_scanpipe_pipes_update_or_create_package(self):
        p1 = Project.objects.create(name="Analysis")
        package = pipes.update_or_create_package(p1, package_data1)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", package.purl)
        self.assertEqual("bash", package.primary_language)
        self.assertEqual(datetime.date(1999, 10, 10), package.release_date)

        updated_data = dict(package_data1)
        updated_data["notice_text"] = "NOTICE"
        updated_package = pipes.update_or_create_package(p1, updated_data)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", updated_package.purl)
        self.assertEqual("NOTICE", updated_package.notice_text)
        self.assertEqual(package.pk, updated_package.pk)

        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        package_data2 = dict(package_data1)
        package_data2["name"] = "new name"
        package_data2["package_uid"] = ""
        package_data2["release_date"] = "2020-11-01T01:40:20"
        package2 = pipes.update_or_create_package(p1, package_data2, [resource1])
        self.assertNotEqual(package.pk, package2.pk)
        self.assertIn(resource1, package2.codebase_resources.all())
        self.assertEqual(datetime.date(2020, 11, 1), package2.release_date)

        # Make sure we can assign a package to multiple Resources calling
        # update_or_create_package() several times.
        resource2 = CodebaseResource.objects.create(project=p1, path="filename2.ext")
        package2 = pipes.update_or_create_package(p1, package_data2, [resource2])
        self.assertIn(package2, resource1.discovered_packages.all())
        self.assertIn(package2, resource2.discovered_packages.all())

    def test_scanpipe_pipes_update_or_create_package_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(project=p1, path="filename2.ext")
        resources = [resource1, resource2]

        # On creation
        package = pipes.update_or_create_package(p1, package_data1, resources)
        self.assertIn(resource1, package.codebase_resources.all())
        self.assertIn(resource2, package.codebase_resources.all())

        # On update
        package.delete()
        package = pipes.update_or_create_package(p1, package_data1)
        self.assertEqual(0, package.codebase_resources.count())
        package = pipes.update_or_create_package(p1, package_data1, resources)
        self.assertIn(resource1, package.codebase_resources.all())
        self.assertIn(resource2, package.codebase_resources.all())

    def test_scanpipe_pipes_update_or_create_package_package_uid(self):
        p1 = Project.objects.create(name="Analysis")
        package_data = dict(package_data1)

        package_data["package_uid"] = None
        pipes.update_or_create_package(p1, package_data)
        pipes.update_or_create_package(p1, package_data)

        package_data["package_uid"] = ""
        pipes.update_or_create_package(p1, package_data)

        del package_data["package_uid"]
        pipes.update_or_create_package(p1, package_data)

        # Make sure only 1 package was created, then properly found in the db regardless
        # of the empty/none package_uid.
        self.assertEqual(1, DiscoveredPackage.objects.count())

    def test_scanpipe_pipes_update_or_create_dependency(self):
        p1 = Project.objects.create(name="Analysis")
        CodebaseResource.objects.create(
            project=p1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        pipes.update_or_create_package(p1, package_data1)

        dependency_data = dict(dependency_data1)
        dependency_data["scope"] = ""
        dependency = pipes.update_or_create_dependency(p1, dependency_data)
        for field_name, value in dependency_data.items():
            self.assertEqual(value, getattr(dependency, field_name), msg=field_name)

        dependency_data["scope"] = "install"
        dependency = pipes.update_or_create_dependency(p1, dependency_data)
        self.assertEqual(dependency.scope, "install")


class ScanPipePipesTransactionTest(TransactionTestCase):
    """
    Since we are testing some Database errors, we need to use a
    TransactionTestCase to avoid any TransactionManagementError while running
    the tests.
    """

    data_location = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_make_codebase_resource(self):
        p1 = Project.objects.create(name="Analysis")
        resource_location = str(self.data_location / "notice.NOTICE")

        with self.assertRaises(ValueError) as cm:
            pipes.make_codebase_resource(p1, resource_location)

        self.assertIn("not", str(cm.exception))
        self.assertIn(resource_location, str(cm.exception))
        self.assertIn("/codebase", str(cm.exception))

        copy_input(resource_location, p1.codebase_path)
        resource_location = str(p1.codebase_path / "notice.NOTICE")
        pipes.make_codebase_resource(p1, resource_location)

        resource = p1.codebaseresources.get()
        self.assertEqual(1178, resource.size)
        self.assertEqual("4bd631df28995c332bf69d9d4f0f74d7ee089598", resource.sha1)
        self.assertEqual("90cd416fd24df31f608249b77bae80f1", resource.md5)
        self.assertEqual("text/plain", resource.mime_type)
        self.assertEqual("ASCII text", resource.file_type)
        self.assertEqual("", resource.status)
        self.assertEqual(CodebaseResource.Type.FILE, resource.type)

        # Duplicated path: skip the creation and no project error added
        pipes.make_codebase_resource(p1, resource_location)
        self.assertEqual(1, p1.codebaseresources.count())
        self.assertEqual(0, p1.projecterrors.count())

    def test_scanpipe_add_resource_to_package(self):
        project1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        package1 = pipes.update_or_create_package(project1, package_data1)
        self.assertFalse(resource1.for_packages)

        self.assertIsNone(scancode.add_resource_to_package(None, resource1, project1))
        self.assertFalse(resource1.for_packages)

        scancode.add_resource_to_package("not_available", resource1, project1)
        self.assertFalse(resource1.for_packages)
        self.assertEqual(1, project1.projecterrors.count())
        error = project1.projecterrors.get()
        self.assertEqual("assemble_package", error.model)
        expected = {"resource": "filename.ext", "package_uid": "not_available"}
        self.assertEqual(expected, error.details)

        scancode.add_resource_to_package(package1.package_uid, resource1, project1)
        self.assertEqual(len(resource1.for_packages), 1)
        self.assertIn(package1.package_uid, resource1.for_packages)

        # Package will not be added twice since it is already associated with the
        # resource.
        scancode.add_resource_to_package(package1.package_uid, resource1, project1)
        self.assertEqual(len(resource1.for_packages), 1)

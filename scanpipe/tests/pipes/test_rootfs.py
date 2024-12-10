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

from pathlib import Path
from unittest import mock

from django.test import TestCase

from commoncode.archive import extract_tar
from container_inspector.distro import Distro
from packagedcode.models import PackageWithResources

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import rootfs
from scanpipe.pipes.rootfs import RootFs


class ScanPipeRootfsPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_rootfs_from_project_codebase_class_method(self):
        p1 = Project.objects.create(name="Analysis")
        root_filesystems = list(rootfs.RootFs.from_project_codebase(p1))
        self.assertEqual([], root_filesystems)

        input_location = str(self.data / "rootfs" / "windows-container-rootfs.tar")
        extract_tar(input_location, target_dir=p1.codebase_path)
        root_filesystems = list(rootfs.RootFs.from_project_codebase(p1))
        self.assertEqual(1, len(root_filesystems))
        distro = root_filesystems[0].distro
        self.assertEqual("windows", distro.os)
        self.assertEqual("windows", distro.identifier)

    def test_scanpipe_pipes_rootfs_flag_uninteresting_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(project=p1, rootfs_path="/etc/file")

        rootfs.flag_uninteresting_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("ignored-not-interesting", resource2.status)

    def test_scanpipe_pipes_rootfs_has_hash_diff(self):
        install_file = mock.Mock(sha256="else", md5="md5")
        codebase_resource = CodebaseResource(sha256="sha256", md5="md5")
        self.assertTrue(rootfs.has_hash_diff(install_file, codebase_resource))

        install_file = mock.Mock(sha512="sha512", md5="md5")
        codebase_resource = CodebaseResource(sha512="sha512", md5="else")
        self.assertTrue(rootfs.has_hash_diff(install_file, codebase_resource))

        install_file = mock.Mock(sha256="sha256", md5="md5")
        codebase_resource = CodebaseResource(sha256="sha256", md5="md5")
        self.assertFalse(rootfs.has_hash_diff(install_file, codebase_resource))

    def test_scanpipe_pipes_rootfs_flag_ignorable_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/cmake_install.cmake",
            rootfs_path="/user/cmake_install.cmake",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1, path="root/user/example.pot", rootfs_path="/user/example.pot"
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/__pycache__/foo.pyc",
            rootfs_path="/user/__pycache__/foo.pyc",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1, path="root/user/foo.css.map", rootfs_path="/user/foo.css.map"
        )
        resource5 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/should-not-be-ignored.txt",
            rootfs_path="/user/should-not-be-ignored.txt",
        )
        rootfs.flag_ignorable_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        resource5.refresh_from_db()
        self.assertEqual("ignored-default-ignores", resource1.status)
        self.assertEqual("ignored-default-ignores", resource2.status)
        self.assertEqual("ignored-default-ignores", resource3.status)
        self.assertEqual("ignored-default-ignores", resource4.status)
        self.assertEqual("", resource5.status)

    def test_scanpipe_pipes_rootfs_flag_data_files_with_no_clues(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/foo.data",
            rootfs_path="/user/foo.data",
            file_type="data",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/bar.data",
            rootfs_path="/user/bar.data",
            file_type="data",
            detected_license_expression="apache-2.0",
        )
        rootfs.flag_data_files_with_no_clues(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("ignored-data-file-no-clues", resource1.status)
        self.assertEqual("", resource2.status)

    def test_scanpipe_pipes_rootfs_flag_media_files_as_uninteresting(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/foo.png",
            rootfs_path="/user/foo.png",
            mime_type="image/png",
            file_type="image/png",
            is_media=True,
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/bar.jpg",
            rootfs_path="/user/bar.jpg",
            mime_type="image/jpeg",
            file_type="JPEG image data",
            is_media=True,
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/baz.txt",
            rootfs_path="/user/baz.txt",
            is_media=False,
        )
        rootfs.flag_media_files_as_uninteresting(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        self.assertEqual("ignored-media-file", resource1.status)
        self.assertEqual("ignored-media-file", resource2.status)
        self.assertEqual("", resource3.status)

    @mock.patch("scanpipe.pipes.rootfs.RootFs.get_installed_packages")
    def test_scanpipe_pipes_rootfs_scan_rootfs_for_system_packages(
        self, mock_get_installed_packages
    ):
        project = Project.objects.create(name="Analysis")
        rootfs_instance = RootFs(location="")
        rootfs_instance.distro = Distro(identifier="debian")

        system_packages = [
            (
                "pkg:deb/ubuntu/libncurses5@1.0",
                PackageWithResources(
                    type="deb",
                    namespace="ubuntu",
                    name="libncurses5",
                    version="1.0",
                ),
            ),
            (
                # Same namespace
                "pkg:deb/ubuntu/libncurses5@2.0",
                PackageWithResources(
                    type="deb",
                    namespace="ubuntu",
                    name="libncurses5",
                    version="2.0",
                ),
            ),
            (
                # Different namespace
                "pkg:deb/other/libncurses5@3.0",
                PackageWithResources(
                    type="deb",
                    namespace="debian",
                    name="libncurses5",
                    version="3.0",
                ),
            ),
            (
                # This package has no namespace on purpose.
                "pkg:deb/libndp0@1.4-2ubuntu0.16.04.1",
                PackageWithResources(
                    type="deb",
                    name="libndp0",
                    version="1.4-2ubuntu0.16.04.1",
                ),
            ),
        ]

        mock_get_installed_packages.return_value = system_packages
        rootfs.scan_rootfs_for_system_packages(project, rootfs_instance)

        package_qs = project.discoveredpackages.all()
        self.assertEqual(4, package_qs.count())
        self.assertEqual(0, package_qs.filter(namespace="ubuntu").count())
        # All namespaces updated to "debian" as the most common namespace
        self.assertEqual(4, package_qs.filter(namespace="debian").count())

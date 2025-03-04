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

from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import windows


class ScanPipeWindowsPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_windows_flag_uninteresting_windows_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/example.lnk",
            rootfs_path="/Files/example.lnk",
            extension=".lnk",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/Hives/Software_Delta",
            rootfs_path="/Hives/Software_Delta",
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/example.dat",
            rootfs_path="/Files/example.dat",
            extension=".dat",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/should-not-be-ignored.txt",
            rootfs_path="/Files/should-not-be-ignored.txt",
            extension=".txt",
        )

        windows.flag_uninteresting_windows_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        self.assertEqual("ignored-not-interesting", resource1.status)
        self.assertEqual("ignored-not-interesting", resource2.status)
        self.assertEqual("ignored-not-interesting", resource3.status)
        self.assertEqual("", resource4.status)

    def test_scanpipe_pipes_windows_flag_known_software(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python/py.exe",
            rootfs_path="/Files/Python/py.exe",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python27/python2.exe",
            rootfs_path="/Files/Python27/python2.exe",
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python3/python3.exe",
            rootfs_path="/Files/Python3/python3.exe",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python39/python3.9",
            rootfs_path="/Files/Python39/python3.9.exe",
        )
        resource5 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
            rootfs_path="/Files/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
        )
        resource6 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/jdk-11.0.1/readme.txt",
            rootfs_path="/Files/jdk-11.0.1/readme.txt",
        )
        resource7 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/openjdk-11.0.1/readme.txt",
            rootfs_path="/Files/openjdk-11.0.1/readme.txt",
        )
        resource8 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/jdk/readme.txt",
            rootfs_path="/Files/jdk/readme.txt",
        )
        resource9 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/openjdk/readme.txt",
            rootfs_path="/Files/openjdk/readme.txt",
        )
        resource10 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/something-else/jdk/readme.txt",
            rootfs_path="/Files/Program Files/something-else/jdk/readme.txt",
        )
        resource11 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python/py.exe",
            rootfs_path="/Python/py.exe",
        )
        resource12 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python27/python2.exe",
            rootfs_path="/Python27/python2.exe",
        )
        resource13 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python3/python3.exe",
            rootfs_path="/Python3/python3.exe",
        )
        resource14 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python39/python3.9",
            rootfs_path="/Python39/python3.9.exe",
        )
        resource15 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
            rootfs_path="/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
        )
        resource16 = CodebaseResource.objects.create(
            project=p1,
            path="root/jdk-11.0.1/readme.txt",
            rootfs_path="/jdk-11.0.1/readme.txt",
        )
        resource17 = CodebaseResource.objects.create(
            project=p1,
            path="root/openjdk-11.0.1/readme.txt",
            rootfs_path="/openjdk-11.0.1/readme.txt",
        )
        resource18 = CodebaseResource.objects.create(
            project=p1,
            path="root/jdk/readme.txt",
            rootfs_path="/jdk/readme.txt",
        )
        resource19 = CodebaseResource.objects.create(
            project=p1,
            path="root/openjdk/readme.txt",
            rootfs_path="/openjdk/readme.txt",
        )
        resource20 = CodebaseResource.objects.create(
            project=p1,
            path="root/Program Files/something-else/jdk/readme.txt",
            rootfs_path="/Program Files/something-else/jdk/readme.txt",
        )

        windows.flag_known_software(p1)
        resource11.refresh_from_db()
        resource12.refresh_from_db()
        resource13.refresh_from_db()
        resource14.refresh_from_db()
        resource15.refresh_from_db()
        resource16.refresh_from_db()
        resource17.refresh_from_db()
        resource18.refresh_from_db()
        resource19.refresh_from_db()
        resource20.refresh_from_db()
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        resource5.refresh_from_db()
        resource6.refresh_from_db()
        resource7.refresh_from_db()
        resource8.refresh_from_db()
        resource9.refresh_from_db()
        resource10.refresh_from_db()

        self.assertEqual("installed-package", resource1.status)
        self.assertEqual("installed-package", resource2.status)
        self.assertEqual("installed-package", resource3.status)
        self.assertEqual("installed-package", resource4.status)
        self.assertEqual("", resource5.status)
        self.assertEqual("installed-package", resource6.status)
        self.assertEqual("installed-package", resource7.status)
        self.assertEqual("installed-package", resource8.status)
        self.assertEqual("installed-package", resource9.status)
        self.assertEqual("", resource10.status)
        self.assertEqual("installed-package", resource11.status)
        self.assertEqual("installed-package", resource12.status)
        self.assertEqual("installed-package", resource13.status)
        self.assertEqual("installed-package", resource14.status)
        self.assertEqual("", resource15.status)
        self.assertEqual("installed-package", resource16.status)
        self.assertEqual("installed-package", resource17.status)
        self.assertEqual("installed-package", resource18.status)
        self.assertEqual("installed-package", resource19.status)
        self.assertEqual("", resource20.status)

    def test_scanpipe_pipes_windows_flag_program_files(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files (x86)/Microsoft/example.exe",
            rootfs_path="/Files/Program Files (x86)/Microsoft/example.exe",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/Microsoft/example.exe",
            rootfs_path="/Files/Program Files/Microsoft/example.exe",
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files (x86)/7Zip/7z.exe",
            rootfs_path="/Files/Program Files (x86)/7Zip/7z.exe",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/7Zip/7z.exe",
            rootfs_path="/Files/Program Files/7Zip/7z.exe",
        )
        resource5 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files (x86)/common files/sample.dat",
            rootfs_path="/Files/Program Files (x86)/common files/sample.dat",
        )
        resource6 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/common files/sample.dat",
            rootfs_path="/Files/Program Files/common files/sample.dat",
        )
        windows.flag_program_files(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        resource5.refresh_from_db()
        resource6.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("", resource2.status)
        self.assertEqual("installed-package", resource3.status)
        self.assertEqual("installed-package", resource4.status)
        self.assertEqual("", resource5.status)
        self.assertEqual("", resource6.status)

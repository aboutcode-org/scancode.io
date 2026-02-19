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

import saneyaml

from scanpipe import pipes
from scanpipe.pipes import ort
from scanpipe.tests import make_project
from scanpipe.tests import package_data1


class ScanPipeORTPipesTest(TestCase):
    def test_scanpipe_ort_pipes_get_ort_project_type(self):
        project = make_project(name="Analysis")
        self.assertIsNone(ort.get_ort_project_type(project))

        project.add_input_source(
            filename="image.tar", download_url="docker://docker-ref"
        )
        self.assertEqual("docker", ort.get_ort_project_type(project))

    def test_scanpipe_ort_pipes_to_ort_package_list_yml(self):
        project = make_project(name="Analysis")
        pipes.update_or_create_package(project, package_data1)

        package_list_yml = ort.to_ort_package_list_yml(project)
        package_list = saneyaml.load(package_list_yml)

        expected = {
            "projectName": "Analysis",
            "projectVcs": {"type": "", "url": "", "revision": "", "path": ""},
            "dependencies": [
                {
                    "id": "deb::adduser:3.118",
                    "purl": "pkg:deb/debian/adduser@3.118?arch=all",
                    "vcs": {
                        "type": "",
                        "url": "https://packages.vcs.url",
                        "revision": "",
                        "path": "",
                    },
                    "sourceArtifact": {"url": "https://download.url/package.zip"},
                    "declaredLicenses": ["GPL-2.0-only AND GPL-2.0-or-later"],
                    "description": "add and remove users and groups",
                    "homepageUrl": "https://packages.debian.org",
                    "authors": [
                        "Debian Adduser Developers <adduser@packages.debian.org>"
                    ],
                }
            ],
        }
        self.assertEqual(expected, package_list)

    def test_scanpipe_ort_pipes_to_ort_package_list_yml_sanitization(self):
        project = make_project(name="Analysis")
        package_data = {
            "name": "passwd",
            "type": "deb",
            "version": "1:4.13+dfsg1-4ubuntu3.2",
            "purl": "pkg:deb/ubuntu/passwd@1:4.13%2Bdfsg1-4ubuntu3.2?arch=amd64",
        }
        pipes.update_or_create_package(project, package_data)

        package_list_yml = ort.to_ort_package_list_yml(project)
        package_list = saneyaml.load(package_list_yml)
        dependency_id = package_list["dependencies"][0]["id"]

        # The colon in the version should be sanitized
        self.assertNotIn("1:4.13", dependency_id)
        self.assertEqual("deb::passwd:1_4.13+dfsg1-4ubuntu3.2", dependency_id)

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

from packageurl import PackageURL

from scanpipe.models import Project
from scanpipe.pipes import maven
from scanpipe.pipes.input import copy_inputs
from scanpipe.pipes.input import load_inventory_from_toolkit_scan


class ScanPipeMavenPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    @mock.patch("scanpipe.pipes.maven.fetch.fetch_http")
    def test_scanpipe_maven_download_pom_file(self, mock_fetch_http):
        mock_response = mock.Mock()
        mock_response.path = "/safe/example1.pom"
        mock_fetch_http.return_value = mock_response

        pom_url = "https://repo1.maven.org/maven2/example/example1.pom"

        expected = {
            "pom_file_path": "/safe/example1.pom",
            "output_path": "/safe/example1.pom-output.json",
            "pom_url": "https://repo1.maven.org/maven2/example/example1.pom",
        }

        result = maven.download_pom_file(pom_url)
        self.assertEqual(result, expected)

    @mock.patch("scanpipe.pipes.maven.scancode.run_scan")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    def test_scanpipe_maven_update_datafile_paths(
        self, mock_json_load, mock_open, mock_run_scan
    ):
        mock_json_load.return_value = {
            "packages": [
                {
                    "name": "example-package",
                    "version": "1.0.0",
                    "datafile_paths": ["/safe/mock_pom.xml"],
                }
            ],
            "dependencies": [
                {
                    "name": "example-dep",
                    "version": "2.0.0",
                    "datafile_path": "/safe/mock_pom.xml",
                }
            ],
        }

        pom_file_dict = {
            "pom_file_path": "/safe/mock.pom",
            "output_path": "/safe/mock.pom-output.json",
            "pom_url": "https://repo1.maven.org/maven2/example/example.pom",
        }

        expected_packages = [
            {
                "name": "example-package",
                "version": "1.0.0",
                "datafile_paths": [
                    "https://repo1.maven.org/maven2/example/example.pom"
                ],
            }
        ]
        expected_deps = [
            {"name": "example-dep", "version": "2.0.0", "datafile_path": ""}
        ]

        packages, deps = maven.update_datafile_paths(pom_file_dict)

        self.assertEqual(packages, expected_packages)
        self.assertEqual(deps, expected_deps)

    def test_scanpipe_maven_get_pom_url(self):
        package_url = "pkg:maven/org/apache/commons/commons-lang3@3.12.0"
        purl = PackageURL.from_string(package_url)
        result = maven.get_pom_url(purl)
        expected = "https://repo.maven.apache.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"

        self.assertEqual(result, expected)

    def test_scanpipe_maven_update_package_license_from_resource_if_missing(self):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "maven" / "missing_lic_in_package.json"
        project1.copy_input_from(input_location)
        copy_inputs(project1.inputs(), project1.codebase_path)

        load_inventory_from_toolkit_scan(project1, str(input_location))

        for package in project1.discoveredpackages.all():
            self.assertEqual(package.get_declared_license_expression(), "")

        maven.update_package_license_from_resource_if_missing(project1)

        for package in project1.discoveredpackages.all():
            self.assertEqual(package.get_declared_license_expression(), "apache-2.0")

    def test_scanpipe_maven_update_package_license_from_resource_if_missing_no_change(
        self,
    ):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "maven" / "lic_in_package.json"
        project1.copy_input_from(input_location)
        copy_inputs(project1.inputs(), project1.codebase_path)

        load_inventory_from_toolkit_scan(project1, str(input_location))

        for package in project1.discoveredpackages.all():
            self.assertEqual(package.get_declared_license_expression(), "custom")

        maven.update_package_license_from_resource_if_missing(project1)

        for package in project1.discoveredpackages.all():
            self.assertEqual(package.get_declared_license_expression(), "custom")

    def test_scanpipe_maven_check_input_and_return_purl(self):
        project = mock.Mock()

        project.inputsources.all.return_value = ["pkg:maven/a/test@1.0"]
        expected = PackageURL(type="maven", namespace="a", name="test", version="1.0")
        result = maven.check_input_and_return_purl(project)
        self.assertEqual(result, expected)

    def test_scanpipe_maven_check_input_and_return_purl_no_input(self):
        project = mock.Mock()
        project.inputsources.all.return_value = []
        with self.assertRaisesMessage(ValueError, "Only 1 maven purl is accepted."):
            maven.check_input_and_return_purl(project)

    def test_scanpipe_maven_check_input_and_return_purl_multi_input(self):
        project = mock.Mock()
        project.inputsources.all.return_value = [
            "pkg:maven/a/b@1",
            "pkg:maven/a/b@2",
        ]
        with self.assertRaisesMessage(ValueError, "Only 1 maven purl is accepted."):
            maven.check_input_and_return_purl(project)

    def test_scanpipe_maven_check_input_and_return_purl_non_supported_type(self):
        project = mock.Mock()
        project.inputsources.all.return_value = ["pkg:npm/test@1.0"]
        with self.assertRaisesMessage(ValueError, "Only maven purl is supported."):
            maven.check_input_and_return_purl(project)

    def test_scanpipe_maven_check_input_and_return_purl_missing_version(self):
        project = mock.Mock()
        project.inputsources.all.return_value = ["pkg:maven/a/test"]
        with self.assertRaisesMessage(ValueError, "Version is required."):
            maven.check_input_and_return_purl(project)

    @mock.patch("scanpipe.pipes.maven.fetch_path")
    def test_scanpipe_maven_fetch_inputs(self, mock_fetch_path):
        purl = PackageURL.from_string("pkg:maven/a/test@1.0")

        mock_fetch_path.side_effect = ["/path/to/binary.jar", "/path/to/source.jar"]

        src_path, bin_path = maven.fetch_inputs(purl)
        self.assertEqual(bin_path, "/path/to/binary.jar")
        self.assertEqual(src_path, "/path/to/source.jar")

    @mock.patch("scanpipe.pipes.maven.fetch.fetch_url")
    def test_scanpipe_maven_fetch_path(self, mock_fetch_url):
        url = "https://example.com/package.jar"

        mock_response = mock.Mock()
        mock_response.path = "/downloaded/package.jar"
        mock_fetch_url.return_value = mock_response

        result = maven.fetch_path(url, "binary")
        self.assertEqual(result, "/downloaded/package.jar")

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    def test_scanpipe_maven_fetch_and_scan_remote_pom_local_pom_exist(
        self, mock_json_load, mock_open
    ):
        mock_json_load.return_value = {
            "files": [{"path": "src/main/pom.xml"}, {"path": "src/main/Main.java"}]
        }
        result = maven.fetch_and_scan_remote_pom(
            "pkg:maven/org/test@1.0", "/path/to/output.json"
        )
        self.assertEqual(result, [])

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    @mock.patch("scanpipe.pipes.maven.get_pom_url")
    def test_scanpipe_maven_fetch_and_scan_remote_pom_no_pom_url(
        self, mock_get_pom_url, mock_json_load, mock_open
    ):
        mock_json_load.return_value = {"files": [{"path": "src/main/Main.java"}]}
        mock_get_pom_url.return_value = None

        result = maven.fetch_and_scan_remote_pom(
            "pkg:maven/org/test@1.0", "/path/to/output.json"
        )
        self.assertEqual(result, [{"pkg:maven/org/test@1.0": ["Failed to resolve POM URL."]}])

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    @mock.patch("scanpipe.pipes.maven.get_pom_url")
    @mock.patch("scanpipe.pipes.maven.download_pom_file")
    def test_scanpipe_maven_fetch_and_scan_remote_pom_no_pom_file(
        self, mock_download_pom_file, mock_get_pom_url, mock_json_load, mock_open
    ):
        mock_json_load.return_value = {"files": []}
        mock_get_pom_url.return_value = "https://example.com/test.pom"
        mock_download_pom_file.return_value = {}

        result = maven.fetch_and_scan_remote_pom(
            "pkg:maven/org/test@1.0", "/path/to/output.json"
        )
        self.assertEqual(result, [{"https://example.com/test.pom": ["Failed to download the POM file."]}])

    def test_update_scan_data(self):
        original_data = {"packages": [{"name": "package1"}], "dependencies": [{"name": "dep1"}]}
        new_package = [{"name": "package2"}]
        new_dependency = [{"name": "dep2"}]

        result = maven.update_scan_data(original_data, new_package, new_dependency)

        self.assertEqual(
            result["packages"], [{"name": "package1"}, {"name": "package2"}]
        )
        self.assertEqual(result["dependencies"], [{"name": "dep1"}, {"name": "dep2"}])

    @mock.patch("scanpipe.pipes.maven.scancode.run_scan")
    def test_scanpipe_maven_scan_pom_file(self, mock_run_scan):
        pom_file_dict = {
            "pom_file_path": "/main/mock.pom",
            "output_path": "/main/mock.pom-output.json",
        }
        mock_run_scan.return_value = {}
        result = maven.scan_pom_file(pom_file_dict)
        self.assertEqual(result, {})

        mock_run_scan.assert_called_once_with(
            location="/main/mock.pom",
            output_file="/main/mock.pom-output.json",
            run_scan_args={"package": True},
        )

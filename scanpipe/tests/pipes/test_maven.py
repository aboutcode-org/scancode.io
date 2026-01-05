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

from scanpipe.models import Project
from scanpipe.pipes import maven
from scanpipe.pipes.input import copy_inputs
from scanpipe.pipes.input import load_inventory_from_toolkit_scan


class ScanPipeMavenPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_maven_parse_maven_filename(self):
        test1 = "wisp-logging-2025.11.11.195957-97a44b0-sources.jar"
        test2 = "guava-33.5.0-jre-javadoc.jar"
        test3 = "junit-4.13.2.jar"
        test4 = "guava-33.5.0-jre.jar"

        expected1_name = "wisp-logging"
        expected1_version = "2025.11.11.195957-97a44b0"
        expected2_name = "guava"
        expected2_version = "33.5.0-jre"
        expected3_name = "junit"
        expected3_version = "4.13.2"

        result1_name, result1_version = maven.parse_maven_filename(test1)
        result2_name, result2_version = maven.parse_maven_filename(test2)
        result3_name, result3_version = maven.parse_maven_filename(test3)
        result4_name, result4_version = maven.parse_maven_filename(test4)

        self.assertEqual(result1_name, expected1_name)
        self.assertEqual(result1_version, expected1_version)
        self.assertEqual(result2_name, expected2_name)
        self.assertEqual(result2_version, expected2_version)
        self.assertEqual(result3_name, expected3_name)
        self.assertEqual(result3_version, expected3_version)
        self.assertEqual(result4_name, expected2_name)
        self.assertEqual(result4_version, expected2_version)

    @mock.patch("requests.get")
    def test_scanpipe_maven_is_maven_pom_url_valid(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = '<?xml version="1.0"?><project></project>'
        mock_get.return_value = mock_response

        result = maven.is_maven_pom_url(
            "https://repo1.maven.org/maven2/example/example.pom"
        )
        self.assertTrue(result)

    @mock.patch("requests.get")
    def test_scanpipe_maven_is_maven_pom_url_404(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = maven.is_maven_pom_url(
            "https://repo.maven.apache.org/maven2/example/404.pom"
        )
        self.assertFalse(result)

    @mock.patch("requests.get")
    def test_scanpipe_maven_is_maven_pom_url_error(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html>Error page</html>"
        mock_get.return_value = mock_response

        result = maven.is_maven_pom_url(
            "https://repo.maven.apache.org/maven2/example/error.pom"
        )
        self.assertFalse(result)

    @mock.patch("scanpipe.pipes.maven.fetch.fetch_http")
    def test_scanpipe_maven_download_pom_files(self, mock_fetch_http):
        mock_response = mock.Mock()
        mock_response.path = "/safe/example1.pom"
        mock_fetch_http.return_value = mock_response

        pom_urls = ["https://repo1.maven.org/maven2/example/example1.pom"]

        expected = [
            {
                "pom_file_path": "/safe/example1.pom",
                "output_path": "/safe/example1.pom-output.json",
                "pom_url": "https://repo1.maven.org/maven2/example/example1.pom",
            }
        ]

        result = maven.download_pom_files(pom_urls)
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

        pom_file_list = [
            {
                "pom_file_path": "/safe/mock.pom",
                "output_path": "/safe/mock.pom-output.json",
                "pom_url": "https://repo1.maven.org/maven2/example/example.pom",
            }
        ]

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

        packages, deps = maven.update_datafile_paths(pom_file_list)

        self.assertEqual(packages, expected_packages)
        self.assertEqual(deps, expected_deps)

    @mock.patch("scanpipe.pipes.maven.is_maven_pom_url")
    @mock.patch("scanpipe.pipes.maven.requests.get")
    def test_scanpipe_maven_construct_pom_url_from_filename(
        self, mock_get, mock_is_maven_pom_url
    ):
        # Setup mock response from Maven Central
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "response": {"docs": [{"g": "org.apache.commons"}]}
        }
        mock_get.return_value = mock_response
        mock_is_maven_pom_url.return_value = True

        # Inputs
        artifact_id = "commons-lang3"
        version = "3.12.0"

        expected_url = [
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"
        ]

        result = maven.construct_pom_url_from_filename(artifact_id, version)

        self.assertEqual(result, expected_url)
        mock_get.assert_called_once_with(
            "https://search.maven.org/solrsearch/select?q=a:commons-lang3&wt=json",
            timeout=5,
        )
        mock_is_maven_pom_url.assert_called_once_with(expected_url[0])

    def test_scanpipe_maven_get_pom_url_list_with_packages(self):
        packages = [
            {
                "type": "maven",
                "namespace": "org.apache.commons",
                "name": "commons-lang3",
                "version": "3.12.0",
            }
        ]
        result = maven.get_pom_url_list({}, packages)
        expected = [
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"
        ]
        self.assertEqual(result, expected)

    def test_scanpipe_maven_get_pom_url_list_with_non_maven_packages(self):
        packages = [
            {
                "type": "jar",
                "namespace": "",
                "name": "spring-context",
                "version": "7.0.0",
            }
        ]
        result = maven.get_pom_url_list({}, packages)
        expected = []
        self.assertEqual(result, expected)

    def test_scanpipe_maven_get_pom_url_list_with_maven_download_url(self):
        input_source = {
            "download_url": "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar"
        }
        result = maven.get_pom_url_list(input_source, [])
        expected = [
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"
        ]
        self.assertEqual(result, expected)

    @mock.patch("scanpipe.pipes.maven.construct_pom_url_from_filename")
    @mock.patch("scanpipe.pipes.maven.parse_maven_filename")
    def test_scanpipe_maven_get_pom_url_list_with_jar_filename(
        self, mock_parse, mock_construct
    ):
        input_source = {"filename": "commons-lang3-3.12.0.jar"}
        mock_parse.return_value = ("commons-lang3", "3.12.0")
        mock_construct.return_value = [
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"
        ]
        result = maven.get_pom_url_list(input_source, [])
        self.assertEqual(result, mock_construct.return_value)

    def test_scanpipe_maven_get_pom_url_list_with_invalid_filename(self):
        input_source = {"filename": "not-a-jar.txt"}
        result = maven.get_pom_url_list(input_source, [])
        self.assertEqual(result, [])

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

    def test_scanpipe_maven_contains_ignore_pattern(self):
        ignore_patterns = ["*example/*", "*.sh", "*test/*"]

        self.assertTrue(
            maven.contains_ignore_pattern(
                "src/com/example/Example.class", ignore_patterns
            )
        )
        self.assertFalse(
            maven.contains_ignore_pattern("docs/README.md", ignore_patterns)
        )
        self.assertTrue(
            maven.contains_ignore_pattern(
                "src/com/project/test/Test.java", ignore_patterns
            )
        )
        self.assertTrue(
            maven.contains_ignore_pattern("src/com/project/conf.sh", ignore_patterns)
        )

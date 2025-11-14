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

import json
from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe import pipes
from scanpipe.models import Project
from scanpipe.pipes import resolve
from scanpipe.pipes import spdx
from scanpipe.pipes.input import copy_inputs
from scanpipe.pipes.scancode import extract_archives
from scanpipe.tests import make_package
from scanpipe.tests import make_project
from scanpipe.tests import package_data1


class ScanPipeResolvePipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"
    manifest_location = data / "manifests"

    def test_scanpipe_pipes_resolve_get_default_package_type(self):
        self.assertIsNone(resolve.get_default_package_type(input_location=""))

        input_location = self.manifest_location / "Django-4.0.8-py3-none-any.whl.ABOUT"
        self.assertEqual("about", resolve.get_default_package_type(input_location))

        input_location = self.manifest_location / "toml.spdx.json"
        self.assertEqual("spdx", resolve.get_default_package_type(input_location))

        input_location = self.manifest_location / "curl-7.70.0-v2.2.spdx.yml"
        self.assertEqual("spdx", resolve.get_default_package_type(input_location))

        input_location = self.manifest_location / "toml.json"
        self.assertEqual("spdx", resolve.get_default_package_type(input_location))

        input_location = self.manifest_location / "curl-7.70.0.yaml"
        self.assertEqual("spdx", resolve.get_default_package_type(input_location))

        input_location = self.data / "cyclonedx/nested.cdx.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

        input_location = self.data / "cyclonedx/asgiref-3.3.0.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

        input_location = self.data / "cyclonedx/missing_schema.json"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

        input_location = self.data / "cyclonedx/laravel-7.12.0/bom.1.4.xml"
        self.assertEqual("cyclonedx", resolve.get_default_package_type(input_location))

    def test_scanpipe_pipes_resolve_set_license_expression(self):
        extracted_license_statement = {"license": "MIT"}
        data = resolve.set_license_expression(
            {"extracted_license_statement": extracted_license_statement}
        )
        self.assertEqual("mit", data.get("declared_license_expression"))

        extracted_license_statement = {
            "classifiers": [
                "License :: OSI Approved :: Python Software Foundation License"
            ]
        }
        data = resolve.set_license_expression(
            {"extracted_license_statement": extracted_license_statement}
        )
        self.assertEqual("python", data.get("declared_license_expression"))

        extracted_license_statement = "GPL 2.0"
        data = resolve.set_license_expression(
            {"extracted_license_statement": extracted_license_statement}
        )
        self.assertEqual("gpl-2.0", data.get("declared_license_expression"))

    def test_scanpipe_pipes_resolve_convert_spdx_expression(self):
        spdx = "MIT OR GPL-2.0-only WITH LicenseRef-scancode-generic-exception"
        scancode_expression = "mit OR gpl-2.0 WITH generic-exception"
        self.assertEqual(scancode_expression, resolve.convert_spdx_expression(spdx))

    def test_scanpipe_pipes_resolve_get_packages_from_manifest(self):
        # ScanCode.io resolvers
        input_location = self.manifest_location / "Django-4.0.8-py3-none-any.whl.ABOUT"
        packages = resolve.get_packages_from_manifest(
            input_location=str(input_location),
            package_registry=resolve.sbom_registry,
        )
        expected = {
            "filename": "Django-4.0.8-py3-none-any.whl",
            "download_url": "https://python.org/Django-4.0.8-py3-none-any.whl",
            "declared_license_expression": "bsd-new",
            "extra_data": {"license_file": "bsd-new.LICENSE"},
            "extracted_license_statement": None,
            "md5": "386349753c386e574dceca5067e2788a",
            "name": "django",
            "sha1": "4cc6f7abda928a0b12cd1f1cd8ad3677519ca04e",
            "type": "pypi",
            "version": "4.0.8",
        }
        self.assertEqual([expected], packages)

    @mock.patch("scanpipe.pipes.resolve.python_inspector.resolve_dependencies")
    def test_scanpipe_pipes_resolve_resolve_pypi_packages(self, mock_resolve):
        # Generated with:
        # $ python-inspector --python-version 3.12 --operating-system linux \
        #     --specifier pip==25.0.1 --json -
        inspector_output_location = (
            self.data / "resolve" / "python_inspector_resolve_dependencies.json"
        )
        with open(inspector_output_location) as f:
            inspector_output = json.loads(f.read())

        mock_resolve.return_value = mock.Mock(packages=inspector_output["packages"])

        packages = resolve.resolve_pypi_packages("")
        self.assertEqual(2, len(packages))
        package_data = packages[0]
        self.assertEqual("pip", package_data["name"])
        self.assertEqual("25.0.1", package_data["version"])
        self.assertEqual("Python", package_data["primary_language"])
        self.assertIsNone(package_data["license_expression"])
        expected_license = {
            "license": "MIT",
            "classifiers": ["License :: OSI Approved :: MIT License"],
        }
        self.assertEqual(expected_license, package_data["extracted_license_statement"])

        project = make_project()
        resolve.create_packages_and_dependencies(
            project=project,
            packages=packages,
            resolved=True,
        )

        self.assertEqual(2, project.discoveredpackages.count())

        package = project.discoveredpackages.all()[0]
        self.assertEqual(str(expected_license), package.extracted_license_statement)

    def test_scanpipe_pipes_resolve_resolve_about_packages(self):
        input_location = self.manifest_location / "Django-4.0.8-py3-none-any.whl.ABOUT"
        package = resolve.resolve_about_packages(str(input_location))
        expected = {
            "filename": "Django-4.0.8-py3-none-any.whl",
            "download_url": "https://python.org/Django-4.0.8-py3-none-any.whl",
            "declared_license_expression": "bsd-new",
            "extra_data": {"license_file": "bsd-new.LICENSE"},
            "extracted_license_statement": None,
            "md5": "386349753c386e574dceca5067e2788a",
            "name": "django",
            "sha1": "4cc6f7abda928a0b12cd1f1cd8ad3677519ca04e",
            "type": "pypi",
            "version": "4.0.8",
        }
        self.assertEqual([expected], package)

        input_location = self.manifest_location / "poor_values.ABOUT"
        package = resolve.resolve_about_packages(str(input_location))
        expected = {"extra_data": {}, "name": "project"}
        self.assertEqual([expected], package)

    def test_scanpipe_pipes_resolve_get_spdx_document_from_file(self):
        input_location = self.data / "spdx" / "SPDXJSONExample-v2.3.spdx.json"
        spdx_document = resolve.get_spdx_document_from_file(input_location)
        self.assertIsInstance(spdx_document, dict)
        self.assertEqual("SPDXRef-DOCUMENT", spdx_document["SPDXID"])
        self.assertEqual("SPDX-2.3", spdx_document["spdxVersion"])

        input_location = self.data / "manifests" / "curl-7.70.0-v2.2.spdx.yml"
        spdx_document = resolve.get_spdx_document_from_file(input_location)
        self.assertIsInstance(spdx_document, dict)
        self.assertEqual("SPDXRef-DOCUMENT", spdx_document["SPDXID"])
        self.assertEqual("SPDX-2.2", spdx_document["spdxVersion"])

    def test_scanpipe_pipes_resolve_spdx_package_to_package_data(self):
        p1 = Project.objects.create(name="Analysis")
        package = pipes.update_or_create_package(p1, package_data1)
        package_spdx = package.as_spdx()
        package_data = resolve.spdx_package_to_package_data(package_spdx)
        expected = {
            "package_uid": package.spdx_id,
            "name": "adduser",
            "download_url": "https://download.url/package.zip",
            "declared_license_expression": "gpl-2.0 AND gpl-2.0-plus",
            "declared_license_expression_spdx": "GPL-2.0-only AND GPL-2.0-or-later",
            "extracted_license_statement": "GPL-2.0-only AND GPL-2.0-or-later",
            "copyright": (
                "Copyright (c) 2000 Roland Bauerschmidt <rb@debian.org>\n"
                "Copyright (c) 1997, 1998, 1999 Guy Maor <maor@debian.org>\n"
                "Copyright (c) 1995 Ted Hajek <tedhajek@boombox.micro.umn.edu>\n"
                "portions Copyright (c) 1994 Debian Association, Inc."
            ),
            "version": "3.118",
            "homepage_url": "https://packages.debian.org",
            "filename": "package.zip",
            "description": "add and remove users and groups",
            "release_date": "1999-10-10",
            "type": "deb",
            "namespace": "debian",
            "qualifiers": "arch=all",
            "md5": "76cf50f29e47676962645632737365a7",
        }
        self.assertEqual(expected, package_data)

    def test_scanpipe_pipes_spdx_relationship_to_dependency_data(self):
        spdx_relationship_data = {
            "spdxElementId": "SPDXRef-package1",
            "relatedSpdxElement": "SPDXRef-package2",
            "relationshipType": "CONTAINS",
        }
        spdx_relationship = spdx.Relationship.from_data(spdx_relationship_data)
        dependency_data = resolve.spdx_relationship_to_dependency_data(
            spdx_relationship
        )
        expected = {
            "for_package_uid": "SPDXRef-package1",
            "resolve_to_package_uid": "SPDXRef-package2",
            "is_runtime": True,
            "is_resolved": True,
            "is_direct": True,
        }
        self.assertEqual(expected, dependency_data)

    def test_scanpipe_pipes_resolve_spdx_packages(self):
        input_location = self.data / "spdx" / "SPDXJSONExample-v2.3.spdx.json"
        packages_data = resolve.resolve_spdx_packages(input_location)
        self.assertEqual(4, len(packages_data))

    def test_scanpipe_pipes_resolve_spdx_dependencies(self):
        input_location = self.data / "spdx" / "SPDXJSONExample-v2.3.spdx.json"
        dependencies_data = resolve.resolve_spdx_dependencies(input_location)
        self.assertEqual(6, len(dependencies_data))

    def test_scanpipe_pipes_resolve_spdx_dependencies_noassertion(self):
        input_location = self.data / "spdx" / "noassertion.spdx.json"
        dependencies_data = resolve.resolve_spdx_dependencies(input_location)
        self.assertEqual(1, len(dependencies_data))

    def test_scanpipe_resolve_get_manifest_resources(self):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "manifests" / "python-inspector-0.10.0.zip"
        project1.copy_input_from(input_location)
        copy_inputs(project1.inputs(), project1.codebase_path)

        extract_archives(project1.codebase_path, recurse=True)
        pipes.collect_and_create_codebase_resources(project1)

        resources = resolve.get_manifest_resources(project1)
        self.assertTrue(resources.exists())
        requirements_resource = project1.codebaseresources.get(
            path=(
                "python-inspector-0.10.0.zip-extract/"
                "python-inspector-0.10.0/requirements.txt"
            )
        )
        self.assertIn(requirements_resource, resources)

    def test_scanpipe_resolve_get_packages_from_sbom(self):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "manifests" / "toml.spdx.json"

        project1.copy_input_from(input_location)
        copy_inputs(project1.inputs(), project1.codebase_path)
        pipes.collect_and_create_codebase_resources(project1)
        resources = resolve.get_manifest_resources(project1)

        packages, _ = resolve.get_data_from_manifests(
            project1,
            resolve.sbom_registry,
            resources,
        )
        self.assertEqual(1, len(packages))
        package = packages[0]
        self.assertEqual("toml", package["name"])
        resource1 = project1.codebaseresources.get(name="toml.spdx.json")
        self.assertEqual([resource1], package.get("codebase_resources"))

        self.assertEqual(["sboms_headers"], list(project1.extra_data.keys()))
        sboms_headers = project1.extra_data["sboms_headers"]
        self.assertEqual(["toml.spdx.json"], list(sboms_headers.keys()))
        expected = [
            "spdxVersion",
            "dataLicense",
            "SPDXID",
            "name",
            "documentNamespace",
            "creationInfo",
            "comment",
        ]
        self.assertEqual(expected, list(sboms_headers["toml.spdx.json"].keys()))

    def test_scanpipe_resolve_create_packages_and_dependencies(self):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "manifests" / "toml.spdx.json"

        project1.copy_input_from(input_location)
        copy_inputs(project1.inputs(), project1.codebase_path)
        pipes.collect_and_create_codebase_resources(project1)
        resources = resolve.get_manifest_resources(project1)
        packages, _ = resolve.get_data_from_manifests(
            project1,
            resolve.sbom_registry,
            resources,
        )
        resolve.create_packages_and_dependencies(project1, packages)
        self.assertEqual(1, project1.discoveredpackages.count())
        self.assertEqual(0, project1.discovereddependencies.count())

        resource1 = project1.codebaseresources.get(name="toml.spdx.json")
        package = project1.discoveredpackages.get()
        self.assertEqual(resource1, package.codebase_resources.get())

    def test_scanpipe_resolve_create_dependencies_from_packages_extra_data(self):
        p1 = Project.objects.create(name="Analysis")

        parent = make_package(
            p1, "pkg:type/parent", extra_data={"depends_on": ["child"]}
        )
        child = make_package(p1, "pkg:type/child", package_uid="child")

        created_count = resolve.create_dependencies_from_packages_extra_data(p1)
        self.assertEqual(1, created_count)
        dependency = p1.discovereddependencies.get()
        self.assertEqual(parent, dependency.for_package)
        self.assertEqual(child, dependency.resolved_to_package)
        self.assertTrue(dependency.is_runtime)
        self.assertTrue(dependency.is_pinned)
        self.assertTrue(dependency.is_direct)
        self.assertFalse(dependency.is_optional)

        parent.update_extra_data({"depends_on": ["unknown"]})
        created_count = resolve.create_dependencies_from_packages_extra_data(p1)
        self.assertEqual(0, created_count)
        message = p1.projectmessages.get()
        self.assertEqual("error", message.severity)
        self.assertEqual(
            "Could not find resolved_to package entry: unknown.", message.description
        )
        self.assertEqual("create_dependencies", message.model)

    def test_scanpipe_resolve_get_manifest_headers(self):
        input_location = self.data / "manifests" / "toml.spdx.json"
        resource = mock.Mock(location=input_location)
        expected = [
            "spdxVersion",
            "dataLicense",
            "SPDXID",
            "name",
            "documentNamespace",
            "creationInfo",
            "comment",
        ]
        headers = resolve.get_manifest_headers(resource)
        self.assertEqual(expected, list(headers.keys()))

    def test_scanpipe_resolve_parse_maven_filename(self):
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

        result1_name, result1_version = resolve.parse_maven_filename(test1)
        result2_name, result2_version = resolve.parse_maven_filename(test2)
        result3_name, result3_version = resolve.parse_maven_filename(test3)
        result4_name, result4_version = resolve.parse_maven_filename(test4)

        self.assertEqual(result1_name, expected1_name)
        self.assertEqual(result1_version, expected1_version)
        self.assertEqual(result2_name, expected2_name)
        self.assertEqual(result2_version, expected2_version)
        self.assertEqual(result3_name, expected3_name)
        self.assertEqual(result3_version, expected3_version)
        self.assertEqual(result4_name, expected2_name)
        self.assertEqual(result4_version, expected2_version)

    @mock.patch("requests.get")
    def test_scanpipe_resolve_is_maven_pom_url_valid(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = '<?xml version="1.0"?><project></project>'
        mock_get.return_value = mock_response

        result = resolve.is_maven_pom_url(
            "https://repo1.maven.org/maven2/example/example.pom"
        )
        self.assertTrue(result)

    @mock.patch("requests.get")
    def test_scanpipe_resolve_is_maven_pom_url_404(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = resolve.is_maven_pom_url(
            "https://repo.maven.apache.org/maven2/example/404.pom"
        )
        self.assertFalse(result)

    @mock.patch("requests.get")
    def test_scanpipe_resolve_is_maven_pom_url_error(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html>Error page</html>"
        mock_get.return_value = mock_response

        result = resolve.is_maven_pom_url(
            "https://repo.maven.apache.org/maven2/example/error.pom"
        )
        self.assertFalse(result)

    @mock.patch("scanpipe.pipes.resolve.fetch.fetch_http")
    def test_scanpipe_resolve_download_pom_files(self, mock_fetch_http):
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

        result = resolve.download_pom_files(pom_urls)
        self.assertEqual(result, expected)

    @mock.patch("scanpipe.pipes.resolve.scancode.run_scan")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    def test_scanpipe_resolve_scan_pom_files(
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

        packages, deps = resolve.scan_pom_files(pom_file_list)

        self.assertEqual(packages, expected_packages)
        self.assertEqual(deps, expected_deps)

        mock_run_scan.assert_called_once_with(
            location="/safe/mock.pom",
            output_file="/safe/mock.pom-output.json",
            run_scan_args={"package": True},
        )
        mock_open.assert_called_once_with("/safe/mock.pom-output.json")
        mock_json_load.assert_called_once()

    @mock.patch("scanpipe.pipes.resolve.is_maven_pom_url")
    @mock.patch("scanpipe.pipes.resolve.requests.get")
    def test_scanpipe_resolve_construct_pom_url_from_filename(
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

        result = resolve.construct_pom_url_from_filename(artifact_id, version)

        self.assertEqual(result, expected_url)
        mock_get.assert_called_once_with(
            "https://search.maven.org/solrsearch/select?q=a:commons-lang3&wt=json",
            timeout=5,
        )
        mock_is_maven_pom_url.assert_called_once_with(expected_url[0])

    def test_scanpipe_resolve_get_pom_url_list_with_packages(self):
        packages = [
            {
                "namespace": "org.apache.commons",
                "name": "commons-lang3",
                "version": "3.12.0",
            }
        ]
        result = resolve.get_pom_url_list({}, packages)
        expected = [
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"
        ]
        self.assertEqual(result, expected)

    def test_scanpipe_resolve_get_pom_url_list_with_maven_download_url(self):
        input_source = {
            "download_url": "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar"
        }
        result = resolve.get_pom_url_list(input_source, [])
        expected = [
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"
        ]
        self.assertEqual(result, expected)

    @mock.patch("scanpipe.pipes.resolve.construct_pom_url_from_filename")
    @mock.patch("scanpipe.pipes.resolve.parse_maven_filename")
    def test_scanpipe_resolve_get_pom_url_list_with_jar_filename(
        self, mock_parse, mock_construct
    ):
        input_source = {"filename": "commons-lang3-3.12.0.jar"}
        mock_parse.return_value = ("commons-lang3", "3.12.0")
        mock_construct.return_value = [
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.pom"
        ]
        result = resolve.get_pom_url_list(input_source, [])
        self.assertEqual(result, mock_construct.return_value)

    def test_scanpipe_resolve_get_pom_url_list_with_invalid_filename(self):
        input_source = {"filename": "not-a-jar.txt"}
        result = resolve.get_pom_url_list(input_source, [])
        self.assertEqual(result, [])

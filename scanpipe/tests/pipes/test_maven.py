# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from pathlib import Path
from unittest import mock

from django.test import TestCase

import defusedxml.ElementTree as ET
from packageurl import PackageURL

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import flag
from scanpipe.pipes import maven
from scanpipe.pipes.input import copy_inputs
from scanpipe.pipes.input import load_inventory_from_toolkit_scan


class ScanPipeMavenPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def _make_package(self, namespace, name):
        """Return a mock package."""
        package = mock.Mock()
        package.namespace = namespace
        package.name = name
        return package

    def _build_pom_tree(self, pom_content):
        """Return a mock resource and mock tree."""
        root = ET.fromstring(pom_content)
        mock_tree = mock.Mock()
        mock_tree.getroot.return_value = root
        mock_resource = mock.Mock()
        mock_resource.location = "/fake/pom.xml"
        return mock_resource, mock_tree

    def _create_maven_package(self, project, namespace, name, version):
        """Create a Maven DiscoveredPackage and return it."""
        purl = f"pkg:maven/{namespace}/{name}@{version}"
        return DiscoveredPackage.objects.create(
            project=project,
            type="maven",
            namespace=namespace,
            name=name,
            version=version,
            package_uid=purl,
        )

    def _create_resource(self, project, path, tag="to", status="", name=None):
        """Create a CodebaseResource with the extension derived from the path."""
        return CodebaseResource.objects.create(
            project=project,
            path=path,
            type=CodebaseResource.Type.FILE,
            tag=tag,
            name=name or Path(path).name,
            extension=Path(path).suffix,
            status=status,
        )

    def _setup_project_with_shaded_classes(self):
        """
        Return a project with htrace-core as the main package and
        commons-logging and jackson-annotations as dependencies.
        """
        project = Project.objects.create(name="Analysis")
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._create_maven_package(
            project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        # Dependency packages.
        commons = self._create_maven_package(
            project, "commons-logging", "commons-logging", "1.1.1"
        )
        jackson = self._create_maven_package(
            project, "com.fasterxml.jackson.core", "jackson-annotations", "2.4.0"
        )
        return project, main_purl, commons, jackson

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
        self.assertEqual(
            result, [{"pkg:maven/org/test@1.0": ["Failed to resolve POM URL."]}]
        )

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
        self.assertEqual(
            result,
            [{"https://example.com/test.pom": ["Failed to download the POM file."]}],
        )

    def test_update_scan_data(self):
        original_data = {
            "packages": [{"name": "package1"}],
            "dependencies": [{"name": "dep1"}],
        }
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

    def test_scanpipe_maven_strip_xml_namespace(self):
        self.assertEqual(
            maven._strip_xml_namespace("{http://maven.apache.org/POM/4.0.0}plugin"),
            "plugin",
        )
        self.assertEqual(maven._strip_xml_namespace("plugin"), "plugin")
        self.assertEqual(maven._strip_xml_namespace(""), "")

    def test_scanpipe_maven_get_java_fqn_from_class_path_simple(self):
        self.assertEqual(
            maven.get_java_fqn_from_class_path("to/org/apache/htrace/Foo.class"),
            "org.apache.htrace.Foo",
        )

    def test_scanpipe_maven_get_java_fqn_from_class_path_inner_class(self):
        self.assertEqual(
            maven.get_java_fqn_from_class_path("to/org/apache/htrace/Foo$Bar.class"),
            "org.apache.htrace.Foo",
        )

    def test_scanpipe_maven_get_java_fqn_from_class_path_from_side(self):
        self.assertEqual(
            maven.get_java_fqn_from_class_path("from/com/example/Bar.class"),
            "com.example.Bar",
        )

    def test_scanpipe_maven_get_java_fqn_from_class_path_extracted(self):
        self.assertEqual(
            maven.get_java_fqn_from_class_path(
                "to/lib.jar-extract/com/example/Baz.class"
            ),
            "com.example.Baz",
        )

    def test_scanpipe_maven_apply_shade_relocations_match(self):
        relocations = {
            "org.apache.htrace.commons.logging": "org.apache.commons.logging",
            "org.apache.htrace.fasterxml.jackson": "com.fasterxml.jackson",
        }
        self.assertEqual(
            maven.apply_shade_relocations(
                "org.apache.htrace.commons.logging.impl.AvalonLogger", relocations
            ),
            "org.apache.commons.logging.impl.AvalonLogger",
        )
        self.assertEqual(
            maven.apply_shade_relocations(
                "org.apache.htrace.fasterxml.jackson.annotation.JsonTypeId",
                relocations,
            ),
            "com.fasterxml.jackson.annotation.JsonTypeId",
        )

    def test_scanpipe_maven_apply_shade_relocations_exact_match(self):
        relocations = {
            "org.apache.htrace.commons.logging": "org.apache.commons.logging"
        }
        self.assertEqual(
            maven.apply_shade_relocations(
                "org.apache.htrace.commons.logging", relocations
            ),
            "org.apache.commons.logging",
        )

    def test_scanpipe_maven_apply_shade_relocations_no_boundary(self):
        relocations = {"org.foo": "com.foo"}
        self.assertEqual(
            maven.apply_shade_relocations("org.foobar.Class", relocations),
            "org.foobar.Class",
        )

    def test_scanpipe_maven_apply_shade_relocations_no_match(self):
        relocations = {
            "org.apache.htrace.commons.logging": "org.apache.commons.logging"
        }
        self.assertEqual(
            maven.apply_shade_relocations("org.example.Foo", relocations),
            "org.example.Foo",
        )

    def test_scanpipe_maven_apply_shade_relocations_longest_pattern_wins(self):
        relocations = {
            "org.foo": "com.foo",
            "org.foo.bar": "com.bar",
        }
        self.assertEqual(
            maven.apply_shade_relocations("org.foo.bar.Baz", relocations),
            "com.bar.Baz",
        )

    def test_scanpipe_maven_apply_shade_relocations_empty(self):
        self.assertEqual(
            maven.apply_shade_relocations("org.example.Foo", {}),
            "org.example.Foo",
        )

    def test_scanpipe_maven_fuzzy_segment_match(self):
        # Plural vs singular
        self.assertTrue(maven._fuzzy_segment_match("annotation", "annotations"))
        # Identical strings
        self.assertTrue(maven._fuzzy_segment_match("logging", "logging"))
        # Non-matched strings
        self.assertFalse(maven._fuzzy_segment_match("core", "annotation"))
        # Empty and None
        self.assertFalse(maven._fuzzy_segment_match("", "annotation"))
        self.assertFalse(maven._fuzzy_segment_match("logging", None))
        self.assertFalse(maven._fuzzy_segment_match(None, None))

    def test_scanpipe_maven_score_dependency_for_fqn_commons_logging(self):
        package = self._make_package("commons-logging", "commons-logging")
        score, signals = maven.score_dependency_for_fqn(
            "org.apache.commons.logging.impl.AvalonLogger", package
        )
        # group: "commons" + "logging" -> +2
        # artifact: "commons" + "logging" -> +4
        # fuzzy: "logging" vs "impl" -> no
        self.assertEqual(score, 6)
        self.assertEqual(signals, {"group", "artifact"})

    def test_scanpipe_maven_score_dependency_for_fqn_jackson(self):
        package = self._make_package(
            "com.fasterxml.jackson.core", "jackson-annotations"
        )
        score, signals = maven.score_dependency_for_fqn(
            "com.fasterxml.jackson.annotation.JsonTypeId", package
        )
        # group: "com" + "fasterxml" + "jackson" -> +3
        # artifact: "jackson" -> +2
        # fuzzy: "annotations" vs "annotation" -> +3
        self.assertEqual(score, 8)
        self.assertEqual(signals, {"group", "artifact", "fuzzy"})

    def test_scanpipe_maven_score_dependency_for_fqn_no_package_segments(self):
        # A single-segment FQN (no package, just a class) has no package segments.
        package = self._make_package("commons-logging", "commons-logging")
        self.assertEqual(maven.score_dependency_for_fqn("Foo", package), (0, set()))

    def test_scanpipe_maven_match_shaded_class_to_package_clear_winner(self):
        commons = self._make_package("commons-logging", "commons-logging")
        jackson = self._make_package(
            "com.fasterxml.jackson.core", "jackson-annotations"
        )
        result = maven.match_shaded_class_to_package(
            "org.apache.commons.logging.impl.AvalonLogger",
            [commons, jackson],
        )
        self.assertIsNotNone(result)
        matched_package, score, signals = result
        self.assertIs(matched_package, commons)
        self.assertEqual(score, 6)
        self.assertEqual(signals, {"group", "artifact"})

    def test_scanpipe_maven_match_shaded_class_to_package_tie(self):
        # Two versions of the same dependency score identically.
        pkg_v1 = self._make_package("commons-logging", "commons-logging")
        pkg_v1.version = "1.1.1"
        pkg_v2 = self._make_package("commons-logging", "commons-logging")
        pkg_v2.version = "1.2.0"
        result = maven.match_shaded_class_to_package(
            "org.apache.commons.logging.impl.AvalonLogger",
            [pkg_v1, pkg_v2],
        )
        self.assertIsNone(result)

    def test_scanpipe_maven_get_maven_shade_relocations(self):
        pom_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-jar-plugin</artifactId>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-shade-plugin</artifactId>
        <configuration>
          <relocations>
            <relocation>
              <pattern>org.apache.commons.logging</pattern>
              <shadedPattern>org.apache.htrace.commons.logging</shadedPattern>
            </relocation>
            <relocation>
              <pattern>com.fasterxml.jackson</pattern>
              <shadedPattern>org.apache.htrace.fasterxml.jackson</shadedPattern>
            </relocation>
          </relocations>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""
        pom_resource, tree = self._build_pom_tree(pom_content)
        with mock.patch.object(maven.ET, "parse", return_value=tree):
            result = maven.get_maven_shade_relocations(pom_resource)

        self.assertEqual(
            result,
            {
                "org.apache.htrace.commons.logging": "org.apache.commons.logging",
                "org.apache.htrace.fasterxml.jackson": "com.fasterxml.jackson",
            },
        )

    def test_scanpipe_maven_get_maven_shade_relocations_no_shade_plugin(self):
        pom_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <build>
    <plugins>
      <plugin>
        <artifactId>maven-jar-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
"""
        pom_resource, tree = self._build_pom_tree(pom_content)
        with mock.patch.object(maven.ET, "parse", return_value=tree):
            result = maven.get_maven_shade_relocations(pom_resource)
        self.assertEqual(result, {})

    def test_scanpipe_maven_get_maven_shade_relocations_no_relocations(self):
        pom_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <build>
    <plugins>
      <plugin>
        <artifactId>maven-shade-plugin</artifactId>
        <configuration>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""
        pom_resource, tree = self._build_pom_tree(pom_content)
        with mock.patch.object(maven.ET, "parse", return_value=tree):
            result = maven.get_maven_shade_relocations(pom_resource)
        self.assertEqual(result, {})

    def test_scanpipe_maven_get_maven_dependency_packages(self):
        project = Project.objects.create(name="Analysis")
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        main_package = self._create_maven_package(
            project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        dep_commons = self._create_maven_package(
            project, "commons-logging", "commons-logging", "1.1.1"
        )
        dep_jackson = self._create_maven_package(
            project, "com.fasterxml.jackson.core", "jackson-annotations", "2.4.0"
        )
        # Non-Maven package should not be returned.
        DiscoveredPackage.objects.create(
            project=project,
            type="npm",
            namespace="example",
            name="foo",
            version="1.0.0",
            package_uid="pkg:npm/example/foo@1.0.0",
        )

        result = maven.get_maven_dependency_packages(project, main_purl)

        self.assertEqual(len(result), 2)
        self.assertIn(dep_commons, result)
        self.assertIn(dep_jackson, result)
        self.assertNotIn(main_package, result)

    def test_scanpipe_maven_get_maven_dependency_packages_no_main_purl(self):
        project = Project.objects.create(name="Analysis")
        dep1 = self._create_maven_package(
            project, "commons-logging", "commons-logging", "1.1.1"
        )
        dep2 = self._create_maven_package(
            project, "com.fasterxml.jackson.core", "jackson-annotations", "2.4.0"
        )
        result = maven.get_maven_dependency_packages(project, None)
        self.assertEqual(len(result), 2)
        self.assertIn(dep1, result)
        self.assertIn(dep2, result)

    def test_scanpipe_maven_get_main_maven_pom_found(self):
        project = Project.objects.create(name="Analysis")
        expected = self._create_resource(
            project,
            "to/META-INF/maven/org.apache.htrace/htrace-core/pom.xml",
        )
        self._create_resource(
            project,
            "to/META-INF/maven/commons-logging/commons-logging/pom.xml",
        )

        purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        result = maven.get_main_maven_pom(project, purl)
        self.assertEqual(result, expected)

    def test_scanpipe_maven_get_main_maven_pom_purl_without_namespace(self):
        project = Project.objects.create(name="Analysis")
        # A PURL without a namespace cannot be matched.
        purl = mock.Mock()
        purl.namespace = None
        purl.name = "foo"
        self.assertIsNone(maven.get_main_maven_pom(project, purl))

    def test_scanpipe_maven_map_shaded_classes_attributions(self):
        project, main_purl, commons, jackson = self._setup_project_with_shaded_classes()

        commons_class = self._create_resource(
            project,
            "to/org/apache/htrace/commons/logging/impl/AvalonLogger.class",
            status=flag.REQUIRES_REVIEW,
        )
        jackson_class = self._create_resource(
            project,
            "to/org/apache/htrace/fasterxml/jackson/annotation/JsonTypeId.class",
            status=flag.REQUIRES_REVIEW,
        )
        unrelated_class = self._create_resource(
            project,
            "to/com/example/Unrelated.class",
            status=flag.REQUIRES_REVIEW,
        )

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        commons_class.refresh_from_db()
        self.assertEqual(commons_class.status, flag.SHADED_CLASS)
        self.assertIn(commons, commons_class.discovered_packages.all())
        self.assertEqual(
            commons_class.extra_data.get("shaded_from_package"),
            "pkg:maven/commons-logging/commons-logging@1.1.1",
        )
        self.assertGreaterEqual(commons_class.extra_data.get("match_score"), 5)
        self.assertIn("group", commons_class.extra_data.get("match_signals"))
        self.assertIn("artifact", commons_class.extra_data.get("match_signals"))

        jackson_class.refresh_from_db()
        self.assertEqual(jackson_class.status, flag.SHADED_CLASS)
        self.assertIn(jackson, jackson_class.discovered_packages.all())
        self.assertEqual(
            jackson_class.extra_data.get("shaded_from_package"),
            "pkg:maven/com.fasterxml.jackson.core/jackson-annotations@2.4.0",
        )
        self.assertGreaterEqual(jackson_class.extra_data.get("match_score"), 5)
        self.assertIn("group", jackson_class.extra_data.get("match_signals"))
        self.assertIn("artifact", jackson_class.extra_data.get("match_signals"))

        # The unrelated class should stay as requires-review.
        unrelated_class.refresh_from_db()
        self.assertEqual(unrelated_class.status, flag.REQUIRES_REVIEW)
        self.assertEqual(unrelated_class.discovered_packages.count(), 0)

    def test_scanpipe_maven_map_shaded_classes_no_classes(self):
        project, main_purl, _, _ = self._setup_project_with_shaded_classes()

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        self.assertEqual(
            project.codebaseresources.filter(status=flag.SHADED_CLASS).count(),
            0,
        )

    def test_scanpipe_maven_map_shaded_classes_tie_is_not_attributed(self):
        project = Project.objects.create(name="Analysis")
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._create_maven_package(
            project, "commons-logging", "commons-logging", "1.1.1"
        )
        self._create_maven_package(
            project, "commons-logging", "commons-logging", "1.2.0"
        )

        common_class = self._create_resource(
            project,
            "to/org/apache/htrace/commons/logging/impl/AvalonLogger.class",
            status=flag.REQUIRES_REVIEW,
        )

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        common_class.refresh_from_db()
        self.assertEqual(common_class.status, flag.REQUIRES_REVIEW)
        self.assertEqual(common_class.discovered_packages.count(), 0)

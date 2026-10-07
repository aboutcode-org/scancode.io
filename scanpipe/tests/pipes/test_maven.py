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

from packageurl import PackageURL

from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import flag
from scanpipe.pipes import maven
from scanpipe.pipes.input import copy_inputs
from scanpipe.pipes.input import load_inventory_from_toolkit_scan
from scanpipe.tests import make_package
from scanpipe.tests import make_resource_file


class ScanPipeMavenPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project = Project.objects.create(name="Analysis")

    def _add_pom_resource(self, project, codebase_path, data_filename):
        """
        Copy the POM test data file into the project's codebase and return
        its CodebaseResource.
        """
        data_path = self.data / "maven" / data_filename
        target_path = project.codebase_path / codebase_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(data_path.read_text())
        return make_resource_file(project, codebase_path)

    def _make_maven_package(self, project, namespace, name, version):
        """Create a Maven DiscoveredPackage and return it."""
        purl = f"pkg:maven/{namespace}/{name}@{version}"
        return make_package(
            project,
            package_url=purl,
            type="maven",
            namespace=namespace,
            name=name,
            version=version,
            package_uid=purl,
        )

    def _setup_project_with_shaded_classes(self):
        """
        Return a project with htrace-core as the main package and
        commons-logging and jackson-annotations as dependencies.
        Also add the main POM that declares the shade relocations.
        """
        project = self.project
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._make_maven_package(
            project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        commons = self._make_maven_package(
            project, "commons-logging", "commons-logging", "1.1.1"
        )
        jackson = self._make_maven_package(
            project, "com.fasterxml.jackson.core", "jackson-annotations", "2.4.0"
        )
        self._add_pom_resource(
            project,
            "to/META-INF/maven/org.apache.htrace/htrace-core/pom.xml",
            "shaded-pom.xml",
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
        project1 = Project.objects.create(name="Analysis-missing-license")
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
        project1 = Project.objects.create(name="Analysis-existing-license")
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

    def test_scanpipe_maven_get_main_maven_pom_found(self):
        expected = make_resource_file(
            self.project,
            "to/META-INF/maven/org.apache.htrace/htrace-core/pom.xml",
        )
        make_resource_file(
            self.project,
            "to/META-INF/maven/commons-logging/commons-logging/pom.xml",
        )

        purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        result = maven.get_main_maven_pom(self.project, purl)
        self.assertEqual(result, expected)

    def test_scanpipe_maven_get_main_maven_pom_not_found(self):
        purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        result = maven.get_main_maven_pom(self.project, purl)
        self.assertIsNone(result)

    def test_scanpipe_maven_get_maven_shade_relocations(self):
        pom_resource = self._add_pom_resource(
            self.project, "to/pom.xml", "shaded-pom.xml"
        )
        result = maven.get_maven_shade_relocations(self.project, pom_resource)

        self.assertEqual(
            result,
            {
                "org.apache.htrace.commons.logging": "org.apache.commons.logging",
                "org.apache.htrace.fasterxml.jackson": "com.fasterxml.jackson",
            },
        )

    def test_scanpipe_maven_get_maven_shade_relocations_no_shade_plugin(self):
        pom_resource = self._add_pom_resource(
            self.project, "to/pom.xml", "no-shade-plugin-pom.xml"
        )
        result = maven.get_maven_shade_relocations(self.project, pom_resource)
        self.assertEqual(result, {})

    def test_scanpipe_maven_get_maven_shade_relocations_no_relocations(self):
        pom_resource = self._add_pom_resource(
            self.project, "to/pom.xml", "no-relocations-pom.xml"
        )
        result = maven.get_maven_shade_relocations(self.project, pom_resource)
        self.assertEqual(result, {})

    def test_scanpipe_maven_get_maven_shade_relocations_parse_failure(self):
        pom_resource = self._add_pom_resource(
            self.project, "to/pom.xml", "invalid-pom.xml"
        )
        result = maven.get_maven_shade_relocations(self.project, pom_resource)

        self.assertEqual(result, {})
        error = self.project.projectmessages.get(severity="error")
        self.assertIn("Cannot parse POM", error.description)
        self.assertEqual(error.details.get("resource_path"), "to/pom.xml")

    def test_scanpipe_maven_get_maven_dependency_packages(self):
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        main_package = self._make_maven_package(
            self.project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        dep_commons = self._make_maven_package(
            self.project, "commons-logging", "commons-logging", "1.1.1"
        )
        dep_jackson = self._make_maven_package(
            self.project, "com.fasterxml.jackson.core", "jackson-annotations", "2.4.0"
        )
        # Non-Maven package should not be returned.
        make_package(
            self.project,
            package_url="pkg:npm/example/foo@1.0.0",
            type="npm",
            namespace="example",
            name="foo",
            version="1.0.0",
            package_uid="pkg:npm/example/foo@1.0.0",
        )

        result = maven.get_maven_dependency_packages(self.project, main_purl)

        self.assertEqual(len(result), 2)
        self.assertIn(dep_commons, result)
        self.assertIn(dep_jackson, result)
        self.assertNotIn(main_package, result)

    def test_scanpipe_maven_get_maven_dependency_packages_unresolved_dependency(
        self,
    ):
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._make_maven_package(
            self.project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        dependency = DiscoveredDependency.objects.create(
            project=self.project,
            dependency_uid="pkg:maven/commons-logging/commons-logging@1.1.1",
        )

        result = maven.get_maven_dependency_packages(self.project, main_purl)

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], DiscoveredDependency)
        self.assertEqual(result[0], dependency)
        self.assertFalse(
            self.project.discoveredpackages.filter(
                type="maven", name="commons-logging", version="1.1.1"
            ).exists()
        )

    def test_scanpipe_maven_get_maven_dependency_packages_resolved_dependency_reused(
        self,
    ):
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._make_maven_package(
            self.project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        resolved = self._make_maven_package(
            self.project, "commons-logging", "commons-logging", "1.1.1"
        )
        DiscoveredDependency.objects.create(
            project=self.project,
            dependency_uid="pkg:maven/commons-logging/commons-logging@1.1.1",
            type="maven",
            namespace="commons-logging",
            name="commons-logging",
            version="1.1.1",
            resolved_to_package=resolved,
        )

        result = maven.get_maven_dependency_packages(self.project, main_purl)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], resolved)

    def test_scanpipe_maven_get_maven_dependency_packages_dedupes_by_name(self):
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._make_maven_package(
            self.project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        # A DiscoveredPackage for jackson-databind...
        package = self._make_maven_package(
            self.project, "com.fasterxml.jackson.core", "jackson-databind", "2.4.0"
        )
        # An unresolved DiscoveredDependency for the same name.
        DiscoveredDependency.objects.create(
            project=self.project,
            dependency_uid="pkg:maven/com.fasterxml.jackson.core/jackson-databind",
            type="maven",
            namespace="com.fasterxml.jackson.core",
            name="jackson-databind",
            version="",
        )

        result = maven.get_maven_dependency_packages(self.project, main_purl)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], package)
        self.assertIsInstance(result[0], DiscoveredPackage)

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

    def test_scanpipe_maven_score_group_segments(self):
        group_id = "org/apache/commons"
        package_segments = ["org", "apache", "htrace", "foo"]
        self.assertEqual(maven._score_group_segments(group_id, package_segments), 2)

    def test_scanpipe_maven_score_artifact_segments(self):
        artifact_id = "commons/logging"
        package_segments = ["org", "apache", "commons", "logging", "impl"]
        self.assertEqual(
            maven._score_artifact_segments(artifact_id, package_segments), 4
        )

    def test_scanpipe_maven_score_fuzzy_segment(self):
        # "annotations" vs "annotation" -> fuzzy match, +3
        self.assertEqual(
            maven._score_fuzzy_segment(
                "jackson/annotations", ["jackson", "annotation"]
            ),
            3,
        )
        # "logging" vs "impl" -> no match
        self.assertEqual(
            maven._score_fuzzy_segment("commons/logging", ["commons", "impl"]),
            0,
        )

    def test_scanpipe_maven_score_dependency_for_fqn_commons_logging(self):
        package = self._make_maven_package(
            self.project, "commons-logging", "commons-logging", "1.1.1"
        )
        score, signals = maven.score_dependency_for_fqn(
            "org.apache.commons.logging.impl.AvalonLogger", package
        )
        # group: "commons" + "logging" -> +2
        # artifact: "commons" + "logging" -> +4
        # fuzzy: "logging" vs "impl" -> no
        self.assertEqual(score, 6)
        self.assertEqual(signals, {"group", "artifact"})

    def test_scanpipe_maven_score_dependency_for_fqn_jackson(self):
        package = self._make_maven_package(
            self.project,
            "com.fasterxml.jackson.core",
            "jackson-annotations",
            "2.4.0",
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
        package = self._make_maven_package(
            self.project, "commons-logging", "commons-logging", "1.1.1"
        )
        self.assertEqual(maven.score_dependency_for_fqn("Foo", package), (0, set()))

    def test_scanpipe_maven_match_shaded_class_to_package_clear_winner(self):
        commons = self._make_maven_package(
            self.project, "commons-logging", "commons-logging", "1.1.1"
        )
        jackson = self._make_maven_package(
            self.project,
            "com.fasterxml.jackson.core",
            "jackson-annotations",
            "2.4.0",
        )
        result = maven.match_shaded_class_to_package(
            "org.apache.commons.logging.impl.AvalonLogger",
            [commons, jackson],
        )
        self.assertIsNotNone(result)
        matched_package, score, signals = result
        self.assertEqual(matched_package, commons)
        self.assertEqual(score, 6)
        self.assertEqual(signals, {"group", "artifact"})

    def test_scanpipe_maven_match_shaded_class_to_package_tie(self):
        # Two versions of the same dependency score identically.
        self._make_maven_package(
            self.project, "commons-logging", "commons-logging", "1.1.1"
        )
        self._make_maven_package(
            self.project, "commons-logging", "commons-logging", "1.2.0"
        )
        packages = list(self.project.discoveredpackages.filter(type="maven"))
        result = maven.match_shaded_class_to_package(
            "org.apache.commons.logging.impl.AvalonLogger",
            packages,
        )
        self.assertIsNone(result)

    def test_scanpipe_maven_get_original_fqn_with_relocations_shaded(self):
        relocations = {
            "org.apache.htrace.commons.logging": "org.apache.commons.logging",
        }
        original = maven._get_original_fqn(
            "org.apache.htrace.commons.logging.impl.AvalonLogger",
            relocations,
            main_prefix="org.apache.htrace.",
        )
        self.assertEqual(original, "org.apache.commons.logging.impl.AvalonLogger")

    def test_scanpipe_maven_get_original_fqn_with_relocations_not_shaded(self):
        relocations = {
            "org.apache.htrace.commons.logging": "org.apache.commons.logging",
        }
        original = maven._get_original_fqn(
            "org.apache.hadoop.mapreduce.Job",
            relocations,
            main_prefix="org.apache.hadoop.",
        )
        self.assertIsNone(original)

    def test_scanpipe_maven_get_original_fqn_no_relocations_main_namespace(self):
        original = maven._get_original_fqn(
            "org.apache.hadoop.mapreduce.Job",
            {},
            main_prefix="org.apache.hadoop.",
        )
        self.assertIsNone(original)

    def test_scanpipe_maven_get_original_fqn_no_relocations_other_namespace(self):
        original = maven._get_original_fqn(
            "org.apache.commons.logging.AvalonLogger",
            {},
            main_prefix="org.apache.hadoop.",
        )
        self.assertEqual(original, "org.apache.commons.logging.AvalonLogger")

    def test_scanpipe_maven_map_shaded_classes_attributions(self):
        project, main_purl, commons, jackson = self._setup_project_with_shaded_classes()

        commons_class = make_resource_file(
            project,
            "to/org/apache/htrace/commons/logging/impl/AvalonLogger.class",
            status=flag.REQUIRES_REVIEW,
        )
        jackson_class = make_resource_file(
            project,
            "to/org/apache/htrace/fasterxml/jackson/annotation/JsonTypeId.class",
            status=flag.REQUIRES_REVIEW,
        )
        unrelated_class = make_resource_file(
            project,
            "to/com/example/Unrelated.class",
            status=flag.REQUIRES_REVIEW,
        )

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        commons_class.refresh_from_db()
        self.assertEqual(commons_class.status, flag.SHADED_CLASS)
        self.assertIn(commons, commons_class.discovered_packages.all())
        self.assertEqual(
            {
                "shaded_from_package": (
                    "pkg:maven/commons-logging/commons-logging@1.1.1"
                ),
                "original_fqn": "org.apache.commons.logging.impl.AvalonLogger",
                "match_score": 6,
                "match_signals": ["artifact", "group"],
            },
            commons_class.extra_data,
        )

        jackson_class.refresh_from_db()
        self.assertEqual(jackson_class.status, flag.SHADED_CLASS)
        self.assertIn(jackson, jackson_class.discovered_packages.all())
        self.assertEqual(
            {
                "shaded_from_package": (
                    "pkg:maven/com.fasterxml.jackson.core/jackson-annotations@2.4.0"
                ),
                "original_fqn": "com.fasterxml.jackson.annotation.JsonTypeId",
                "match_score": 8,
                "match_signals": ["artifact", "fuzzy", "group"],
            },
            jackson_class.extra_data,
        )

        # The unrelated class should stay as requires-review.
        unrelated_class.refresh_from_db()
        self.assertEqual(unrelated_class.status, flag.REQUIRES_REVIEW)
        self.assertEqual(unrelated_class.discovered_packages.count(), 0)

    def test_scanpipe_maven_map_shaded_classes_with_unresolved_dependency(self):
        project = self.project
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._make_maven_package(
            project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        DiscoveredDependency.objects.create(
            project=project,
            dependency_uid="pkg:maven/commons-logging/commons-logging@1.1.1",
            type="maven",
            namespace="commons-logging",
            name="commons-logging",
            version="1.1.1",
        )
        self._add_pom_resource(
            project,
            "to/META-INF/maven/org.apache.htrace/htrace-core/pom.xml",
            "shaded-pom.xml",
        )

        commons_class = make_resource_file(
            project,
            "to/org/apache/htrace/commons/logging/impl/AvalonLogger.class",
            status=flag.REQUIRES_REVIEW,
        )

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        commons_class.refresh_from_db()
        self.assertEqual(commons_class.status, flag.SHADED_CLASS)
        self.assertEqual(
            {
                "shaded_from_package": (
                    "pkg:maven/commons-logging/commons-logging@1.1.1"
                ),
                "original_fqn": "org.apache.commons.logging.impl.AvalonLogger",
                "match_score": 6,
                "match_signals": ["artifact", "group"],
            },
            commons_class.extra_data,
        )

        self.assertEqual(commons_class.discovered_packages.count(), 0)
        self.assertFalse(
            project.discoveredpackages.filter(
                type="maven", name="commons-logging", version="1.1.1"
            ).exists()
        )

    def test_scanpipe_maven_map_shaded_classes_with_resolved_dependency(self):
        project = self.project
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._make_maven_package(
            project, "org.apache.htrace", "htrace-core", "4.0.0-incubating"
        )
        resolved = self._make_maven_package(
            project, "commons-logging", "commons-logging", "1.1.1"
        )
        DiscoveredDependency.objects.create(
            project=project,
            dependency_uid="pkg:maven/commons-logging/commons-logging@1.1.1",
            type="maven",
            namespace="commons-logging",
            name="commons-logging",
            version="1.1.1",
            resolved_to_package=resolved,
        )
        self._add_pom_resource(
            project,
            "to/META-INF/maven/org.apache.htrace/htrace-core/pom.xml",
            "shaded-pom.xml",
        )

        commons_class = make_resource_file(
            project,
            "to/org/apache/htrace/commons/logging/impl/AvalonLogger.class",
            status=flag.REQUIRES_REVIEW,
        )

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        commons_class.refresh_from_db()
        self.assertEqual(commons_class.status, flag.SHADED_CLASS)
        self.assertEqual(
            {
                "shaded_from_package": (
                    "pkg:maven/commons-logging/commons-logging@1.1.1"
                ),
                "original_fqn": "org.apache.commons.logging.impl.AvalonLogger",
                "match_score": 6,
                "match_signals": ["artifact", "group"],
            },
            commons_class.extra_data,
        )

        self.assertEqual(commons_class.discovered_packages.count(), 1)
        self.assertTrue(
            project.discoveredpackages.filter(
                type="maven", name="commons-logging", version="1.1.1"
            ).exists()
        )

    def test_scanpipe_maven_map_shaded_classes_no_classes(self):
        project, main_purl, _, _ = self._setup_project_with_shaded_classes()

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        self.assertEqual(
            project.codebaseresources.filter(status=flag.SHADED_CLASS).count(),
            0,
        )

    def test_scanpipe_maven_map_shaded_classes_dedupes_versions(self):
        project = self.project
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        self._make_maven_package(project, "commons-logging", "commons-logging", "1.1.1")
        self._make_maven_package(project, "commons-logging", "commons-logging", "1.2.0")
        self._add_pom_resource(
            project,
            "to/META-INF/maven/org.apache.htrace/htrace-core/pom.xml",
            "shaded-pom.xml",
        )

        commons_class = make_resource_file(
            project,
            "to/org/apache/htrace/commons/logging/impl/AvalonLogger.class",
            status=flag.REQUIRES_REVIEW,
        )

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        commons_class.refresh_from_db()
        self.assertEqual(commons_class.status, flag.SHADED_CLASS)
        # Only one of the two versions is attributed.
        self.assertEqual(commons_class.discovered_packages.count(), 1)

    def test_scanpipe_maven_map_shaded_classes_no_dependency_packages(self):
        project = Project.objects.create(name="No-dependencies-analysis")
        main_purl = PackageURL.from_string(
            "pkg:maven/org.apache.htrace/htrace-core@4.0.0-incubating"
        )
        make_resource_file(
            project,
            "to/com/example/Foo.class",
            status=flag.REQUIRES_REVIEW,
        )

        maven.map_shaded_classes_to_maven_packages(project, purl=main_purl)

        self.assertEqual(
            project.codebaseresources.filter(status=flag.SHADED_CLASS).count(),
            0,
        )

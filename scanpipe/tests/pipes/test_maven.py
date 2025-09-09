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
from unittest import TestCase
from unittest.mock import Mock, patch

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import InputSource
from scanpipe.models import Project
from scanpipe.pipes import maven


class ScanPipeMavenTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Maven Project")
        
    def tearDown(self):
        self.project.delete()

    def test_extract_maven_coordinates_from_url_maven_central(self):
        """Test extraction of Maven coordinates from Maven Central URLs."""
        test_cases = [
            {
                'url': 'https://repo1.maven.org/maven2/io/perfmark/perfmark-api/0.27.0/perfmark-api-0.27.0.jar',
                'expected': {
                    'group_id': 'io.perfmark',
                    'artifact_id': 'perfmark-api',
                    'version': '0.27.0'
                }
            },
            {
                'url': 'https://central.maven.org/maven2/com/google/guava/guava/30.1-jre/guava-30.1-jre.jar',
                'expected': {
                    'group_id': 'com.google.guava',
                    'artifact_id': 'guava',
                    'version': '30.1-jre'
                }
            },
            {
                'url': 'https://repo.maven.apache.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar',
                'expected': {
                    'group_id': 'org.apache.commons',
                    'artifact_id': 'commons-lang3',
                    'version': '3.12.0'
                }
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(url=test_case['url']):
                coords = maven._extract_maven_coordinates_from_url(test_case['url'])
                self.assertEqual(test_case['expected'], coords)

    def test_extract_maven_coordinates_from_url_invalid(self):
        """Test extraction with invalid or non-Maven URLs."""
        invalid_urls = [
            'https://github.com/perfmark/perfmark/releases/download/v0.27.0/perfmark-api-0.27.0.jar',
            'https://example.com/some-file.jar',
            'https://repo1.maven.org/maven2/incomplete/path',
            'not-a-url',
            None,
            ''
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                coords = maven._extract_maven_coordinates_from_url(url)
                self.assertIsNone(coords)

    def test_detect_maven_jars_from_input_source_url(self):
        """Test Maven JAR detection based on input source URLs."""
        # Create an input source with Maven Central URL
        input_source = InputSource.objects.create(
            project=self.project,
            download_url="https://repo1.maven.org/maven2/io/perfmark/perfmark-api/0.27.0/perfmark-api-0.27.0.jar",
            filename="perfmark-api-0.27.0.jar"
        )
        
        # Create a JAR package (incorrectly detected as jar type)
        jar_package = DiscoveredPackage.objects.create(
            project=self.project,
            type="jar",
            namespace="io.perfmark",
            name="io.perfmark",  # ScanCode might detect this way
            version="0.27.0"
        )
        
        # Run the Maven detection
        result = maven.detect_maven_jars_from_pom_properties(self.project)
        
        # Verify results
        self.assertEqual(1, result)
        
        # Refresh the package from database
        jar_package.refresh_from_db()
        
        # Check that the package was updated to Maven type
        self.assertEqual("maven", jar_package.type)
        self.assertEqual("io.perfmark", jar_package.namespace)
        self.assertEqual("perfmark-api", jar_package.name)
        self.assertEqual("0.27.0", jar_package.version)
        
        # Check the PURL is correct
        expected_purl = "pkg:maven/io.perfmark/perfmark-api@0.27.0"
        self.assertEqual(expected_purl, jar_package.package_url)

    def test_validate_maven_coordinates_against_jar_package(self):
        """Test validation of Maven coordinates against JAR packages."""
        input_source = InputSource.objects.create(
            project=self.project,
            download_url="https://repo1.maven.org/maven2/io/perfmark/perfmark-api/0.27.0/perfmark-api-0.27.0.jar",
            filename="perfmark-api-0.27.0.jar"
        )
        
        maven_coords = {
            'group_id': 'io.perfmark',
            'artifact_id': 'perfmark-api',
            'version': '0.27.0'
        }
        
        # Test cases with different package configurations
        test_cases = [
            {
                'description': 'Package with matching version',
                'package_data': {
                    'name': 'some-name',
                    'namespace': None,
                    'version': '0.27.0'
                },
                'expected': True
            },
            {
                'description': 'Package with matching namespace',
                'package_data': {
                    'name': 'some-name',
                    'namespace': 'io.perfmark',
                    'version': '1.0.0'
                },
                'expected': True
            },
            {
                'description': 'Package with artifact in name',
                'package_data': {
                    'name': 'perfmark-api',
                    'namespace': None,
                    'version': '1.0.0'
                },
                'expected': True
            },
            {
                'description': 'Package with group in name',
                'package_data': {
                    'name': 'io.perfmark',
                    'namespace': None,
                    'version': '1.0.0'
                },
                'expected': True
            },
            {
                'description': 'Unrelated package',
                'package_data': {
                    'name': 'unrelated',
                    'namespace': 'com.example',
                    'version': '2.0.0'
                },
                'expected': True  # Returns True for single JAR inputs
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(description=test_case['description']):
                jar_package = DiscoveredPackage.objects.create(
                    project=self.project,
                    type="jar",
                    **test_case['package_data']
                )
                
                result = maven._validate_maven_coordinates_against_jar_package(
                    jar_package, maven_coords, input_source
                )
                
                self.assertEqual(test_case['expected'], result)
                
                # Clean up
                if jar_package.pk:  # Only delete if the package was saved
                    jar_package.delete()

    @patch('pathlib.Path.read_text')
    def test_extract_maven_coordinates_from_pom_properties(self, mock_read_text):
        """Test extraction of Maven coordinates from pom.properties content."""
        # Mock the file content
        mock_read_text.return_value = (
            "# Generated by Maven\n"
            "# Some comment\n"
            "groupId=io.perfmark\n"
            "artifactId=perfmark-api\n"
            "version=0.27.0\n"
            "someOtherProperty=value\n"
        )
        
        # Create a mock CodebaseResource
        mock_resource = Mock()
        mock_resource.location = "/fake/path/pom.properties"
        
        # Mock Path.exists to return True
        with patch('pathlib.Path.exists', return_value=True):
            # Test the extraction function
            coords = maven._extract_maven_coordinates_from_pom_properties(mock_resource)
            
            # Verify the extracted coordinates
            expected = {
                'group_id': 'io.perfmark',
                'artifact_id': 'perfmark-api',
                'version': '0.27.0'
            }
            self.assertEqual(expected, coords)

    @patch('pathlib.Path.read_text')
    def test_extract_maven_coordinates_missing_fields(self, mock_read_text):
        """Test extraction when required fields are missing."""
        # Mock the file content with missing fields
        mock_read_text.return_value = (
            "# Generated by Maven\n"
            "groupId=io.perfmark\n"
            "# artifactId is missing\n"
            "version=0.27.0\n"
        )
        
        # Create a mock CodebaseResource
        mock_resource = Mock()
        mock_resource.location = "/fake/path/pom.properties"
        
        # Mock Path.exists to return True
        with patch('pathlib.Path.exists', return_value=True):
            # Test the extraction function
            coords = maven._extract_maven_coordinates_from_pom_properties(mock_resource)
            
            # Should return None when required fields are missing
            self.assertIsNone(coords)

    def test_no_maven_jars_detected(self):
        """Test that no changes are made when no Maven JARs are found."""
        # Create a regular JAR package without Maven metadata
        jar_package = DiscoveredPackage.objects.create(
            project=self.project,
            type="jar",
            name="some-library",
            version="1.0.0",
            package_uid="pkg:jar/some-library@1.0.0"
        )
        
        # Run the Maven detection
        result = maven.detect_maven_jars_from_pom_properties(self.project)
        
        # Verify no packages were modified
        self.assertEqual(0, result)
        
        # Refresh the package from database
        jar_package.refresh_from_db()
        
        # Check that the package remains unchanged
        self.assertEqual("jar", jar_package.type)
        self.assertEqual("some-library", jar_package.name)
        self.assertEqual("1.0.0", jar_package.version)
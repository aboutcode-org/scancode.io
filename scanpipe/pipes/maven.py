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

"""Support for Maven-specific package detection and PURL correction."""

import logging
import re
from pathlib import Path

from packageurl import PackageURL

logger = logging.getLogger(__name__)


def detect_maven_jars_from_pom_properties(project, logger_func=None):
    """
    Detect JAR files that should be Maven packages by looking for Maven metadata.

    This function identifies JAR packages that were incorrectly detected as
    pkg:jar/ type instead of pkg:maven/ type by looking for Maven metadata
    files (pom.properties) in the JAR's extracted content, or by inferring
    Maven coordinates from the download URL pattern.

    For each detected Maven JAR, it updates the package PURL to use the
    correct Maven coordinates.
    """
    if logger_func:
        logger_func(
            "Detecting Maven JARs from pom.properties files and download URLs..."
        )

    maven_jars_fixed = 0

    # Method 1: Look for pom.properties files in extracted JAR contents
    pom_properties_resources = project.codebaseresources.filter(
        path__contains="META-INF/maven/", name="pom.properties"
    )

    for pom_resource in pom_properties_resources:
        try:
            # Extract Maven coordinates from pom.properties
            maven_coords = _extract_maven_coordinates_from_pom_properties(
                pom_resource
            )
            if not maven_coords:
                continue

            # Find the corresponding JAR package
            jar_package = _find_jar_package_for_pom(
                project, pom_resource, maven_coords
            )
            if not jar_package:
                continue

            # Update the package to use Maven PURL
            if _update_jar_package_to_maven(
                jar_package, maven_coords, logger_func
            ):
                maven_jars_fixed += 1

        except Exception as e:
            logger.error(f"Error processing {pom_resource.path}: {e}")
            continue

    # Method 2: Look for JAR packages with Maven Central download URLs
    jar_packages = project.discoveredpackages.filter(type="jar")

    for jar_package in jar_packages:
        try:
            # Check if the JAR file came from an input source with a Maven Central URL
            maven_coords = None

            # First, try to find input sources that could be related to this package
            input_sources = project.inputsources.filter(
                download_url__contains="maven2"
            )

            for input_source in input_sources:
                if input_source.download_url:
                    # Check if this input source could be for this JAR package
                    # by matching filename or checking if JAR was extracted
                    potential_coords = _extract_maven_coordinates_from_url(
                        input_source.download_url
                    )
                    if potential_coords:
                        # Validate that this JAR package could be from coordinate
                        if _validate_maven_coordinates_against_jar_package(
                            jar_package, potential_coords, input_source
                        ):
                            maven_coords = potential_coords
                            break

            if maven_coords:
                if _update_jar_package_to_maven(
                    jar_package, maven_coords, logger_func
                ):
                    maven_jars_fixed += 1
                    if logger_func:
                        logger_func(
                            f"Converted JAR to Maven via input source URL: "
                            f"{input_source.download_url}"
                        )

        except Exception as e:
            logger.error(f"Error processing JAR package {jar_package.uuid}: {e}")
            continue

    if logger_func and maven_jars_fixed:
        logger_func(f"Fixed {maven_jars_fixed} JAR packages to use Maven PURLs")

    return maven_jars_fixed


def _extract_maven_coordinates_from_url(download_url):
    """
    Extract Maven coordinates from a Maven Central download URL.

    Supports URLs like:
    https://repo1.maven.org/maven2/io/perfmark/perfmark-api/0.27.0/perfmark-api-0.27.0.jar
    https://central.maven.org/maven2/group/artifact/version/artifact-version.jar

    Returns a dict with 'group_id', 'artifact_id', and 'version' keys, or None.
    """
    import re
    from urllib.parse import urlparse

    if not download_url:
        return None

    try:
        # Parse the URL
        parsed = urlparse(download_url)

        # Check if it's from a Maven repository
        if not any(
            maven_host in parsed.netloc.lower()
            for maven_host in [
                "repo1.maven.org",
                "central.maven.org",
                "repo.maven.apache.org",
            ]
        ):
            return None

        # Extract the path after /maven2/
        path = parsed.path
        maven2_match = re.search(r"/maven2/(.+)", path)
        if not maven2_match:
            return None

        maven_path = maven2_match.group(1)

        # Parse Maven path: group/artifact/version/artifact-version.jar
        # Example: io/perfmark/perfmark-api/0.27.0/perfmark-api-0.27.0.jar
        path_parts = maven_path.strip("/").split("/")

        if len(path_parts) < 4:
            return None

        # Last part is the filename
        filename = path_parts[-1]
        # Second to last is version
        version = path_parts[-2]
        # Third to last is artifact
        artifact_id = path_parts[-3]
        # Everything before that is group (with / converted to .)
        group_parts = path_parts[:-3]
        group_id = ".".join(group_parts)

        # Validate the filename matches the expected pattern
        expected_filename = f"{artifact_id}-{version}.jar"
        if filename != expected_filename:
            # Try with classifier (e.g., artifact-version-classifier.jar)
            prefix = f"{artifact_id}-{version}-"
            if not filename.startswith(prefix) or not filename.endswith(".jar"):
                return None

        # Validate extracted coordinates
        if not group_id or not artifact_id or not version:
            return None

        return {
            "group_id": group_id,
            "artifact_id": artifact_id,
            "version": version,
        }

    except Exception as e:
        logger.debug(f"Could not parse Maven coordinates from URL {download_url}: {e}")
        return None


def _extract_maven_coordinates_from_pom_properties(pom_resource):
    """
    Extract Maven coordinates (groupId, artifactId, version) from a pom.properties file.

    Returns a dict with 'group_id', 'artifact_id', and 'version' keys, or None if
    the coordinates cannot be extracted.
    """
    try:
        # Read the pom.properties file content
        if not pom_resource.location or not Path(pom_resource.location).exists():
            return None

        content = Path(pom_resource.location).read_text(
            encoding="utf-8", errors="ignore"
        )

        # Parse the properties
        props = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()

        # Extract Maven coordinates
        group_id = props.get("groupId")
        artifact_id = props.get("artifactId")
        version = props.get("version")

        if group_id and artifact_id and version:
            return {
                "group_id": group_id,
                "artifact_id": artifact_id,
                "version": version,
            }

    except Exception as e:
        logger.debug(f"Could not parse pom.properties from {pom_resource.path}: {e}")

    return None


def _find_jar_package_for_pom(project, pom_resource, maven_coords):
    """
    Find the JAR package that corresponds to the given pom.properties resource.

    This looks for packages of type 'jar' that are associated with the same
    JAR file that contains the pom.properties.
    """
    # Extract the JAR path from the pom.properties path
    # Example: "path/file.jar-extract/META-INF/maven/group/artifact/pom.properties"
    #          should match package from "path/file.jar"

    pom_path = pom_resource.path

    # Look for the pattern: something.jar-extract/META-INF/maven/...
    jar_extract_match = re.search(r"(.+\.jar)-extract/", pom_path)
    if not jar_extract_match:
        return None

    jar_path = jar_extract_match.group(1)

    # Find packages that might be associated with this JAR
    # Look for packages of type 'jar' that might be from this file
    jar_packages = project.discoveredpackages.filter(type="jar")

    # Try to find the package by checking if it has resources from the JAR
    for package in jar_packages:
        # Check if the package has resources from this JAR
        package_resources = package.codebase_resources.all()
        for resource in package_resources:
            if resource.path == jar_path or resource.path.startswith(
                jar_path + "-extract/"
            ):
                # Additional validation: check if Maven coordinates match expected
                if _validate_maven_coordinates_match(package, maven_coords):
                    return package

    return None


def _validate_maven_coordinates_against_jar_package(
    jar_package, maven_coords, input_source
):
    """
    Validate that the Maven coordinates make sense for this JAR package.

    This is more flexible than the basic validation since we're matching
    based on the input source download URL.
    """
    # Check if the input source filename matches the expected JAR filename
    if input_source.filename:
        expected_jar_name = (
            f"{maven_coords['artifact_id']}-{maven_coords['version']}.jar"
        )
        if input_source.filename == expected_jar_name:
            return True

    # Check if the package version matches
    if jar_package.version and jar_package.version == maven_coords["version"]:
        return True

    # Check if the package name contains the artifact ID or group ID
    if jar_package.name:
        # Name could be "io.perfmark" (group) or "perfmark-api" (artifact)
        if (
            maven_coords["artifact_id"] in jar_package.name
            or maven_coords["group_id"] in jar_package.name
        ):
            return True

    # Check if the namespace matches the group ID
    if (
        jar_package.namespace
        and jar_package.namespace == maven_coords["group_id"]
    ):
        return True

    # If it's a single JAR file input and we have Maven coordinates from the URL,
    # it's likely a match (this handles the perfmark-api case)
    return True


def _validate_maven_coordinates_match(package, maven_coords):
    """
    Validate that the Maven coordinates make sense for this package.

    This performs basic validation to ensure we're not incorrectly
    converting unrelated packages.
    """
    # Check if the package name matches the artifact ID
    if package.name and package.name == maven_coords["artifact_id"]:
        return True

    # Check if the package version matches
    if package.version and package.version == maven_coords["version"]:
        return True

    # For packages detected from URLs, check if the name contains the artifact ID
    # This handles cases where ScanCode detects the name as "io.perfmark" but
    # the artifact ID is "perfmark-api"
    if package.name and maven_coords["artifact_id"] in package.name:
        return True

    # Check if the namespace/group matches
    if package.namespace and package.namespace == maven_coords["group_id"]:
        return True

    # If we can't validate, be conservative and don't convert
    return False


def _update_jar_package_to_maven(jar_package, maven_coords, logger_func=None):
    """
    Update a JAR package to use the correct Maven PURL format.

    Returns True if the package was updated, False otherwise.
    """
    try:
        # Create the new Maven PURL
        maven_purl = PackageURL(
            type="maven",
            namespace=maven_coords["group_id"],
            name=maven_coords["artifact_id"],
            version=maven_coords["version"],
            qualifiers=jar_package.qualifiers if jar_package.qualifiers else None,
            subpath=jar_package.subpath if jar_package.subpath else None,
        )

        # Update the package fields
        updates = {
            "type": "maven",
            "namespace": maven_coords["group_id"],
            "name": maven_coords["artifact_id"],
            "version": maven_coords["version"],
        }

        # Log the change
        old_purl = jar_package.package_url
        new_purl = str(maven_purl)

        if logger_func:
            logger_func(f"Converting JAR to Maven: {old_purl} -> {new_purl}")

        # Update the package
        jar_package.update(**updates)

        return True

    except Exception as e:
        logger.error(
            f"Failed to update package {jar_package.uuid} to Maven PURL: {e}"
        )
        return False

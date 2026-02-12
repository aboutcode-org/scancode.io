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

from packagedcode import get_package_handler
from packageurl import PackageURL

logger = logging.getLogger(__name__)


def detect_maven_jars_from_pom_properties(project, logger_func=None):
    """
    Detect JAR files that should be Maven packages by looking for Maven metadata.

    This function identifies JAR packages that were incorrectly detected as
    pkg:jar/ type instead of pkg:maven/ type by looking for Maven metadata
    files (pom.properties) in the JAR's extracted content.

    For each detected Maven JAR, it updates the package PURL to use the
    correct Maven coordinates.
    """
    if logger_func:
        logger_func("Detecting Maven JARs from pom.properties files...")

    maven_jars_fixed = 0

    # Look for pom.properties files in extracted JAR contents
    pom_properties_resources = project.codebaseresources.filter(
        path__contains="META-INF/maven/", name="pom.properties"
    )

    for pom_resource in pom_properties_resources:
        maven_coords = get_maven_coordinates_from_pom_properties(pom_resource)
        if not maven_coords:
            continue

        jar_package = get_jar_package_for_pom_resource(project, pom_resource, maven_coords)
        if not jar_package:
            continue

        if convert_jar_package_to_maven(jar_package, maven_coords, logger_func):
            maven_jars_fixed += 1

    if logger_func and maven_jars_fixed:
        logger_func(f"Fixed {maven_jars_fixed} JAR packages to use Maven PURLs")

    return maven_jars_fixed


def get_maven_coordinates_from_pom_properties(pom_resource):
    """
    Extract Maven coordinates from a pom.properties file.
    
    Uses the ScanCode Toolkit package handler to do the heavy lifting.
    """
    if not pom_resource.location:
        return None

    handler = get_package_handler(pom_resource.location)
    if not handler:
        return None
        
    packages = list(handler.parse(pom_resource.location))
    if not packages:
        return None
        
    package = packages[0]
    if not all([package.namespace, package.name, package.version]):
        return None
        
    return {
        "group_id": package.namespace,
        "artifact_id": package.name,
        "version": package.version,
    }


def get_jar_package_for_pom_resource(project, pom_resource, maven_coords):
    """
    Find the JAR package that matches this pom.properties file.
    
    We look for packages by matching the JAR path pattern.
    """
    # Extract JAR path from pom.properties location
    # e.g., "some-lib.jar-extract/META-INF/maven/org/example/pom.properties" -> "some-lib.jar"
    pom_path = pom_resource.path
    jar_match = re.search(r"(.+\.jar)-extract/", pom_path)
    if not jar_match:
        return None

    jar_path = jar_match.group(1)
    jar_packages = project.discoveredpackages.filter(type="jar")

    # First, try to match by checking package resources
    for package in jar_packages:
        for resource in package.codebase_resources.all():
            if resource.path == jar_path or resource.path.startswith(jar_path + "-extract/"):
                if is_maven_coordinates_match(package, maven_coords):
                    return package

    # Fallback: match by coordinates alone
    for package in jar_packages:
        if is_maven_coordinates_match(package, maven_coords):
            return package

    return None


def is_maven_coordinates_match(package, maven_coords):
    """
    Check if a package matches the Maven coordinates we found.
    
    We're pretty lenient here - any reasonable match counts.
    """
    artifact_id = maven_coords["artifact_id"]
    group_id = maven_coords["group_id"]
    version = maven_coords["version"]
    
    # Direct name match is best
    if package.name == artifact_id:
        return True

    # Version match is also a good sign
    if package.version == version:
        return True

    # Name contains artifact ID
    if package.name and artifact_id in package.name:
        return True

    # Namespace matches group ID
    if package.namespace == group_id:
        return True

    return False


def convert_jar_package_to_maven(jar_package, maven_coords, logger_func=None):
    """
    Convert a JAR package to proper Maven format.
    
    Updates the package type and coordinates based on what we found
    in the pom.properties file.
    """
    try:
        # Build the new Maven PURL
        maven_purl = PackageURL(
            type="maven",
            namespace=maven_coords["group_id"],
            name=maven_coords["artifact_id"],
            version=maven_coords["version"],
            qualifiers=jar_package.qualifiers,
            subpath=jar_package.subpath,
        )

        # Update package info
        jar_package.update(
            type="maven",
            namespace=maven_coords["group_id"],
            name=maven_coords["artifact_id"],
            version=maven_coords["version"],
        )

        if logger_func:
            logger_func(f"Converting JAR to Maven: {jar_package.package_url} -> {maven_purl}")

        return True

    except Exception as error:
        logger.error(f"Failed to convert package {jar_package.uuid}: {error}")
        return False
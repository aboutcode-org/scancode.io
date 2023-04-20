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
import sys
from pathlib import Path

from django.core.validators import EMPTY_VALUES

from attributecode.model import About
from licensedcode.match_spdx_lid import get_spdx_expression
from packagedcode import APPLICATION_PACKAGE_DATAFILE_HANDLERS
from packagedcode.licensing import get_normalized_expression
from packageurl import PackageURL
from python_inspector.resolve_cli import resolver_api
from scancode.api import get_package_data

from scanpipe.models import DiscoveredPackage
from scanpipe.pipes import cyclonedx
from scanpipe.pipes import spdx

"""
Resolve packages from manifest, lockfile, and SBOM.
"""


def resolve_packages(input_location):
    """Resolve the packages from manifest file."""
    default_package_type = get_default_package_type(input_location)
    if not default_package_type:
        raise Exception(f"No package type found for {input_location}")

    # The ScanCode.io resolvers take precedence over the ScanCode-toolkit ones.
    resolver = resolver_registry.get(default_package_type)
    if resolver:
        resolved_packages = resolver(input_location=input_location)
    else:
        package_data = get_package_data(location=input_location)
        resolved_packages = package_data.get("package_data", [])

    return resolved_packages


def resolve_pypi_packages(input_location):
    """Resolve the PyPI packages from the `input_location` requirements file."""
    python_version = f"{sys.version_info.major}{sys.version_info.minor}"
    operating_system = "linux"

    inspector_output = resolver_api(
        requirement_files=[input_location],
        python_version=python_version,
        operating_system=operating_system,
        prefer_source=True,
    )

    return inspector_output.packages


def resolve_about_packages(input_location):
    """Resolve the packages from the `input_location` .ABOUT file."""
    about = About(location=input_location)
    about_data = about.as_dict()
    package_data = about_data.copy()

    if package_url := about_data.get("package_url"):
        package_url_data = PackageURL.from_string(package_url).to_dict(encode=True)
        for field_name, value in package_url_data.items():
            if value:
                package_data[field_name] = value

    if about_resource := about_data.get("about_resource"):
        package_data["filename"] = list(about_resource.keys())[0]

    for field_name, value in about_data.items():
        if field_name.startswith("checksum_"):
            package_data[field_name.replace("checksum_", "")] = value

    package_data = DiscoveredPackage.clean_data(package_data)
    return [package_data]


def spdx_package_to_discovered_package_data(spdx_package):
    package_url_dict = {}
    for ref in spdx_package.external_refs:
        if ref.type == "purl":
            purl = ref.locator
            package_url_dict = PackageURL.from_string(purl).to_dict(encode=True)

    checksum_data = {
        checksum.algorithm.lower(): checksum.value
        for checksum in spdx_package.checksums
    }

    package_data = {
        "name": spdx_package.name,
        "download_url": spdx_package.download_location,
        "declared_license": spdx_package.license_declared,
        "license_expression": get_spdx_expression(spdx_package.license_concluded or ""),
        "copyright": spdx_package.copyright_text,
        "version": spdx_package.version,
        "homepage_url": spdx_package.homepage,
        "filename": spdx_package.filename,
        "description": spdx_package.description,
        "release_date": spdx_package.release_date,
        **package_url_dict,
        **checksum_data,
    }

    return {
        key: value
        for key, value in package_data.items()
        if value not in [None, "", "NOASSERTION"]
    }


def resolve_spdx_packages(input_location):
    """Resolve the packages from the `input_location` SPDX document file."""
    input_path = Path(input_location)
    spdx_document = json.loads(input_path.read_text())

    try:
        spdx.validate_document(spdx_document)
    except Exception as e:
        raise Exception(f'SPDX document "{input_path.name}" is not valid: {e}')

    return [
        spdx_package_to_discovered_package_data(spdx.Package.from_data(spdx_package))
        for spdx_package in spdx_document.get("packages", [])
    ]


def cyclonedx_component_to_package_data(component_data):
    """Return package_data from CycloneDX component."""
    extra_data = {}
    component = component_data["cdx_package"]

    package_url_dict = {}
    if component.purl:
        package_url_dict = PackageURL.from_string(component.purl).to_dict(encode=True)

    declared_license = cyclonedx.get_declared_licenses(licenses=component.licenses)

    if external_references := cyclonedx.get_external_references(component):
        extra_data["externalReferences"] = external_references

    if nested_components := component_data.get("nested_components"):
        extra_data["nestedComponents"] = nested_components

    package_data = {
        "name": component.name,
        "declared_license": declared_license,
        "copyright": component.copyright,
        "version": component.version,
        "description": component.description,
        "extra_data": extra_data,
        **package_url_dict,
        **cyclonedx.get_checksums(component),
        **cyclonedx.get_properties_data(component),
    }

    return {
        key: value for key, value in package_data.items() if value not in EMPTY_VALUES
    }


def resolve_cyclonedx_packages(input_location):
    """Resolve the packages from the `input_location` CycloneDX document file."""
    input_path = Path(input_location)
    cyclonedx_document = json.loads(input_path.read_text())

    try:
        cyclonedx.validate_document(cyclonedx_document)
    except Exception as e:
        raise Exception(f'CycloneDX document "{input_path.name}" is not valid: {e}')

    cyclonedx_bom = cyclonedx.get_bom(cyclonedx_document)
    components = cyclonedx.get_components(cyclonedx_bom)

    return [cyclonedx_component_to_package_data(component) for component in components]


def get_default_package_type(input_location):
    """
    Return the package type associated with the provided `input_location`.
    This type is used to get the related handler that knows how process the input.
    """
    input_location = str(input_location)

    for handler in APPLICATION_PACKAGE_DATAFILE_HANDLERS:
        if handler.is_datafile(input_location):
            return handler.default_package_type

        if input_location.endswith((".spdx", ".spdx.json")):
            return "spdx"

        if input_location.endswith((".bom.json", ".cdx.json")):
            return "cyclonedx"

        if input_location.endswith(".json"):
            if cyclonedx.is_cyclonedx_bom(input_location):
                return "cyclonedx"
            if spdx.is_spdx_document(input_location):
                return "spdx"


# Mapping between the `default_package_type` its related resolver function
resolver_registry = {
    "about": resolve_about_packages,
    "pypi": resolve_pypi_packages,
    "spdx": resolve_spdx_packages,
    "cyclonedx": resolve_cyclonedx_packages,
}


def set_license_expression(package_data):
    """
    Set the license expression from a detected license dict/str in provided
    `package_data`.
    """
    declared_license = package_data.get("declared_license")
    license_expression = package_data.get("license_expression")

    if declared_license and not license_expression:
        license_str = ""

        if isinstance(declared_license, dict):
            license_str = declared_license.get("license")

        if not license_str:
            license_str = repr(declared_license)

        license_expression = get_normalized_expression(query_string=license_str)
        if license_expression:
            package_data["license_expression"] = license_expression

    return package_data

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
from collections import defaultdict
from contextlib import suppress
from pathlib import Path

from django.core.validators import EMPTY_VALUES

from cyclonedx.model import license as cdx_license_model
from cyclonedx.schema import SchemaVersion
from cyclonedx.schema.schema import SCHEMA_VERSIONS
from cyclonedx.validation import ValidationError
from cyclonedx.validation.json import JsonStrictValidator
from packageurl import PackageURL


def get_bom(cyclonedx_document):
    """Return CycloneDX BOM object."""
    from cyclonedx.model.bom import Bom

    return Bom.from_json(data=cyclonedx_document)


def get_components(bom, view):
    """Return list of components from CycloneDX BOM."""
    # TODO: Check if we could use `return list(bom._get_all_components())`
    return recursive_component_collector(bom.components, [], view)


def bom_attributes_to_dict(cyclonedx_attributes, view):
    """Return list of dict from a list of CycloneDX attributes."""
    if not cyclonedx_attributes:
        return []

    return [
        json.loads(attribute.as_json(view_=view)) for attribute in cyclonedx_attributes
    ]


def recursive_component_collector(root_component_list, collected, view):
    """Return list of components including the nested components."""
    if not root_component_list:
        return []

    for component in root_component_list:
        nested_components = {}
        if component.components is not None:
            nested_components = bom_attributes_to_dict(component.components, view)

        collected.append(
            {"cdx_package": component, "nested_components": nested_components}
        )
        recursive_component_collector(component.components, collected, view)
    return collected


def resolve_license(license):
    """Return license expression/id/name from license item."""
    if isinstance(license, cdx_license_model.LicenseExpression):
        return license.value
    elif isinstance(license, cdx_license_model.License):
        return license.id or license.name


def get_declared_licenses(licenses):
    """Return resolved license from list of LicenseChoice."""
    if not licenses:
        return ""

    resolved_licenses = [resolve_license(license) for license in licenses]
    return "\n".join(resolved_licenses)


def get_checksums(component):
    """Return dict of all the checksums from a component."""
    if not component.hashes:
        return {}

    algorithm_map_cdx_scio = {
        "MD5": "md5",
        "SHA-1": "sha1",
        "SHA-256": "sha256",
        "SHA-512": "sha512",
    }

    return {
        algorithm_map_cdx_scio[algo_hash.alg]: algo_hash.content
        for algo_hash in component.hashes
        if algo_hash.alg in algorithm_map_cdx_scio
    }


def get_external_references(component):
    """Return dict of reference urls from list of `component.external_references`."""
    external_references = component.external_references
    if not external_references:
        return {}

    references = defaultdict(list)
    for reference in external_references:
        references[reference.type.value].append(reference.url.uri)

    return dict(references)


def get_properties_data(component):
    """Return the properties as dict, extracted from  `component.properties`."""
    prefix = "aboutcode:"
    properties_data = {}
    properties = component.properties or []

    for component_property in properties:
        property_name = component_property.name
        property_value = component_property.value
        if property_name.startswith(prefix) and property_value not in EMPTY_VALUES:
            field_name = property_name.replace(prefix, "", 1)
            properties_data[field_name] = property_value

    return properties_data


def validate_document(document):
    """
    Check the validity of this CycloneDX document.

    The validator is loaded from the document specVersion property.
    """
    if isinstance(document, str):
        document = json.loads(document)

    spec_version = document.get("specVersion")
    if not spec_version:
        return ValidationError("'specVersion' is a required property")

    schema_version = SchemaVersion.from_version(spec_version)

    json_validator = JsonStrictValidator(schema_version)
    return json_validator._validata_data(document)


def is_cyclonedx_bom(input_location):
    """Return True if the file at `input_location` is a CycloneDX BOM."""
    with suppress(Exception):
        data = json.loads(Path(input_location).read_text())
        if data.get("bomFormat") == "CycloneDX":
            return True
    return False


# TODO: Add unit test
def cyclonedx_component_to_package_data(component_data):
    """Return package_data from CycloneDX component."""
    extra_data = {}
    component = component_data["cdx_package"]

    package_url_dict = {}
    if component.purl:
        package_url_dict = PackageURL.from_string(str(component.purl)).to_dict(
            encode=True
        )

    declared_license = get_declared_licenses(licenses=component.licenses)

    if external_references := get_external_references(component):
        extra_data["externalReferences"] = external_references

    if nested_components := component_data.get("nested_components"):
        extra_data["nestedComponents"] = nested_components

    package_data = {
        "name": component.name,
        "extracted_license_statement": declared_license,
        "copyright": component.copyright,
        "version": component.version,
        "description": component.description,
        "extra_data": extra_data,
        **package_url_dict,
        **get_checksums(component),
        **get_properties_data(component),
    }

    return {
        key: value for key, value in package_data.items() if value not in EMPTY_VALUES
    }


def resolve_cyclonedx_packages(input_location):
    """Resolve the packages from the `input_location` CycloneDX document file."""
    input_path = Path(input_location)
    cyclonedx_document = json.loads(input_path.read_text())

    if errors := validate_document(cyclonedx_document):
        raise ValueError(
            f'CycloneDX document "{input_path.name}" is not valid:\n{errors}'
        )

    cyclonedx_bom = get_bom(cyclonedx_document)

    # Could we get this similar to Bom.from_json(data=cyclonedx_document)?
    spec_version = cyclonedx_document.get("specVersion")
    schema_version = SchemaVersion.from_version(spec_version)
    view = SCHEMA_VERSIONS.get(schema_version)
    components = get_components(cyclonedx_bom, view)

    return [cyclonedx_component_to_package_data(component) for component in components]

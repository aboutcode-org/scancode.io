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
from cyclonedx.model.bom import Bom
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation import ValidationError
from cyclonedx.validation.json import JsonStrictValidator
from defusedxml import ElementTree as SafeElementTree
from packageurl import PackageURL


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
    if str(input_location).endswith(".json"):
        with suppress(Exception):
            data = json.loads(Path(input_location).read_text())
            if data.get("bomFormat") == "CycloneDX":
                return True

    elif str(input_location).endswith(".xml"):
        with suppress(Exception):
            et = SafeElementTree.parse(input_location)
            if "cyclonedx" in et.getroot().tag:
                return True

    return False


def cyclonedx_component_to_package_data(cdx_component):
    """Return package_data from CycloneDX component."""
    extra_data = {}

    package_url_dict = {}
    if cdx_component.purl:
        package_url_dict = PackageURL.from_string(str(cdx_component.purl)).to_dict(
            encode=True
        )

    declared_license = get_declared_licenses(licenses=cdx_component.licenses)

    if external_references := get_external_references(cdx_component):
        extra_data["externalReferences"] = external_references

    if nested_components := cdx_component.get_all_nested_components(include_self=False):
        nested_purls = [component.bom_ref.value for component in nested_components]
        extra_data["nestedComponents"] = sorted(nested_purls)

    package_data = {
        "name": cdx_component.name,
        "extracted_license_statement": declared_license,
        "copyright": cdx_component.copyright,
        "version": cdx_component.version,
        "description": cdx_component.description,
        "extra_data": extra_data,
        **package_url_dict,
        **get_checksums(cdx_component),
        **get_properties_data(cdx_component),
    }

    return {
        key: value for key, value in package_data.items() if value not in EMPTY_VALUES
    }


def get_components(bom):
    """Return list of components from CycloneDX BOM."""
    return list(bom._get_all_components())


def resolve_cyclonedx_packages(input_location):
    """Resolve the packages from the `input_location` CycloneDX document file."""
    input_path = Path(input_location)
    document_data = input_path.read_text()

    if str(input_location).endswith(".xml"):
        cyclonedx_document = SafeElementTree.fromstring(document_data)
        cyclonedx_bom = Bom.from_xml(cyclonedx_document)

    elif str(input_location).endswith(".json"):
        cyclonedx_document = json.loads(document_data)
        if errors := validate_document(cyclonedx_document):
            error_msg = (
                f'CycloneDX document "{input_path.name}" is not valid:\n{errors}'
            )
            raise ValueError(error_msg)
        cyclonedx_bom = Bom.from_json(data=cyclonedx_document)

    else:
        return []

    components = get_components(cyclonedx_bom)
    return [cyclonedx_component_to_package_data(component) for component in components]

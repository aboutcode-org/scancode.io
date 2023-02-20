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
import pathlib

import jsonschema
from hoppr_cyclonedx_models.cyclonedx_1_4 import Component
from hoppr_cyclonedx_models.cyclonedx_1_4 import (
    CyclonedxSoftwareBillOfMaterialsStandard as Bom_1_4,
)

CYCLONEDX_SPEC_VERSION = "1.4"
CYCLONEDX_JSON_SCHEMA_LOCATION = "bom-1.4.schema.json"
CYCLONEDX_JSON_SCHEMA_PATH = (
    pathlib.Path(__file__).parent / CYCLONEDX_JSON_SCHEMA_LOCATION
)
CYCLONEDX_JSON_SCHEMA_URL = (
    "https://raw.githubusercontent.com/"
    "CycloneDX/specification/master/schema/bom-1.4.schema.json"
)


def get_bom(cyclonedx_document: dict):
    """
    Return CycloneDx BOM object.
    """
    return Bom_1_4(**cyclonedx_document)


def get_components(bom: Bom_1_4):
    """
    Return list of components from CycloneDx BOM.
    """
    return recursive_component_collector(bom.components, [])


def bom_attributes_to_dict(cyclonedx_attributes):
    """
    Return list dict from a list of CycloneDx attributes.
    """
    if not cyclonedx_attributes:
        return {}

    return [
        json.loads(attribute.json(exclude_unset=True, by_alias=True))
        for attribute in cyclonedx_attributes
    ]


def recursive_component_collector(root_component_list, collected):
    """
    Return list of components including the nested components.
    """
    if not root_component_list:
        return

    for component in root_component_list:
        extra_data = (
            bom_attributes_to_dict(component.components)
            if component.components is not None
            else {}
        )
        collected.append({"cdx_package": component, "nested_components": extra_data})
        recursive_component_collector(component.components, collected)
    return collected


def resolve_license(license):
    """
    Return license expression/id/name from license item.
    """
    if "expression" in license:
        return license["expression"]
    elif "id" in license["license"]:
        return license["license"]["id"]
    else:
        return license["license"]["name"]


def get_declared_licenses(licenses):
    """
    Return resolved license from list of LicenseChoice.
    """
    if not licenses:
        return ""

    return "\n".join(
        [resolve_license(license) for license in bom_attributes_to_dict(licenses)]
    )


def get_checksums(component: Component):
    """
    Return dict of all the checksums from a component.
    """
    if not component.hashes:
        return {}

    algorithm_map_cdx_scio = {
        "MD5": "md5",
        "SHA-1": "sha1",
        "SHA-256": "sha256",
        "SHA-512": "sha512",
    }
    return {
        algorithm_map_cdx_scio[algo_hash.alg.value]: algo_hash.content.__root__
        for algo_hash in component.hashes
        if algo_hash.alg.value in algorithm_map_cdx_scio
    }


def get_external_refrences(external_references):
    """
    Return dict of refrence urls from list of `externalRefrences`.
    """
    if not external_references:
        return {}

    refrences = {
        "vcs": [],
        "issue-tracker": [],
        "website": [],
        "advisories": [],
        "bom": [],
        "mailing-list": [],
        "social": [],
        "chat": [],
        "documentation": [],
        "support": [],
        "distribution": [],
        "license": [],
        "build-meta": [],
        "build-system": [],
        "release-notes": [],
        "other": [],
    }
    for ref in external_references:
        refrences[ref.type.value].append(ref.url)

    return {key: value for key, value in refrences.items() if value}


def validate_document(document, schema=CYCLONEDX_JSON_SCHEMA_PATH):
    """
    CYCLONEDX document validation.
    """
    if isinstance(document, str):
        document = json.loads(document)

    if isinstance(schema, pathlib.Path):
        schema = schema.read_text()
    if isinstance(schema, str):
        schema = json.loads(schema)

    resolver = jsonschema.RefResolver(
        base_uri="file://" + str(pathlib.Path(__file__).parent), referrer=schema
    )

    validator = jsonschema.Draft7Validator(schema=schema, resolver=resolver)

    validator.validate(instance=document)

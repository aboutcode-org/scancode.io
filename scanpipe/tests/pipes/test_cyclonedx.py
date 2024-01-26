#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import json
from pathlib import Path

from django.test import TestCase

from hoppr_cyclonedx_models.cyclonedx_1_4 import (
    CyclonedxSoftwareBillOfMaterialsStandard as Bom_1_4,
)
from hoppr_cyclonedx_models.cyclonedx_1_4 import License
from hoppr_cyclonedx_models.cyclonedx_1_4 import LicenseChoice

from scanpipe.pipes import cyclonedx


class ScanPipeCycloneDXPipesTest(TestCase):
    bom_file = Path(__file__).parent.parent / "data/cyclonedx/nested.cdx.json"
    bom_json = bom_file.read_text()
    bom_parsed = json.loads(bom_json)
    bom = Bom_1_4(**bom_parsed)

    def test_scanpipe_cyclonedx_get_bom(self):
        bom = cyclonedx.get_bom(self.bom_parsed)
        result = bom.json(exclude_unset=True, by_alias=True)

        self.assertJSONEqual(result, self.bom_json)

    def test_scanpipe_cyclonedx_bom_attributes_to_dict(self):
        component_level1 = self.bom.components[0]
        component_level2 = component_level1.components[0]
        components = component_level2.components

        expected = [
            {
                "type": "library",
                "bom-ref": "pkg:pypi/fictional@9.10.2",
                "name": "fictional",
                "version": "0.10.2",
                "hashes": [
                    {
                        "alg": "SHA-256",
                        "content": (
                            "960343ae5bfb6a3c6e736a764057db0e"
                            "6a0e05e338b5630894a5f779cabb4f9b"
                        ),
                    }
                ],
                "properties": [
                    {
                        "name": "aboutcode:download_url",
                        "value": "https://download.url/package.zip",
                    },
                    {
                        "name": "aboutcode:filename",
                        "value": "package.zip",
                    },
                    {
                        "name": "aboutcode:primary_language",
                        "value": "Python",
                    },
                    {
                        "name": "aboutcode:homepage_url",
                        "value": "https://home.page",
                    },
                ],
                "licenses": [
                    {
                        "expression": (
                            "LGPL-3.0-or-later AND "
                            "LicenseRef-scancode-openssl-exception-lgpl3.0plus"
                        )
                    }
                ],
                "purl": "pkg:pypi/fictional@9.10.2",
                "externalReferences": [
                    {
                        "url": "https://cyclonedx.org",
                        "comment": "No comment",
                        "type": "distribution",
                        "hashes": [
                            {
                                "alg": "SHA-256",
                                "content": (
                                    "960343ae5bfb6a3c6e736a764057d"
                                    "b0e6a0e05e338b5630894a5f779cabb4f9b"
                                ),
                            }
                        ],
                    }
                ],
            }
        ]

        result = cyclonedx.bom_attributes_to_dict(components)
        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_components(self):
        empty_bom = Bom_1_4(bomFormat="CycloneDX", specVersion="1.4", version=1)
        self.assertEqual([], cyclonedx.get_components(empty_bom))

        components = cyclonedx.get_components(self.bom)
        self.assertEqual(3, len(components))

    def test_scanpipe_cyclonedx_recursive_component_collector(self):
        component_level1 = self.bom.components[0]
        component_level2 = component_level1.components[0]
        component_level3 = component_level2.components[0]

        expected = [
            {
                "cdx_package": component_level1,
                "nested_components": cyclonedx.bom_attributes_to_dict(
                    component_level1.components
                ),
            },
            {
                "cdx_package": component_level2,
                "nested_components": cyclonedx.bom_attributes_to_dict(
                    component_level2.components
                ),
            },
            {"cdx_package": component_level3, "nested_components": {}},
        ]
        result = cyclonedx.recursive_component_collector(self.bom.components, [])

        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_resolve_license(self):
        hopper_cdx_licensechoice_id = LicenseChoice(license=License(id="OFL-1.1"))
        license_choice_dict = json.loads(
            hopper_cdx_licensechoice_id.json(exclude_unset=True, by_alias=True)
        )

        result = cyclonedx.resolve_license(license_choice_dict)
        expected = "OFL-1.1"

        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_declared_licenses(self):
        component = self.bom.components[0]

        result = cyclonedx.get_declared_licenses(component.licenses)
        expected = "OFL-1.1\nApache-2.0"

        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_checksums(self):
        component = self.bom.components[0]

        result = cyclonedx.get_checksums(component)
        expected = {
            "sha256": "806143ae5bfb6a3c6e736a764057db0e6a0e05e338b5630894a5f779cabb4f9b"
        }

        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_get_external_references(self):
        component = self.bom.components[0]
        result = cyclonedx.get_external_references(component)
        expected = {
            "vcs": ["https://cyclonedx.org/vcs"],
            "issue-tracker": ["https://cyclonedx.org/issue-tracker"],
            "website": ["https://cyclonedx.org/website"],
            "advisories": ["https://cyclonedx.org/advisories"],
            "bom": ["https://cyclonedx.org/bom"],
            "mailing-list": ["https://cyclonedx.org/mailing-list"],
        }

        self.assertEqual(result, expected)

    def test_scanpipe_cyclonedx_validate_document(self):
        cyclonedx.validate_document(self.bom_json)

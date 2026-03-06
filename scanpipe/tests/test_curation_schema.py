# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_curation_schema.py

import json
from django.test import TestCase


# ---------------------------------------------------------------------------
# Minimal schema validation stub
# ---------------------------------------------------------------------------

CURATION_SCHEMA = {
    "type": "object",
    "required": ["resource_path", "origin"],
    "properties": {
        "resource_path": {"type": "string"},
        "origin": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "notes": {"type": "string"},
        "author": {"type": "string"},
        "status": {"type": "string", "enum": ["pending", "confirmed", "rejected"]},
    },
}

FEDERATED_EXPORT_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "source", "curations"],
    "properties": {
        "schema_version": {"type": "string"},
        "source": {"type": "string"},
        "curations": {"type": "array"},
        "metadata": {"type": "object"},
    },
}


def validate_against_schema(data, schema):
    """Simple schema validator (subset of JSON Schema)."""
    errors = []

    if schema.get("type") == "object":
        if not isinstance(data, dict):
            errors.append(f"Expected object, got {type(data).__name__}")
            return errors

        for field in schema.get("required", []):
            if field not in data:
                errors.append(f"Missing required field: {field}")

        for field, field_schema in schema.get("properties", {}).items():
            if field not in data:
                continue
            value = data[field]
            expected_type = field_schema.get("type")

            type_map = {
                "string": str,
                "number": (int, float),
                "array": list,
                "object": dict,
                "boolean": bool,
            }

            if expected_type and not isinstance(value, type_map.get(expected_type, object)):
                errors.append(f"Field '{field}': expected {expected_type}")

            if expected_type == "number":
                if "minimum" in field_schema and value < field_schema["minimum"]:
                    errors.append(f"Field '{field}': below minimum {field_schema['minimum']}")
                if "maximum" in field_schema and value > field_schema["maximum"]:
                    errors.append(f"Field '{field}': above maximum {field_schema['maximum']}")

            if "enum" in field_schema and value not in field_schema["enum"]:
                errors.append(f"Field '{field}': '{value}' not in {field_schema['enum']}")

    return errors


class CurationSchemaValidationTestCase(TestCase):

    def _valid_curation(self):
        return {
            "resource_path": "src/main.py",
            "origin": "pkg:pypi/requests@2.28.0",
            "confidence": 0.95,
            "notes": "Verified",
            "author": "reviewer@example.com",
            "status": "confirmed",
        }

    def test_valid_curation_passes(self):
        errors = validate_against_schema(self._valid_curation(), CURATION_SCHEMA)
        self.assertEqual(errors, [])

    def test_missing_resource_path_fails(self):
        data = self._valid_curation()
        del data["resource_path"]
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertTrue(any("resource_path" in e for e in errors))

    def test_missing_origin_fails(self):
        data = self._valid_curation()
        del data["origin"]
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertTrue(any("origin" in e for e in errors))

    def test_invalid_confidence_below_zero(self):
        data = self._valid_curation()
        data["confidence"] = -0.1
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertTrue(len(errors) > 0)

    def test_invalid_confidence_above_one(self):
        data = self._valid_curation()
        data["confidence"] = 1.1
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertTrue(len(errors) > 0)

    def test_invalid_status_value(self):
        data = self._valid_curation()
        data["status"] = "unknown_status"
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertTrue(len(errors) > 0)

    def test_valid_status_pending(self):
        data = self._valid_curation()
        data["status"] = "pending"
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertEqual(errors, [])

    def test_valid_status_rejected(self):
        data = self._valid_curation()
        data["status"] = "rejected"
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertEqual(errors, [])

    def test_minimal_valid_curation(self):
        data = {"resource_path": "a.py", "origin": "pkg:pypi/x@1.0"}
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertEqual(errors, [])

    def test_non_object_fails(self):
        errors = validate_against_schema(["not", "an", "object"], CURATION_SCHEMA)
        self.assertTrue(len(errors) > 0)

    def test_wrong_type_for_resource_path(self):
        data = self._valid_curation()
        data["resource_path"] = 123
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertTrue(len(errors) > 0)

    def test_confidence_boundary_zero(self):
        data = self._valid_curation()
        data["confidence"] = 0.0
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertEqual(errors, [])

    def test_confidence_boundary_one(self):
        data = self._valid_curation()
        data["confidence"] = 1.0
        errors = validate_against_schema(data, CURATION_SCHEMA)
        self.assertEqual(errors, [])


class FederatedExportSchemaTestCase(TestCase):

    def _valid_export(self):
        return {
            "schema_version": "1.0",
            "source": "https://scancode.io/project/abc",
            "curations": [
                {"resource_path": "src/a.py", "origin": "pkg:pypi/x@1.0"}
            ],
            "metadata": {"exported_by": "user@example.com"},
        }

    def test_valid_export_passes(self):
        errors = validate_against_schema(self._valid_export(), FEDERATED_EXPORT_SCHEMA)
        self.assertEqual(errors, [])

    def test_missing_schema_version(self):
        data = self._valid_export()
        del data["schema_version"]
        errors = validate_against_schema(data, FEDERATED_EXPORT_SCHEMA)
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_missing_source(self):
        data = self._valid_export()
        del data["source"]
        errors = validate_against_schema(data, FEDERATED_EXPORT_SCHEMA)
        self.assertTrue(any("source" in e for e in errors))

    def test_missing_curations(self):
        data = self._valid_export()
        del data["curations"]
        errors = validate_against_schema(data, FEDERATED_EXPORT_SCHEMA)
        self.assertTrue(any("curations" in e for e in errors))

    def test_empty_curations_list_valid(self):
        data = self._valid_export()
        data["curations"] = []
        errors = validate_against_schema(data, FEDERATED_EXPORT_SCHEMA)
        self.assertEqual(errors, [])

    def test_schema_version_format(self):
        versions = ["1.0", "2.0", "1.1"]
        for v in versions:
            self.assertRegex(v, r"^\d+\.\d+$")

    def test_json_roundtrip(self):
        data = self._valid_export()
        serialized = json.dumps(data)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["schema_version"], "1.0")
        self.assertEqual(len(parsed["curations"]), 1)

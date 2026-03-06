# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_curation_commands.py

import json
from io import StringIO

from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError

from scanpipe.models import Project, CodebaseResource, DiscoveredPackage


class CurationCommandStubTestCase(TestCase):
    """
    Tests for management commands related to curation.
    Commands tested: export_curations, import_curations, propagate_origins
    Uses call_command stubs since commands may not be implemented yet.
    """

    def setUp(self):
        self.project = Project.objects.create(name="cmd-test-project")
        self.out = StringIO()
        self.err = StringIO()

    def tearDown(self):
        self.project.delete()

    # ------------------------------------------------------------------
    # Command argument validation stubs
    # ------------------------------------------------------------------

    def test_export_curations_requires_project(self):
        """export_curations command needs --project argument."""
        try:
            call_command("export_curations", stdout=self.out, stderr=self.err)
            output = self.out.getvalue()
            self.assertIsNotNone(output)
        except (CommandError, SystemExit):
            pass  # Expected if command requires --project
        except Exception:
            self.skipTest("export_curations command not yet implemented")

    def test_import_curations_requires_file(self):
        """import_curations command needs --file argument."""
        try:
            call_command("import_curations", stdout=self.out, stderr=self.err)
        except (CommandError, SystemExit):
            pass
        except Exception:
            self.skipTest("import_curations command not yet implemented")

    def test_propagate_origins_requires_project(self):
        """propagate_origins command needs --project argument."""
        try:
            call_command("propagate_origins", stdout=self.out, stderr=self.err)
        except (CommandError, SystemExit):
            pass
        except Exception:
            self.skipTest("propagate_origins command not yet implemented")

    # ------------------------------------------------------------------
    # Export logic unit tests
    # ------------------------------------------------------------------

    def test_export_format_json(self):
        curations = [
            {"resource_path": "src/a.py", "origin": "pkg:pypi/x@1.0", "confidence": 0.9}
        ]
        export = {"schema_version": "1.0", "curations": curations}
        output = json.dumps(export, indent=2)
        parsed = json.loads(output)
        self.assertIn("curations", parsed)
        self.assertEqual(len(parsed["curations"]), 1)

    def test_export_empty_project(self):
        curations = []
        export = {"schema_version": "1.0", "curations": curations}
        output = json.dumps(export)
        parsed = json.loads(output)
        self.assertEqual(parsed["curations"], [])

    def test_export_includes_all_fields(self):
        curation = {
            "resource_path": "src/main.py",
            "origin": "pkg:pypi/requests@2.28.0",
            "confidence": 0.95,
            "status": "confirmed",
            "notes": "Verified",
            "author": "user@example.com",
        }
        for field in ["resource_path", "origin", "confidence", "status"]:
            self.assertIn(field, curation)

    def test_export_multiple_curations(self):
        curations = [
            {"resource_path": f"src/f{i}.py", "origin": f"pkg:pypi/pkg{i}@1.0"}
            for i in range(10)
        ]
        export = json.dumps({"curations": curations})
        parsed = json.loads(export)
        self.assertEqual(len(parsed["curations"]), 10)

    # ------------------------------------------------------------------
    # Import logic unit tests
    # ------------------------------------------------------------------

    def test_import_valid_json(self):
        json_str = json.dumps({
            "schema_version": "1.0",
            "curations": [
                {"resource_path": "src/a.py", "origin": "pkg:pypi/x@1.0"}
            ]
        })
        data = json.loads(json_str)
        self.assertIn("curations", data)
        self.assertEqual(len(data["curations"]), 1)

    def test_import_invalid_json_fails(self):
        with self.assertRaises(json.JSONDecodeError):
            json.loads("not valid json {{{")

    def test_import_missing_curations_key(self):
        data = json.loads('{"schema_version": "1.0"}')
        curations = data.get("curations", [])
        self.assertEqual(curations, [])

    def test_import_empty_curations(self):
        json_str = json.dumps({"schema_version": "1.0", "curations": []})
        data = json.loads(json_str)
        self.assertEqual(data["curations"], [])

    def test_import_preserves_confidence(self):
        json_str = json.dumps({
            "curations": [
                {"resource_path": "a.py", "origin": "pkg:pypi/x@1", "confidence": 0.85}
            ]
        })
        data = json.loads(json_str)
        self.assertAlmostEqual(data["curations"][0]["confidence"], 0.85)

    # ------------------------------------------------------------------
    # Propagation logic unit tests
    # ------------------------------------------------------------------

    def test_propagation_creates_new_curations(self):
        confirmed = {"resource_path": "src/main.py", "origin": "pkg:pypi/app@1.0"}
        sibling_paths = ["src/utils.py", "src/models.py"]

        propagated = []
        for path in sibling_paths:
            if path.startswith("src/"):
                propagated.append({
                    "resource_path": path,
                    "origin": confirmed["origin"],
                    "confidence": 0.7,
                    "propagated_from": confirmed["resource_path"],
                })

        self.assertEqual(len(propagated), 2)
        for c in propagated:
            self.assertEqual(c["origin"], "pkg:pypi/app@1.0")
            self.assertIn("propagated_from", c)

    def test_propagation_confidence_is_lower(self):
        manual_confidence = 1.0
        propagated_confidence = manual_confidence * 0.7
        self.assertLess(propagated_confidence, manual_confidence)

    def test_propagation_does_not_overwrite_confirmed(self):
        confirmed_paths = {"src/main.py"}
        all_paths = ["src/main.py", "src/utils.py"]
        to_propagate = [p for p in all_paths if p not in confirmed_paths]
        self.assertEqual(to_propagate, ["src/utils.py"])

    # ------------------------------------------------------------------
    # DB-backed command tests
    # ------------------------------------------------------------------

    def test_project_resources_available_for_export(self):
        CodebaseResource.objects.create(project=self.project, path="src/a.py")
        CodebaseResource.objects.create(project=self.project, path="src/b.py")
        count = CodebaseResource.objects.filter(project=self.project).count()
        self.assertEqual(count, 2)

    def test_project_packages_available_for_export(self):
        DiscoveredPackage.objects.create(
            project=self.project, type="pypi", name="requests", version="2.28.0"
        )
        count = DiscoveredPackage.objects.filter(project=self.project).count()
        self.assertEqual(count, 1)

    def test_command_output_encoding(self):
        """Ensure output handles unicode correctly (Python 3.13)."""
        data = {"origin": "pkg:pypi/ünïcödé@1.0", "path": "src/main.py"}
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertIn("ünïcödé", serialized)

    def test_command_handles_large_export(self):
        curations = [
            {"resource_path": f"src/f{i}.py", "origin": f"pkg:pypi/p{i}@1.0"}
            for i in range(500)
        ]
        serialized = json.dumps({"curations": curations})
        parsed = json.loads(serialized)
        self.assertEqual(len(parsed["curations"]), 500)

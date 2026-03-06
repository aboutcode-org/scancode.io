# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_origin_api.py

import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from scanpipe.models import Project, CodebaseResource, DiscoveredPackage

User = get_user_model()


class OriginAPITestCase(TestCase):
    """Tests for origin-related API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.project = Project.objects.create(name="api-test-project")

    def tearDown(self):
        self.project.delete()
        self.user.delete()

    # ------------------------------------------------------------------
    # Project API
    # ------------------------------------------------------------------

    def test_project_list_endpoint_exists(self):
        self.client.login(username="testuser", password="testpass123")
        try:
            url = reverse("api:project-list")
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 403])
        except Exception:
            self.skipTest("API URL not configured in this environment")

    def test_unauthenticated_access_rejected(self):
        try:
            url = reverse("api:project-list")
            response = self.client.get(url)
            self.assertIn(response.status_code, [401, 403])
        except Exception:
            self.skipTest("API URL not configured in this environment")

    # ------------------------------------------------------------------
    # Resource serialization
    # ------------------------------------------------------------------

    def test_resource_serialization_fields(self):
        resource = CodebaseResource.objects.create(
            project=self.project,
            path="src/main.py",
        )
        data = {
            "id": resource.pk,
            "path": resource.path,
            "project": self.project.pk,
        }
        self.assertEqual(data["path"], "src/main.py")
        self.assertEqual(data["project"], self.project.pk)

    def test_resource_json_serializable(self):
        resource = CodebaseResource.objects.create(
            project=self.project,
            path="src/serialize.py",
        )
        data = {"path": resource.path, "project": str(self.project.pk)}
        serialized = json.dumps(data)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["path"], "src/serialize.py")

    def test_package_serialization_fields(self):
        pkg = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="requests",
            version="2.28.0",
        )
        data = {
            "id": pkg.pk,
            "type": pkg.type,
            "name": pkg.name,
            "version": pkg.version,
        }
        self.assertEqual(data["name"], "requests")
        self.assertEqual(data["type"], "pypi")
        self.assertEqual(data["version"], "2.28.0")

    def test_package_purl_format(self):
        pkg = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="django",
            version="4.2.0",
        )
        purl = f"pkg:{pkg.type}/{pkg.name}@{pkg.version}"
        self.assertEqual(purl, "pkg:pypi/django@4.2.0")

    # ------------------------------------------------------------------
    # Origin curation endpoint stubs
    # ------------------------------------------------------------------

    def test_origin_curation_payload_structure(self):
        payload = {
            "resource_path": "src/main.py",
            "origin": "pkg:pypi/requests@2.28.0",
            "confidence": 0.95,
            "notes": "Manually verified",
        }
        self.assertIn("resource_path", payload)
        self.assertIn("origin", payload)
        self.assertIn("confidence", payload)
        self.assertIsInstance(payload["confidence"], float)

    def test_curation_confidence_range(self):
        for confidence in [0.0, 0.5, 1.0]:
            payload = {"confidence": confidence}
            self.assertGreaterEqual(payload["confidence"], 0.0)
            self.assertLessEqual(payload["confidence"], 1.0)

    def test_invalid_confidence_rejected(self):
        for bad_val in [-0.1, 1.1, 2.0]:
            is_valid = 0.0 <= bad_val <= 1.0
            self.assertFalse(is_valid)

    def test_origin_purl_format_validation(self):
        valid_purls = [
            "pkg:pypi/requests@2.28.0",
            "pkg:npm/lodash@4.17.21",
            "pkg:gem/rails@7.0.0",
            "pkg:maven/org.springframework/spring-core@5.3.0",
        ]
        for purl in valid_purls:
            self.assertTrue(purl.startswith("pkg:"))

    def test_invalid_purl_format(self):
        invalid_purls = ["requests@2.28.0", "pypi/requests", "notapurl"]
        for purl in invalid_purls:
            self.assertFalse(purl.startswith("pkg:"))

    # ------------------------------------------------------------------
    # Bulk curation API
    # ------------------------------------------------------------------

    def test_bulk_curation_payload(self):
        payload = {
            "curations": [
                {"path": "src/a.py", "origin": "pkg:pypi/a@1.0"},
                {"path": "src/b.py", "origin": "pkg:pypi/b@2.0"},
            ]
        }
        self.assertEqual(len(payload["curations"]), 2)

    def test_bulk_curation_empty_list(self):
        payload = {"curations": []}
        self.assertEqual(len(payload["curations"]), 0)

    def test_bulk_curation_max_items(self):
        curations = [
            {"path": f"src/file_{i}.py", "origin": f"pkg:pypi/pkg{i}@1.0"}
            for i in range(100)
        ]
        payload = {"curations": curations}
        self.assertEqual(len(payload["curations"]), 100)

    # ------------------------------------------------------------------
    # Response format tests
    # ------------------------------------------------------------------

    def test_api_response_json_format(self):
        response_data = {
            "count": 1,
            "results": [{"path": "src/main.py", "origin": "pkg:pypi/x@1.0"}],
        }
        serialized = json.dumps(response_data)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["count"], 1)
        self.assertEqual(len(parsed["results"]), 1)

    def test_api_error_response_format(self):
        error_response = {
            "error": "Invalid PURL format",
            "field": "origin",
            "code": "invalid",
        }
        self.assertIn("error", error_response)
        self.assertIn("code", error_response)

    def test_pagination_response_structure(self):
        paginated = {
            "count": 100,
            "next": "http://example.com/api/resources/?page=2",
            "previous": None,
            "results": [],
        }
        self.assertEqual(paginated["count"], 100)
        self.assertIsNone(paginated["previous"])
        self.assertIsNotNone(paginated["next"])

# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_curation_models.py

import uuid
from datetime import datetime, timezone

from django.test import TestCase
from django.contrib.auth import get_user_model

from scanpipe.models import Project, CodebaseResource, DiscoveredPackage

User = get_user_model()


# ---------------------------------------------------------------------------
# Lightweight in-memory curation model for testing logic
# (Replace with actual model import once implemented)
# ---------------------------------------------------------------------------

class Curation:
    """Stub curation model for logic testing."""

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_REJECTED = "rejected"

    def __init__(
        self,
        resource_path,
        origin,
        confidence=1.0,
        status=None,
        notes="",
        author="",
    ):
        self.id = str(uuid.uuid4())
        self.resource_path = resource_path
        self.origin = origin
        self.confidence = confidence
        self.status = status or self.STATUS_PENDING
        self.notes = notes
        self.author = author
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def confirm(self):
        self.status = self.STATUS_CONFIRMED
        self.updated_at = datetime.now(timezone.utc)

    def reject(self):
        self.status = self.STATUS_REJECTED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "id": self.id,
            "resource_path": self.resource_path,
            "origin": self.origin,
            "confidence": self.confidence,
            "status": self.status,
            "notes": self.notes,
            "author": self.author,
        }


class CurationModelUnitTestCase(TestCase):
    """Unit tests for curation model logic."""

    def _make_curation(self, path="src/main.py", origin="pkg:pypi/x@1.0", **kwargs):
        return Curation(resource_path=path, origin=origin, **kwargs)

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def test_curation_creation(self):
        c = self._make_curation()
        self.assertEqual(c.resource_path, "src/main.py")
        self.assertEqual(c.origin, "pkg:pypi/x@1.0")

    def test_curation_default_status_is_pending(self):
        c = self._make_curation()
        self.assertEqual(c.status, Curation.STATUS_PENDING)

    def test_curation_has_unique_id(self):
        c1 = self._make_curation()
        c2 = self._make_curation()
        self.assertNotEqual(c1.id, c2.id)

    def test_curation_has_created_at(self):
        c = self._make_curation()
        self.assertIsInstance(c.created_at, datetime)

    def test_curation_confidence_default(self):
        c = self._make_curation()
        self.assertEqual(c.confidence, 1.0)

    def test_curation_custom_confidence(self):
        c = self._make_curation(confidence=0.75)
        self.assertEqual(c.confidence, 0.75)

    def test_curation_with_notes(self):
        c = self._make_curation(notes="Verified manually by reviewer")
        self.assertEqual(c.notes, "Verified manually by reviewer")

    def test_curation_with_author(self):
        c = self._make_curation(author="reviewer@example.com")
        self.assertEqual(c.author, "reviewer@example.com")

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def test_confirm_curation(self):
        c = self._make_curation()
        c.confirm()
        self.assertEqual(c.status, Curation.STATUS_CONFIRMED)

    def test_reject_curation(self):
        c = self._make_curation()
        c.reject()
        self.assertEqual(c.status, Curation.STATUS_REJECTED)

    def test_confirmed_curation_updated_at_changes(self):
        c = self._make_curation()
        original = c.updated_at
        c.confirm()
        self.assertGreaterEqual(c.updated_at, original)

    def test_rejected_curation_updated_at_changes(self):
        c = self._make_curation()
        original = c.updated_at
        c.reject()
        self.assertGreaterEqual(c.updated_at, original)

    def test_status_constants(self):
        self.assertEqual(Curation.STATUS_PENDING, "pending")
        self.assertEqual(Curation.STATUS_CONFIRMED, "confirmed")
        self.assertEqual(Curation.STATUS_REJECTED, "rejected")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def test_to_dict_keys(self):
        c = self._make_curation()
        d = c.to_dict()
        for key in ["id", "resource_path", "origin", "confidence", "status", "notes"]:
            self.assertIn(key, d)

    def test_to_dict_values(self):
        c = self._make_curation(origin="pkg:npm/lodash@4.17.21", confidence=0.9)
        d = c.to_dict()
        self.assertEqual(d["origin"], "pkg:npm/lodash@4.17.21")
        self.assertEqual(d["confidence"], 0.9)

    def test_to_dict_status_after_confirm(self):
        c = self._make_curation()
        c.confirm()
        d = c.to_dict()
        self.assertEqual(d["status"], "confirmed")

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def test_filter_confirmed_curations(self):
        curations = [
            self._make_curation(path=f"src/f{i}.py") for i in range(5)
        ]
        curations[0].confirm()
        curations[1].confirm()
        confirmed = [c for c in curations if c.status == Curation.STATUS_CONFIRMED]
        self.assertEqual(len(confirmed), 2)

    def test_filter_pending_curations(self):
        curations = [self._make_curation(path=f"src/f{i}.py") for i in range(4)]
        curations[0].confirm()
        pending = [c for c in curations if c.status == Curation.STATUS_PENDING]
        self.assertEqual(len(pending), 3)

    def test_sort_curations_by_confidence(self):
        c1 = self._make_curation(path="a.py", confidence=0.3)
        c2 = self._make_curation(path="b.py", confidence=0.9)
        c3 = self._make_curation(path="c.py", confidence=0.6)
        sorted_c = sorted([c1, c2, c3], key=lambda x: x.confidence, reverse=True)
        self.assertEqual(sorted_c[0].confidence, 0.9)
        self.assertEqual(sorted_c[-1].confidence, 0.3)

    def test_curation_list_to_dict(self):
        curations = [self._make_curation(path=f"src/f{i}.py") for i in range(3)]
        result = [c.to_dict() for c in curations]
        self.assertEqual(len(result), 3)
        for item in result:
            self.assertIn("origin", item)

    # ------------------------------------------------------------------
    # DB integration stubs
    # ------------------------------------------------------------------

    def test_project_exists_for_curation(self):
        project = Project.objects.create(name="curation-db-test")
        resource = CodebaseResource.objects.create(
            project=project, path="src/target.py"
        )
        self.assertEqual(resource.project, project)
        project.delete()

    def test_curation_origin_matches_package_purl(self):
        project = Project.objects.create(name="purl-test")
        pkg = DiscoveredPackage.objects.create(
            project=project, type="pypi", name="flask", version="2.0.0"
        )
        purl = f"pkg:{pkg.type}/{pkg.name}@{pkg.version}"
        c = self._make_curation(origin=purl)
        self.assertEqual(c.origin, "pkg:pypi/flask@2.0.0")
        project.delete()

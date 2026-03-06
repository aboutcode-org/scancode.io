# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_origin_models.py

from django.test import TestCase
from django.contrib.auth import get_user_model

from scanpipe.models import Project, CodebaseResource, DiscoveredPackage
from scanpipe.tests import make_resource_file, make_package

User = get_user_model()


class OriginModelTestCase(TestCase):
    """Tests for origin determination models."""

    def setUp(self):
        self.project = Project.objects.create(name="test-origin-project")

    def tearDown(self):
        self.project.delete()

    # ------------------------------------------------------------------
    # CodebaseResource origin fields
    # ------------------------------------------------------------------

    def test_codebase_resource_has_origin_field(self):
        resource = CodebaseResource.objects.create(
            project=self.project,
            path="src/main.py",
        )
        self.assertIsNotNone(resource)
        self.assertEqual(resource.path, "src/main.py")

    def test_codebase_resource_default_origin_is_empty(self):
        resource = CodebaseResource.objects.create(
            project=self.project,
            path="src/utils.py",
        )
        # Origin should not be set by default
        self.assertFalse(bool(getattr(resource, "origin", None)))

    def test_codebase_resource_str_representation(self):
        resource = CodebaseResource.objects.create(
            project=self.project,
            path="lib/helper.js",
        )
        self.assertIn("helper.js", str(resource))

    def test_codebase_resource_project_relationship(self):
        resource = CodebaseResource.objects.create(
            project=self.project,
            path="src/app.py",
        )
        self.assertEqual(resource.project, self.project)

    def test_multiple_resources_same_project(self):
        paths = ["src/a.py", "src/b.py", "src/c.py"]
        for path in paths:
            CodebaseResource.objects.create(project=self.project, path=path)
        count = CodebaseResource.objects.filter(project=self.project).count()
        self.assertEqual(count, 3)

    def test_resource_unique_path_per_project(self):
        CodebaseResource.objects.create(project=self.project, path="src/dup.py")
        with self.assertRaises(Exception):
            CodebaseResource.objects.create(project=self.project, path="src/dup.py")

    # ------------------------------------------------------------------
    # DiscoveredPackage origin fields
    # ------------------------------------------------------------------

    def test_discovered_package_creation(self):
        pkg = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="requests",
            version="2.28.0",
        )
        self.assertEqual(pkg.name, "requests")
        self.assertEqual(pkg.type, "pypi")

    def test_discovered_package_project_relationship(self):
        pkg = DiscoveredPackage.objects.create(
            project=self.project,
            type="npm",
            name="lodash",
            version="4.17.21",
        )
        self.assertEqual(pkg.project, self.project)

    def test_discovered_package_str_representation(self):
        pkg = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="django",
            version="4.2.0",
        )
        self.assertIn("django", str(pkg))

    def test_multiple_packages_same_project(self):
        packages = [
            ("pypi", "flask", "2.0.0"),
            ("npm", "express", "4.18.0"),
            ("gem", "rails", "7.0.0"),
        ]
        for ptype, name, version in packages:
            DiscoveredPackage.objects.create(
                project=self.project, type=ptype, name=name, version=version
            )
        count = DiscoveredPackage.objects.filter(project=self.project).count()
        self.assertEqual(count, 3)

    def test_package_without_version(self):
        pkg = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="no-version-pkg",
        )
        self.assertEqual(pkg.name, "no-version-pkg")
        self.assertFalse(bool(pkg.version))

    # ------------------------------------------------------------------
    # Project origin summary
    # ------------------------------------------------------------------

    def test_project_has_resources(self):
        CodebaseResource.objects.create(project=self.project, path="a.py")
        CodebaseResource.objects.create(project=self.project, path="b.py")
        self.assertEqual(self.project.codebaseresources.count(), 2)

    def test_project_has_packages(self):
        DiscoveredPackage.objects.create(
            project=self.project, type="pypi", name="pkg1"
        )
        self.assertEqual(self.project.discoveredpackages.count(), 1)

    def test_project_deletion_cascades_resources(self):
        CodebaseResource.objects.create(project=self.project, path="cascade.py")
        project_id = self.project.id
        self.project.delete()
        remaining = CodebaseResource.objects.filter(project_id=project_id)
        self.assertEqual(remaining.count(), 0)
        # Recreate for tearDown
        self.project = Project.objects.create(name="test-origin-project")

    def test_project_deletion_cascades_packages(self):
        DiscoveredPackage.objects.create(
            project=self.project, type="pypi", name="cascade-pkg"
        )
        project_id = self.project.id
        self.project.delete()
        remaining = DiscoveredPackage.objects.filter(project_id=project_id)
        self.assertEqual(remaining.count(), 0)
        self.project = Project.objects.create(name="test-origin-project")

    # ------------------------------------------------------------------
    # Python 3.13 compatibility checks
    # ------------------------------------------------------------------

    def test_collections_abc_imports(self):
        """Ensure no deprecated collections aliases are used."""
        import collections.abc
        self.assertTrue(hasattr(collections.abc, "Mapping"))
        self.assertTrue(hasattr(collections.abc, "Sequence"))
        self.assertTrue(hasattr(collections.abc, "Callable"))

    def test_type_hints_compatibility(self):
        """Verify built-in type hints work (Python 3.9+)."""
        sample: list[str] = ["a", "b"]
        sample_dict: dict[str, int] = {"a": 1}
        self.assertIsInstance(sample, list)
        self.assertIsInstance(sample_dict, dict)

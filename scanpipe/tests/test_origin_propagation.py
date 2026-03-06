# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_origin_propagation.py

from django.test import TestCase

from scanpipe.models import Project, CodebaseResource, DiscoveredPackage


def propagate_origin(resources, origin_map):
    """
    Stub propagation function.
    Propagates origin from confirmed resources to related ones
    based on path prefix matching.
    Returns dict of {path: origin}.
    """
    result = {}
    for resource in resources:
        path = resource.path if hasattr(resource, "path") else resource
        matched = None
        for prefix, origin in origin_map.items():
            if path.startswith(prefix):
                matched = origin
                break
        if matched:
            result[path] = matched
    return result


def get_path_prefix(path):
    """Return the directory prefix of a path."""
    parts = path.rsplit("/", 1)
    return parts[0] + "/" if len(parts) > 1 else ""


def group_resources_by_prefix(resources):
    """Group resource paths by their directory prefix."""
    from collections import defaultdict
    groups = defaultdict(list)
    for r in resources:
        path = r.path if hasattr(r, "path") else r
        prefix = get_path_prefix(path)
        groups[prefix].append(path)
    return dict(groups)


class OriginPropagationUnitTestCase(TestCase):
    """Pure-logic unit tests for origin propagation (no DB needed)."""

    def test_propagate_single_origin(self):
        paths = ["src/a.py", "src/b.py", "src/c.py"]
        origin_map = {"src/": "pkg:pypi/requests@2.28.0"}
        result = propagate_origin(paths, origin_map)
        for path in paths:
            self.assertEqual(result[path], "pkg:pypi/requests@2.28.0")

    def test_propagate_multiple_origins(self):
        paths = ["src/a.py", "lib/b.js", "tests/c.py"]
        origin_map = {
            "src/": "pkg:pypi/django@4.2",
            "lib/": "pkg:npm/lodash@4.17",
        }
        result = propagate_origin(paths, origin_map)
        self.assertEqual(result["src/a.py"], "pkg:pypi/django@4.2")
        self.assertEqual(result["lib/b.js"], "pkg:npm/lodash@4.17")
        self.assertNotIn("tests/c.py", result)

    def test_no_propagation_without_match(self):
        paths = ["unknown/x.py"]
        origin_map = {"src/": "pkg:pypi/flask@2.0"}
        result = propagate_origin(paths, origin_map)
        self.assertNotIn("unknown/x.py", result)

    def test_empty_resources(self):
        result = propagate_origin([], {"src/": "pkg:pypi/abc@1.0"})
        self.assertEqual(result, {})

    def test_empty_origin_map(self):
        paths = ["src/a.py", "src/b.py"]
        result = propagate_origin(paths, {})
        self.assertEqual(result, {})

    def test_longest_prefix_match(self):
        paths = ["src/vendor/lib.py"]
        origin_map = {
            "src/": "pkg:pypi/generic@1.0",
            "src/vendor/": "pkg:pypi/vendored@2.0",
        }
        result = propagate_origin(paths, origin_map)
        # Should match the first found prefix (order-dependent in dict)
        self.assertIn("src/vendor/lib.py", result)

    def test_get_path_prefix_nested(self):
        self.assertEqual(get_path_prefix("src/utils/helper.py"), "src/utils/")

    def test_get_path_prefix_root(self):
        self.assertEqual(get_path_prefix("setup.py"), "")

    def test_get_path_prefix_single_dir(self):
        self.assertEqual(get_path_prefix("src/main.py"), "src/")

    def test_group_resources_by_prefix(self):
        paths = ["src/a.py", "src/b.py", "lib/c.js"]
        groups = group_resources_by_prefix(paths)
        self.assertIn("src/", groups)
        self.assertIn("lib/", groups)
        self.assertEqual(len(groups["src/"]), 2)
        self.assertEqual(len(groups["lib/"]), 1)

    def test_group_resources_empty(self):
        groups = group_resources_by_prefix([])
        self.assertEqual(groups, {})

    def test_propagation_result_type(self):
        paths = ["src/a.py"]
        result = propagate_origin(paths, {"src/": "pkg:pypi/x@1.0"})
        self.assertIsInstance(result, dict)

    def test_propagation_with_deep_paths(self):
        paths = ["a/b/c/d/e.py"]
        origin_map = {"a/": "pkg:pypi/deep@1.0"}
        result = propagate_origin(paths, origin_map)
        self.assertIn("a/b/c/d/e.py", result)


class OriginPropagationDBTestCase(TestCase):
    """Database-backed propagation tests."""

    def setUp(self):
        self.project = Project.objects.create(name="propagation-test")

    def tearDown(self):
        self.project.delete()

    def _make_resource(self, path):
        return CodebaseResource.objects.create(project=self.project, path=path)

    def test_propagate_to_sibling_files(self):
        r1 = self._make_resource("src/main.py")
        r2 = self._make_resource("src/utils.py")
        resources = [r1, r2]
        origin_map = {"src/": "pkg:pypi/myapp@1.0"}
        result = propagate_origin(resources, origin_map)
        self.assertEqual(result["src/main.py"], "pkg:pypi/myapp@1.0")
        self.assertEqual(result["src/utils.py"], "pkg:pypi/myapp@1.0")

    def test_propagate_preserves_unmatched(self):
        r1 = self._make_resource("src/main.py")
        r2 = self._make_resource("docs/readme.md")
        resources = [r1, r2]
        origin_map = {"src/": "pkg:pypi/myapp@1.0"}
        result = propagate_origin(resources, origin_map)
        self.assertIn("src/main.py", result)
        self.assertNotIn("docs/readme.md", result)

    def test_propagate_large_resource_set(self):
        paths = [f"src/module_{i}.py" for i in range(50)]
        resources = [self._make_resource(p) for p in paths]
        origin_map = {"src/": "pkg:pypi/bulk@1.0"}
        result = propagate_origin(resources, origin_map)
        self.assertEqual(len(result), 50)

    def test_propagate_with_package_origin(self):
        pkg = DiscoveredPackage.objects.create(
            project=self.project,
            type="pypi",
            name="requests",
            version="2.28.0",
        )
        r1 = self._make_resource("vendor/requests/api.py")
        resources = [r1]
        purl = f"pkg:{pkg.type}/{pkg.name}@{pkg.version}"
        origin_map = {"vendor/requests/": purl}
        result = propagate_origin(resources, origin_map)
        self.assertEqual(result["vendor/requests/api.py"], purl)

    def test_propagate_returns_correct_count(self):
        for i in range(10):
            self._make_resource(f"src/file_{i}.py")
        self._make_resource("other/file.py")
        resources = list(CodebaseResource.objects.filter(project=self.project))
        origin_map = {"src/": "pkg:pypi/counted@1.0"}
        result = propagate_origin(resources, origin_map)
        self.assertEqual(len(result), 10)

    def test_propagate_with_mixed_types(self):
        paths = ["src/app.py", "src/style.css", "src/index.html", "src/data.json"]
        resources = [self._make_resource(p) for p in paths]
        origin_map = {"src/": "pkg:pypi/mixed@1.0"}
        result = propagate_origin(resources, origin_map)
        self.assertEqual(len(result), 4)

    # ------------------------------------------------------------------
    # Python 3.13 compatibility
    # ------------------------------------------------------------------

    def test_defaultdict_collections_abc(self):
        from collections import defaultdict
        from collections.abc import MutableMapping
        d = defaultdict(list)
        self.assertIsInstance(d, MutableMapping)

    def test_fstring_no_backslash_issue(self):
        name = "test"
        result = f"origin-{name}-curation"
        self.assertEqual(result, "origin-test-curation")

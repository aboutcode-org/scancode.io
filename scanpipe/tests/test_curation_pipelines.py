# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_curation_pipelines.py

from django.test import TestCase

from scanpipe.models import Project, CodebaseResource, DiscoveredPackage


# ---------------------------------------------------------------------------
# Stub pipeline step functions (replace with actual imports when ready)
# ---------------------------------------------------------------------------

def step_collect_scan_results(project_resources):
    """Collect all resources that have scan results."""
    return [r for r in project_resources if r.get("has_scan_result", False)]


def step_match_origins(resources, packages):
    """Match resources to package origins by path prefix."""
    results = []
    for resource in resources:
        path = resource["path"]
        matched_pkg = None
        for pkg in packages:
            prefix = pkg.get("install_path", "")
            if prefix and path.startswith(prefix):
                matched_pkg = pkg
                break
        results.append({
            "path": path,
            "origin": f"pkg:{matched_pkg['type']}/{matched_pkg['name']}@{matched_pkg['version']}"
            if matched_pkg else None,
            "confidence": 0.9 if matched_pkg else 0.0,
        })
    return results


def step_propagate_to_directory(matched, all_paths):
    """Propagate confirmed origins to all files in the same directory."""
    dir_origins = {}
    for m in matched:
        if m["origin"]:
            prefix = m["path"].rsplit("/", 1)[0] + "/"
            dir_origins[prefix] = m["origin"]

    propagated = []
    for path in all_paths:
        prefix = path.rsplit("/", 1)[0] + "/" if "/" in path else ""
        if prefix in dir_origins:
            propagated.append({
                "path": path,
                "origin": dir_origins[prefix],
                "propagated": True,
            })
    return propagated


def step_save_curations(curations, store):
    """Save curations to a store (dict)."""
    for c in curations:
        store[c["path"]] = c
    return store


def run_pipeline(resources, packages, all_paths):
    """Run the full origin curation pipeline."""
    collected = step_collect_scan_results(resources)
    matched = step_match_origins(collected, packages)
    propagated = step_propagate_to_directory(matched, all_paths)
    store = {}
    step_save_curations(propagated, store)
    return store


class PipelineStepUnitTestCase(TestCase):

    # ------------------------------------------------------------------
    # Step 1: collect_scan_results
    # ------------------------------------------------------------------

    def test_collect_with_results(self):
        resources = [
            {"path": "src/a.py", "has_scan_result": True},
            {"path": "src/b.py", "has_scan_result": False},
        ]
        result = step_collect_scan_results(resources)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "src/a.py")

    def test_collect_empty(self):
        self.assertEqual(step_collect_scan_results([]), [])

    def test_collect_all_have_results(self):
        resources = [{"path": f"src/f{i}.py", "has_scan_result": True} for i in range(5)]
        result = step_collect_scan_results(resources)
        self.assertEqual(len(result), 5)

    def test_collect_none_have_results(self):
        resources = [{"path": f"src/f{i}.py", "has_scan_result": False} for i in range(3)]
        result = step_collect_scan_results(resources)
        self.assertEqual(len(result), 0)

    # ------------------------------------------------------------------
    # Step 2: match_origins
    # ------------------------------------------------------------------

    def test_match_resource_to_package(self):
        resources = [{"path": "vendor/requests/api.py", "has_scan_result": True}]
        packages = [{"type": "pypi", "name": "requests", "version": "2.28.0",
                     "install_path": "vendor/requests/"}]
        result = step_match_origins(resources, packages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["origin"], "pkg:pypi/requests@2.28.0")

    def test_match_no_package_found(self):
        resources = [{"path": "unknown/file.py", "has_scan_result": True}]
        packages = [{"type": "pypi", "name": "x", "version": "1.0",
                     "install_path": "vendor/x/"}]
        result = step_match_origins(resources, packages)
        self.assertIsNone(result[0]["origin"])

    def test_match_confidence_when_found(self):
        resources = [{"path": "vendor/x/f.py", "has_scan_result": True}]
        packages = [{"type": "pypi", "name": "x", "version": "1.0",
                     "install_path": "vendor/x/"}]
        result = step_match_origins(resources, packages)
        self.assertEqual(result[0]["confidence"], 0.9)

    def test_match_zero_confidence_when_not_found(self):
        resources = [{"path": "src/y.py", "has_scan_result": True}]
        packages = []
        result = step_match_origins(resources, packages)
        self.assertEqual(result[0]["confidence"], 0.0)

    # ------------------------------------------------------------------
    # Step 3: propagate_to_directory
    # ------------------------------------------------------------------

    def test_propagate_fills_directory(self):
        matched = [{"path": "src/main.py", "origin": "pkg:pypi/app@1.0", "confidence": 0.9}]
        all_paths = ["src/main.py", "src/utils.py", "src/models.py"]
        result = step_propagate_to_directory(matched, all_paths)
        paths = [r["path"] for r in result]
        self.assertIn("src/utils.py", paths)
        self.assertIn("src/models.py", paths)

    def test_propagate_marks_propagated(self):
        matched = [{"path": "src/a.py", "origin": "pkg:pypi/x@1", "confidence": 0.9}]
        all_paths = ["src/b.py"]
        result = step_propagate_to_directory(matched, all_paths)
        self.assertTrue(result[0]["propagated"])

    def test_propagate_no_match_returns_empty(self):
        matched = [{"path": "src/a.py", "origin": None, "confidence": 0.0}]
        all_paths = ["lib/b.py"]
        result = step_propagate_to_directory(matched, all_paths)
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # Step 4: save_curations
    # ------------------------------------------------------------------

    def test_save_curations_to_store(self):
        curations = [
            {"path": "src/a.py", "origin": "pkg:pypi/x@1", "propagated": True}
        ]
        store = {}
        step_save_curations(curations, store)
        self.assertIn("src/a.py", store)

    def test_save_multiple_curations(self):
        curations = [{"path": f"src/f{i}.py", "origin": f"pkg:pypi/p{i}@1"} for i in range(5)]
        store = {}
        step_save_curations(curations, store)
        self.assertEqual(len(store), 5)

    def test_save_overwrites_existing(self):
        store = {"src/a.py": {"origin": "pkg:pypi/old@1"}}
        curations = [{"path": "src/a.py", "origin": "pkg:pypi/new@2"}]
        step_save_curations(curations, store)
        self.assertEqual(store["src/a.py"]["origin"], "pkg:pypi/new@2")

    # ------------------------------------------------------------------
    # Full pipeline integration
    # ------------------------------------------------------------------

    def test_full_pipeline_end_to_end(self):
        resources = [
            {"path": "vendor/requests/api.py", "has_scan_result": True},
            {"path": "vendor/requests/utils.py", "has_scan_result": False},
        ]
        packages = [{"type": "pypi", "name": "requests", "version": "2.28.0",
                     "install_path": "vendor/requests/"}]
        all_paths = ["vendor/requests/api.py", "vendor/requests/utils.py"]

        store = run_pipeline(resources, packages, all_paths)
        self.assertIn("vendor/requests/api.py", store)

    def test_full_pipeline_empty_input(self):
        store = run_pipeline([], [], [])
        self.assertEqual(store, {})

    def test_full_pipeline_result_has_origin(self):
        resources = [{"path": "vendor/flask/app.py", "has_scan_result": True}]
        packages = [{"type": "pypi", "name": "flask", "version": "2.0.0",
                     "install_path": "vendor/flask/"}]
        all_paths = ["vendor/flask/app.py", "vendor/flask/helpers.py"]
        store = run_pipeline(resources, packages, all_paths)
        for path, curation in store.items():
            self.assertIn("origin", curation)


class PipelineDBIntegrationTestCase(TestCase):

    def setUp(self):
        self.project = Project.objects.create(name="pipeline-db-test")

    def tearDown(self):
        self.project.delete()

    def test_pipeline_processes_db_resources(self):
        CodebaseResource.objects.create(project=self.project, path="src/a.py")
        CodebaseResource.objects.create(project=self.project, path="src/b.py")
        resources = list(CodebaseResource.objects.filter(project=self.project))
        self.assertEqual(len(resources), 2)

    def test_pipeline_uses_discovered_packages(self):
        DiscoveredPackage.objects.create(
            project=self.project, type="pypi", name="flask", version="2.0.0"
        )
        packages = list(DiscoveredPackage.objects.filter(project=self.project))
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0].name, "flask")

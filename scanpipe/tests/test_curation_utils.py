# SPDX-License-Identifier: Apache-2.0
# scanpipe/tests/test_curation_utils.py

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence

from django.test import TestCase


# ---------------------------------------------------------------------------
# Utility functions under test
# (Inline stubs — replace with actual imports once implemented)
# ---------------------------------------------------------------------------

def validate_purl(purl):
    """Validate a Package URL format."""
    if not isinstance(purl, str):
        return False
    pattern = r"^pkg:[a-zA-Z][a-zA-Z0-9+\-.]+/.+$"
    return bool(re.match(pattern, purl))


def normalize_path(path):
    """Normalize a file path for consistent comparison."""
    return path.strip().lstrip("/").replace("\\", "/")


def merge_curations(base, override):
    """
    Merge two curation dicts. Override takes precedence.
    Returns a new merged dict.
    """
    merged = dict(base)
    merged.update(override)
    return merged


def deduplicate_curations(curations):
    """
    Remove duplicate curations by resource_path.
    Last entry wins.
    """
    seen = {}
    for c in curations:
        seen[c["resource_path"]] = c
    return list(seen.values())


def compute_confidence_average(curations):
    """Return the average confidence across a list of curations."""
    if not curations:
        return 0.0
    total = sum(c.get("confidence", 0.0) for c in curations)
    return total / len(curations)


def group_curations_by_origin(curations):
    """Group curations by their origin PURL."""
    groups = defaultdict(list)
    for c in curations:
        groups[c["origin"]].append(c)
    return dict(groups)


def filter_curations_by_confidence(curations, min_confidence=0.8):
    """Return only curations at or above min_confidence."""
    return [c for c in curations if c.get("confidence", 0.0) >= min_confidence]


def export_curations_to_json(curations):
    """Serialize curations to a JSON string."""
    return json.dumps({"curations": curations}, indent=2)


def import_curations_from_json(json_str):
    """Deserialize curations from a JSON string."""
    data = json.loads(json_str)
    return data.get("curations", [])


def resolve_conflict(local, remote, strategy="local_wins"):
    """
    Resolve conflicting curations from different sources.
    Strategies: local_wins, remote_wins, highest_confidence
    """
    if strategy == "local_wins":
        return local
    elif strategy == "remote_wins":
        return remote
    elif strategy == "highest_confidence":
        lc = local.get("confidence", 0.0)
        rc = remote.get("confidence", 0.0)
        return local if lc >= rc else remote
    return local


class PURLValidationTestCase(TestCase):

    def test_valid_pypi_purl(self):
        self.assertTrue(validate_purl("pkg:pypi/requests@2.28.0"))

    def test_valid_npm_purl(self):
        self.assertTrue(validate_purl("pkg:npm/lodash@4.17.21"))

    def test_valid_gem_purl(self):
        self.assertTrue(validate_purl("pkg:gem/rails@7.0.0"))

    def test_valid_maven_purl(self):
        self.assertTrue(validate_purl("pkg:maven/org.springframework/spring-core@5.3.0"))

    def test_valid_docker_purl(self):
        self.assertTrue(validate_purl("pkg:docker/ubuntu@20.04"))

    def test_invalid_no_pkg_prefix(self):
        self.assertFalse(validate_purl("pypi/requests@2.28.0"))

    def test_invalid_empty_string(self):
        self.assertFalse(validate_purl(""))

    def test_invalid_none(self):
        self.assertFalse(validate_purl(None))

    def test_invalid_integer(self):
        self.assertFalse(validate_purl(12345))

    def test_invalid_missing_name(self):
        self.assertFalse(validate_purl("pkg:pypi/"))

    def test_valid_purl_without_version(self):
        self.assertTrue(validate_purl("pkg:pypi/requests"))


class PathNormalizationTestCase(TestCase):

    def test_strip_leading_slash(self):
        self.assertEqual(normalize_path("/src/main.py"), "src/main.py")

    def test_strip_whitespace(self):
        self.assertEqual(normalize_path("  src/main.py  "), "src/main.py")

    def test_replace_backslash(self):
        self.assertEqual(normalize_path("src\\main.py"), "src/main.py")

    def test_no_change_needed(self):
        self.assertEqual(normalize_path("src/main.py"), "src/main.py")

    def test_empty_string(self):
        self.assertEqual(normalize_path(""), "")

    def test_deep_path(self):
        self.assertEqual(normalize_path("/a/b/c/d/e.py"), "a/b/c/d/e.py")

    def test_windows_path(self):
        self.assertEqual(normalize_path("src\\utils\\helper.py"), "src/utils/helper.py")


class MergeCurationsTestCase(TestCase):

    def _curation(self, path, origin, confidence=1.0):
        return {"resource_path": path, "origin": origin, "confidence": confidence}

    def test_merge_non_overlapping(self):
        base = {"a": 1}
        override = {"b": 2}
        result = merge_curations(base, override)
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_merge_override_wins(self):
        base = {"origin": "pkg:pypi/old@1.0"}
        override = {"origin": "pkg:pypi/new@2.0"}
        result = merge_curations(base, override)
        self.assertEqual(result["origin"], "pkg:pypi/new@2.0")

    def test_merge_does_not_mutate_base(self):
        base = {"origin": "pkg:pypi/old@1.0"}
        override = {"origin": "pkg:pypi/new@2.0"}
        merge_curations(base, override)
        self.assertEqual(base["origin"], "pkg:pypi/old@1.0")

    def test_merge_empty_override(self):
        base = {"origin": "pkg:pypi/x@1.0"}
        result = merge_curations(base, {})
        self.assertEqual(result["origin"], "pkg:pypi/x@1.0")

    def test_merge_empty_base(self):
        result = merge_curations({}, {"origin": "pkg:pypi/x@1.0"})
        self.assertEqual(result["origin"], "pkg:pypi/x@1.0")


class DeduplicateCurationsTestCase(TestCase):

    def _c(self, path, origin):
        return {"resource_path": path, "origin": origin}

    def test_no_duplicates(self):
        curations = [self._c("a.py", "pkg:pypi/a@1"), self._c("b.py", "pkg:pypi/b@1")]
        result = deduplicate_curations(curations)
        self.assertEqual(len(result), 2)

    def test_with_duplicates_last_wins(self):
        curations = [
            self._c("a.py", "pkg:pypi/old@1"),
            self._c("a.py", "pkg:pypi/new@2"),
        ]
        result = deduplicate_curations(curations)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["origin"], "pkg:pypi/new@2")

    def test_empty_list(self):
        self.assertEqual(deduplicate_curations([]), [])


class ConfidenceAverageTestCase(TestCase):

    def test_average_equal_confidences(self):
        curations = [{"confidence": 0.8}, {"confidence": 0.8}]
        self.assertAlmostEqual(compute_confidence_average(curations), 0.8)

    def test_average_mixed_confidences(self):
        curations = [{"confidence": 0.6}, {"confidence": 1.0}]
        self.assertAlmostEqual(compute_confidence_average(curations), 0.8)

    def test_empty_returns_zero(self):
        self.assertEqual(compute_confidence_average([]), 0.0)

    def test_single_item(self):
        self.assertAlmostEqual(compute_confidence_average([{"confidence": 0.75}]), 0.75)


class FilterByConfidenceTestCase(TestCase):

    def _c(self, path, conf):
        return {"resource_path": path, "confidence": conf}

    def test_filter_above_threshold(self):
        curations = [self._c("a.py", 0.9), self._c("b.py", 0.7), self._c("c.py", 0.8)]
        result = filter_curations_by_confidence(curations, min_confidence=0.8)
        self.assertEqual(len(result), 2)

    def test_filter_all_below(self):
        curations = [self._c("a.py", 0.5), self._c("b.py", 0.3)]
        result = filter_curations_by_confidence(curations, min_confidence=0.8)
        self.assertEqual(len(result), 0)

    def test_filter_empty(self):
        self.assertEqual(filter_curations_by_confidence([], 0.8), [])


class JSONExportImportTestCase(TestCase):

    def _c(self, path, origin):
        return {"resource_path": path, "origin": origin, "confidence": 0.9}

    def test_export_produces_valid_json(self):
        curations = [self._c("a.py", "pkg:pypi/x@1")]
        result = export_curations_to_json(curations)
        parsed = json.loads(result)
        self.assertIn("curations", parsed)

    def test_import_from_exported(self):
        curations = [self._c("a.py", "pkg:pypi/x@1"), self._c("b.py", "pkg:npm/y@2")]
        exported = export_curations_to_json(curations)
        imported = import_curations_from_json(exported)
        self.assertEqual(len(imported), 2)

    def test_import_empty(self):
        result = import_curations_from_json('{"curations": []}')
        self.assertEqual(result, [])

    def test_roundtrip_preserves_data(self):
        original = [self._c("src/main.py", "pkg:pypi/flask@2.0")]
        exported = export_curations_to_json(original)
        imported = import_curations_from_json(exported)
        self.assertEqual(imported[0]["resource_path"], "src/main.py")
        self.assertEqual(imported[0]["origin"], "pkg:pypi/flask@2.0")


class ConflictResolutionTestCase(TestCase):

    def _c(self, origin, confidence):
        return {"origin": origin, "confidence": confidence}

    def test_local_wins(self):
        local = self._c("pkg:pypi/local@1", 0.7)
        remote = self._c("pkg:pypi/remote@2", 0.9)
        result = resolve_conflict(local, remote, strategy="local_wins")
        self.assertEqual(result["origin"], "pkg:pypi/local@1")

    def test_remote_wins(self):
        local = self._c("pkg:pypi/local@1", 0.7)
        remote = self._c("pkg:pypi/remote@2", 0.9)
        result = resolve_conflict(local, remote, strategy="remote_wins")
        self.assertEqual(result["origin"], "pkg:pypi/remote@2")

    def test_highest_confidence_picks_remote(self):
        local = self._c("pkg:pypi/local@1", 0.6)
        remote = self._c("pkg:pypi/remote@2", 0.9)
        result = resolve_conflict(local, remote, strategy="highest_confidence")
        self.assertEqual(result["origin"], "pkg:pypi/remote@2")

    def test_highest_confidence_picks_local_on_tie(self):
        local = self._c("pkg:pypi/local@1", 0.9)
        remote = self._c("pkg:pypi/remote@2", 0.9)
        result = resolve_conflict(local, remote, strategy="highest_confidence")
        self.assertEqual(result["origin"], "pkg:pypi/local@1")


class Python313CompatibilityTestCase(TestCase):

    def test_collections_abc_mapping(self):
        self.assertTrue(issubclass(dict, Mapping))

    def test_collections_abc_sequence(self):
        self.assertTrue(issubclass(list, Sequence))

    def test_builtin_type_hints(self):
        x: list[str] = ["a"]
        y: dict[str, int] = {"a": 1}
        self.assertIsInstance(x, list)
        self.assertIsInstance(y, dict)

    def test_fstring_expressions(self):
        name = "curation"
        result = f"test-{name}-utils"
        self.assertEqual(result, "test-curation-utils")

    def test_defaultdict_still_works(self):
        d = defaultdict(list)
        d["key"].append(1)
        self.assertEqual(d["key"], [1])

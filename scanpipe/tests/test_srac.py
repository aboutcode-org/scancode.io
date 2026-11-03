import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from scanpipe.pipelines.load_srac import correlate_sidecar


class SRACCorrelationTest(SimpleTestCase):
    def make_sidecar(self, document):
        handle = tempfile.NamedTemporaryFile(suffix=".srac.json", delete=False)
        path = Path(handle.name)
        handle.close()
        path.write_text(json.dumps(document))
        return SimpleNamespace(name=path.name, location=str(path))

    def make_package(self, purl, uuid="package-1", sha256=""):
        return SimpleNamespace(
            uuid=uuid,
            package_uid=purl,
            sha256=sha256,
            extra_data={},
            get_package_url=lambda: purl,
        )

    def test_matches_by_purl_and_preserves_assertion(self):
        package = self.make_package("pkg:pypi/demo@1.0")
        assertion = {
            "id": "a-1",
            "subject": {"purl": "pkg:pypi/demo@1.0"},
            "review": "pending",
        }
        report = correlate_sidecar(
            [self.make_sidecar({"assertions": [assertion]})], [package]
        )
        self.assertEqual("valid", report["status"])
        self.assertEqual("purl", report["matched"][0]["identifier"])
        self.assertEqual(assertion, report["assertions"][0])

    def test_unmatched_and_ambiguous_are_explicit(self):
        document = {
            "assertions": [
                {"id": "missing", "subject": {"purl": "pkg:pypi/missing@1"}},
                {"id": "ambiguous", "subject": {"sha256": "a"}},
            ]
        }
        packages = [
            self.make_package("pkg:pypi/a@1", "one", "a"),
            self.make_package("pkg:pypi/b@1", "two", "a"),
        ]
        report = correlate_sidecar([self.make_sidecar(document)], packages)
        self.assertEqual(["missing"], [item["id"] for item in report["unmatched"]])
        self.assertEqual(["ambiguous"], [item["id"] for item in report["ambiguous"]])
        self.assertEqual("incomplete", report["status"])

    def test_malformed_and_bad_integrity_fail_closed(self):
        sidecar = self.make_sidecar({"assertions": []})
        Path(sidecar.location).write_text("{")
        report = correlate_sidecar([sidecar], [])
        self.assertEqual("invalid", report["status"])

        document = {"assertions": [], "integrity": {"algorithm": "sha256", "value": "bad"}}
        report = correlate_sidecar([self.make_sidecar(document)], [])
        self.assertEqual("invalid", report["status"])
        self.assertIn("integrity check failed", report["invalid"][0]["reason"])

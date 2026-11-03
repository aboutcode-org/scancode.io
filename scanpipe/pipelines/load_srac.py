# SPDX-License-Identifier: Apache-2.0
"""Load and correlate an SRAC JSON sidecar with packages from an SBOM."""

import hashlib
import json
from pathlib import Path

from scanpipe.pipelines.load_sbom import LoadSBOM


class LoadSRAC(LoadSBOM):
    """Import an SBOM and correlate an optional SRAC safety assertion sidecar.

    This pipeline only records externally authored assertions. It does not infer,
    create, or modify a package safety classification or approval.
    """

    @classmethod
    def steps(cls):
        return super().steps() + (cls.correlate_srac,)

    def correlate_srac(self):
        sidecars = [
            resource
            for resource in self.project.codebaseresources.files()
            if resource.name.lower().endswith((".srac.json", ".srac"))
        ]
        report = correlate_sidecar(sidecars, self.project.discoveredpackages.all())
        self.project.update_extra_data({"srac_correlation": report})
        output = self.project.get_output_file_path("srac-correlation", "json")
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        self.log(f"SRAC correlation report written to {output}")


def _digest_matches(document, raw_bytes):
    integrity = document.get("integrity") or document.get("digest")
    if not integrity:
        return True, "missing"
    if isinstance(integrity, str):
        algorithm, _, expected = integrity.partition(":")
    else:
        algorithm = integrity.get("algorithm", "sha256")
        expected = integrity.get("value") or integrity.get("digest", "")
    algorithm = str(algorithm).lower().replace("-", "")
    if algorithm not in hashlib.algorithms_available or not expected:
        return False, "invalid"
    expected = str(expected).lower()
    actual = hashlib.new(algorithm, raw_bytes).hexdigest()
    if actual.lower() == expected:
        return True, actual
    # Also support the usual detached-integrity representation: the digest is
    # computed over canonical JSON with the integrity field removed.
    payload = dict(document)
    payload.pop("integrity", None)
    payload.pop("digest", None)
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    canonical_digest = hashlib.new(algorithm, canonical).hexdigest()
    return canonical_digest.lower() == expected, canonical_digest


def _assertion_subject(assertion):
    subject = assertion.get("subject", assertion.get("component", {}))
    return subject if isinstance(subject, dict) else {}


def _package_identifiers(package):
    identifiers = {"purl": str(package.get_package_url())}
    if package.package_uid:
        identifiers["package_uid"] = package.package_uid
    if package.sha256:
        identifiers["sha256"] = package.sha256.lower()
    identifiers["sbom_ref"] = str(package.extra_data.get("bom_ref", "")).lower()
    return identifiers


def _matches(assertion, packages):
    subject = _assertion_subject(assertion)
    requested = {
        key: str(value).lower()
        for key, value in {
            "purl": subject.get("purl") or subject.get("package_url"),
            "package_uid": subject.get("package_uid"),
            "sbom_ref": subject.get("sbom_ref") or subject.get("bom_ref"),
            "sha256": subject.get("sha256")
            or (subject.get("digest") or {}).get("value"),
        }.items()
        if value
    }
    if not requested:
        return [], "invalid"

    matches = []
    for package in packages:
        identifiers = _package_identifiers(package)
        if any(
            identifiers.get(key, "").lower() == value
            for key, value in requested.items()
        ):
            matched_keys = [
                key
                for key in ("purl", "package_uid", "sbom_ref", "sha256")
                if identifiers.get(key, "").lower() == requested.get(key)
            ]
            matches.append((package, matched_keys[0]))
    unique = {package.uuid: (package, identifier) for package, identifier in matches}
    return list(unique.values()), "matched"


def correlate_sidecar(sidecars, packages):
    """Return a deterministic, fail-closed SRAC correlation report."""
    report = {
        "format": "srac-correlation-1",
        "status": "valid",
        "sidecar": None,
        "assertions": [],
        "matched": [],
        "unmatched": [],
        "ambiguous": [],
        "invalid": [],
        "stale": [],
    }
    if len(sidecars) != 1:
        report["status"] = "invalid"
        report["invalid"].append(
            {
                "reason": "expected exactly one clearly identified SRAC sidecar",
                "count": len(sidecars),
            }
        )
        return report

    resource = sidecars[0]
    path = Path(resource.location)
    report["sidecar"] = {
        "name": resource.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        report["status"] = "invalid"
        report["invalid"].append({"reason": "malformed JSON", "detail": str(error)})
        return report

    if not isinstance(document, dict) or not isinstance(document.get("assertions"), list):
        report["status"] = "invalid"
        report["invalid"].append({"reason": "SRAC requires an assertions array"})
        report["assertions"] = document if isinstance(document, dict) else {}
        return report

    integrity_ok, actual_digest = _digest_matches(document, raw)
    report["sidecar"]["declared_digest"] = document.get("integrity") or document.get("digest")
    if not integrity_ok:
        report["status"] = "invalid"
        report["invalid"].append({"reason": "integrity check failed", "actual_sha256": actual_digest})

    report["assertions"] = document["assertions"]
    for index, assertion in enumerate(document["assertions"]):
        assertion_id = (
            assertion.get("id", f"assertion-{index + 1}")
            if isinstance(assertion, dict)
            else f"assertion-{index + 1}"
        )
        item = {"id": assertion_id, "index": index}
        if not isinstance(assertion, dict):
            report["invalid"].append({**item, "reason": "assertion must be an object"})
            report["status"] = "invalid"
            continue
        if assertion.get("stale") is True or assertion.get("status") == "stale":
            report["stale"].append({**item, "reason": "assertion marked stale"})
            continue
        matches, reason = _matches(assertion, packages)
        if reason == "invalid":
            report["invalid"].append({**item, "reason": "assertion has no supported stable identifier"})
        elif len(matches) == 1:
            package, identifier = matches[0]
            report["matched"].append(
                {
                    **item,
                    "package_uuid": str(package.uuid),
                    "identifier": identifier,
                }
            )
        elif len(matches) > 1:
            report["ambiguous"].append(
                {
                    **item,
                    "package_uuids": sorted(
                        str(package.uuid) for package, _ in matches
                    ),
                }
            )
        else:
            report["unmatched"].append(item)

    if report["invalid"] or report["ambiguous"] or report["unmatched"] or report["stale"]:
        report["status"] = "invalid" if report["invalid"] else "incomplete"
    return report

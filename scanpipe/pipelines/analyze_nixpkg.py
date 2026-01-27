# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.

"""
NixpkgClarity: Analyze a single Nix package (nixpkg).

Goals:
- Be aware of common nixpkgs conventions and community practices for license and origin metadata
- Normalize declared license fields (including lists and license set references)
- Determine source origins (homepage, vcs URL) and fetch sources when provided
- Perform a standard ScanCode scan and emit a summary for clarity

Inputs (recommended):
- A nixpkg meta JSON file named "nixpkg_meta.json" placed in project inputs directory
  Example keys: {"name", "version", "homepage", "license", "src"}
  - "license" may be a string, a list of strings, or objects; we normalize
  - "src" may be a URL (archive) or VCS URL (e.g., GitHub)
- Optionally, source archives or pre-fetched directories can be provided as inputs

Outputs:
- Project output JSON file "nixpkg_clarity_summary.json" summarizing origin and license
- Standard ScanCode results available through the UI
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes.input import copy_inputs

try:
    # fetchcode is optional but available in this project dependencies
    from fetchcode import fetch
except Exception:  # pragma: no cover - keep pipeline usable without fetchcode
    fetch = None


def _normalize_license(value: Any) -> List[str]:
    """Return a list of normalized license identifiers/labels from nixpkgs meta.

    Nixpkgs conventions:
    - license can be a single license OR a list
    - license entries can be strings (e.g., "mit"), SPDX ids ("MIT"),
      or objects referring to nixpkgs license sets (e.g., {"spdxId": "MIT", "shortName": "mit"})
    - some entries may be placeholders like "unfree"; keep them verbatim
    """
    def to_label(item: Any) -> Optional[str]:
        if item is None:
            return None
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            # Prefer SPDX id if present, fallback to shortName or fullName
            return (
                item.get("spdxId")
                or item.get("spdx")
                or item.get("shortName")
                or item.get("fullName")
                or item.get("name")
            )
        return str(item)

    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        labels = [to_label(v) for v in value]
    else:
        labels = [to_label(value)]
    return sorted({l for l in labels if l})


def _read_nixpkg_meta(inputs_dir: Path) -> Dict[str, Any]:
    """Load nixpkg_meta.json if present in inputs, else return empty dict."""
    meta_path = inputs_dir / "nixpkg_meta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


class NixpkgClarity(Pipeline):
    """Pipeline to analyze a single nixpkg with origin and license clarity."""

    results_url = "/project/{slug}/packages/?compliance_alert=warning"

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.fetch_sources_if_any,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.scan_for_files,
            cls.collect_and_create_license_detections,
            cls.emit_nixpkg_clarity_summary,
        )

    def copy_inputs_to_codebase_directory(self):
        copy_inputs(self.project.inputs("*"), self.project.codebase_path)

    def fetch_sources_if_any(self):
        """If nixpkg meta provides a 'src' URL and fetchcode is available, fetch it."""
        inputs_dir = self.project.input_path
        meta = _read_nixpkg_meta(inputs_dir)
        src = meta.get("src") or meta.get("source")
        if not src or fetch is None:
            return
        try:
            self.log(f"Fetching sources from: {src}")
            dest_dir = self.project.codebase_path / "nixpkg-src"
            dest_dir.mkdir(parents=True, exist_ok=True)
            # fetchcode will place archives or VCS clones under dest_dir
            fetch(src, dest_dir=str(dest_dir))
        except Exception as e:
            self.add_error(e)

    def collect_and_create_codebase_resources(self):
        pipes.collect_and_create_codebase_resources(self.project)

    def scan_for_application_packages(self):
        pipes.scancode.scan_for_application_packages(self.project, progress_logger=self.log)

    def scan_for_files(self):
        pipes.scancode.scan_for_files(self.project, progress_logger=self.log)

    def collect_and_create_license_detections(self):
        pipes.scancode.collect_and_create_license_detections(project=self.project)

    def emit_nixpkg_clarity_summary(self):
        """Emit a JSON summary derived from nixpkg meta and scan results."""
        inputs_dir = self.project.input_path
        meta = _read_nixpkg_meta(inputs_dir)

        name = meta.get("name") or meta.get("pname") or ""
        version = meta.get("version") or meta.get("rev") or ""
        homepage = meta.get("homepage") or meta.get("url") or ""
        src = meta.get("src") or meta.get("source") or ""
        licenses = _normalize_license(meta.get("license"))

        # Derive best-effort origin URL from common conventions
        origin_urls: List[str] = []
        for key in ("homepage", "url", "repository", "src", "source"):
            val = meta.get(key)
            if isinstance(val, str) and val:
                origin_urls.append(val)
        origin_urls = [u for u in origin_urls if u]

        # Compose summary
        summary: Dict[str, Any] = {
            "nixpkg": {
                "name": name,
                "version": version,
            },
            "origin": {
                "homepage": homepage,
                "source": src,
                "candidates": origin_urls,
            },
            "license": {
                "declared": licenses,
            },
        }

        # Optionally include a quick package overview
        try:
            from scanpipe.models import DiscoveredPackage

            pkgs = (
                DiscoveredPackage.objects.project(self.project)
                .order_by("type", "namespace", "name", "version")
            )
            summary["packages"] = [
                {
                    "purl": p.package_url,
                    "name": p.name,
                    "version": p.version,
                    "declared_spdx": p.get_declared_license_expression_spdx(),
                }
                for p in pkgs
            ]
        except Exception:
            # best effort; keep summary minimal if models are not ready
            pass

        output_file = self.project.get_output_file_path("nixpkg_clarity_summary", "json")
        try:
            output_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            self.log(f"Nixpkg clarity summary written to: {output_file}")
        except Exception as e:
            self.add_error(e)

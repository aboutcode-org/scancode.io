# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.

from collections import defaultdict
from pathlib import Path
import csv

from licensedcode.cache import get_licensing

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes.input import copy_inputs
class NixpkgsLicenseAudit(Pipeline):
    """
    Scan the codebase, collect license detections, and audit package-level
    declared vs detected licenses, with a focus on nixpkgs metadata correctness.

    What it does:
    - Copies inputs, extracts archives, and scans for packages/files
    - Aggregates detected SPDX license keys across resources per package
    - Compares with each package's declared SPDX license expression
    - Flags mismatches and emits a CSV report in the project output directory

    Notes:
    - If you have nixpkgs-specific metadata (e.g., expected licenses), place a
      mapping file in the project input directory named
      "nixpkgs_licenses.json" mapping a package PURL to an expected SPDX
      expression. This audit uses the package declared expression by default,
      and will use the mapping file when available to override.
    - MatchCode-based code matching can be run separately to enrich packages
      before auditing if configured, using the MatchToMatchCode pipeline.
    """

    results_url = "/project/{slug}/packages/?compliance_alert=warning"

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.scan_for_files,
            cls.collect_and_create_license_detections,
            cls.audit_nixpkgs_licenses,
        )

    def copy_inputs_to_codebase_directory(self):
        copy_inputs(self.project.inputs("*"), self.project.codebase_path)

    def collect_and_create_codebase_resources(self):
        pipes.collect_and_create_codebase_resources(self.project)

    def scan_for_application_packages(self):
        pipes.scancode.scan_for_application_packages(self.project, progress_logger=self.log)

    def scan_for_files(self):
        pipes.scancode.scan_for_files(self.project, progress_logger=self.log)

    def collect_and_create_license_detections(self):
        pipes.scancode.collect_and_create_license_detections(project=self.project)

    def _load_expected_map(self):
        """Optionally load a PURL->SPDX expression mapping from inputs."""
        import json

        expected = {}
        for input_src in self.project.inputsources.all():
            if input_src.filename == "nixpkgs_licenses.json" and input_src.exists():
                try:
                    data = json.loads(input_src.path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        expected.update({str(k): str(v) for k, v in data.items()})
                        self.log("Loaded nixpkgs_licenses.json overrides")
                except Exception as e:
                    self.add_error(e)
        return expected

    def _symbols_from_expression(self, expression_spdx):
        """Return a set of SPDX license keys parsed from an SPDX expression."""
        if not expression_spdx:
            return set()
        licensing = get_licensing()
        try:
            return {sym.key for sym in licensing.license_symbols(expression_spdx)}
        except Exception:
            return set()

    def audit_nixpkgs_licenses(self):
        """Compare declared vs detected licenses per package and export CSV."""
        from scanpipe.models import DiscoveredPackage, CodebaseResource

        # Optional override map for expected SPDX expressions by PURL
        expected_map = self._load_expected_map()

        # Build detected SPDX keys per package by aggregating resource detections
        detected_per_pkg = defaultdict(set)

        # Prefetch to reduce queries
        packages = (
            DiscoveredPackage.objects.project(self.project)
            .prefetch_related("codebase_resources")
            .order_by("type", "namespace", "name", "version")
        )

        # Aggregate detected licenses per package
        licensing = get_licensing()
        for pkg in packages.iterator(chunk_size=2000):
            for res in pkg.codebase_resources.all():
                expr = getattr(res, "detected_license_expression_spdx", "")
                if not expr:
                    continue
                try:
                    for sym in licensing.license_symbols(expr):
                        detected_per_pkg[pkg.uuid].add(sym.key)
                except Exception:
                    continue

        # Prepare CSV output
        output_file = self.project.get_output_file_path(
            "nixpkgs_license_audit", "csv"
        )

        fieldnames = [
            "purl",
            "name",
            "version",
            "declared_spdx",
            "expected_spdx",
            "detected_spdx_keys",
            "files_with_detections",
            "comparison",
        ]

        with output_file.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()

            for pkg in packages.iterator(chunk_size=2000):
                declared_spdx = pkg.get_declared_license_expression_spdx()
                expected_spdx = expected_map.get(pkg.package_url, "")
                basis_spdx = expected_spdx or declared_spdx

                basis_set = self._symbols_from_expression(basis_spdx)
                detected_set = detected_per_pkg.get(pkg.uuid, set())

                # Derive comparison classification
                if not basis_set and not detected_set:
                    comparison = "no-declared-and-no-detected"
                elif basis_set and not detected_set:
                    comparison = "no-detected"
                elif detected_set and not basis_set:
                    comparison = "no-declared"
                elif basis_set == detected_set:
                    comparison = "match"
                elif basis_set.issubset(detected_set):
                    comparison = "declared-subset-of-detected"
                elif detected_set.issubset(basis_set):
                    comparison = "detected-subset-of-declared"
                else:
                    comparison = "different"

                # Count files with detections for this package
                files_with_detections = 0
                for res in pkg.codebase_resources.all():
                    if getattr(res, "detected_license_expression_spdx", ""):
                        files_with_detections += 1

                writer.writerow(
                    {
                        "purl": pkg.package_url,
                        "name": pkg.name,
                        "version": pkg.version,
                        "declared_spdx": declared_spdx,
                        "expected_spdx": expected_spdx,
                        "detected_spdx_keys": " ".join(sorted(detected_set)),
                        "files_with_detections": files_with_detections,
                        "comparison": comparison,
                    }
                )

        self.log(f"Nixpkgs license audit written to: {output_file}")

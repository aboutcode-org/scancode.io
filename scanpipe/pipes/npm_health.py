# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

"""Utilities for the npm-health ScanCode.io pipeline."""

import json
import shlex
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.parse import urlunparse

import requests
from packageurl import PackageURL


NPM_HEALTH_EXTRA_DATA_KEY = "npm_health"
DEFAULT_CACHE_MAX_AGE_DAYS = 90
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_COMMAND_TIMEOUT = 900

DEFAULT_METRIC_WEIGHTS = {
    "activity": 1.0,
    "community": 1.0,
    "maintenance": 1.0,
    "documentation": 0.75,
    "security": 1.0,
    "metadata_completeness": 0.5,
    "maintainer_presence": 0.5,
    "dependency_simplicity": 0.25,
}


class NpmHealthError(Exception):
    """Base npm-health error."""


class NpmHealthPayloadError(NpmHealthError):
    """Invalid PURL, registry data, or metrics payload."""


class NpmHealthCommandError(NpmHealthError):
    """External metrics collector failure."""



def parse_package_url(value):
    """Return a PackageURL parsed from ``value``."""
    if not value or not isinstance(value, str):
        raise NpmHealthPayloadError("A project PURL is required.")
    try:
        return PackageURL.from_string(value)
    except ValueError as error:
        raise NpmHealthPayloadError(f"Invalid package URL: {value}") from error



def validate_npm_package_url(value):
    """Return a versioned npm PackageURL or raise a descriptive error."""
    package = parse_package_url(value)
    if package.type != "npm":
        raise NpmHealthPayloadError(
            f"npm-health requires an npm PURL, not {package.type!r}."
        )
    if not package.name:
        raise NpmHealthPayloadError("npm-health requires a package name.")
    if not package.version:
        raise NpmHealthPayloadError("npm-health requires a package version.")
    return package



def get_package_name(package):
    """Return the npm registry name for a PackageURL."""
    if not package.namespace:
        return package.name
    namespace = package.namespace
    if not namespace.startswith("@"):
        namespace = f"@{namespace}"
    return f"{namespace}/{package.name}"



def get_registry_metadata_url(package):
    """Return the npm registry URL for one exact package version."""
    name = quote(get_package_name(package), safe="@")
    version = quote(package.version, safe="")
    return f"https://registry.npmjs.org/{name}/{version}"



def normalize_repository_url(repository):
    """Return a normalized HTTP(S) repository URL."""
    if isinstance(repository, dict):
        repository = repository.get("url")
    if not repository or not isinstance(repository, str):
        return ""

    value = repository.strip()
    if value.startswith("git+"):
        value = value[4:]
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    if value.startswith("git://github.com/"):
        value = "https://github.com/" + value.removeprefix("git://github.com/")

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    path = parsed.path.removesuffix(".git").rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))



def get_repository_url(metadata):
    """Return a normalized repository URL from npm metadata."""
    return normalize_repository_url(metadata.get("repository"))



def get_tarball_url(metadata):
    """Return the npm distribution tarball URL."""
    dist = metadata.get("dist") or {}
    value = dist.get("tarball")
    return value if isinstance(value, str) else ""



def get_homepage_url(metadata):
    """Return the package homepage URL when available."""
    value = metadata.get("homepage")
    return value if isinstance(value, str) else ""



def get_license(metadata):
    """Return a compact license value from npm metadata."""
    value = metadata.get("license")
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("type"), str):
        return value["type"]
    return ""



def get_maintainer_count(metadata):
    """Return the number of maintainers declared by npm."""
    maintainers = metadata.get("maintainers") or []
    return len(maintainers) if isinstance(maintainers, list) else 0



def get_dependency_count(metadata):
    """Return the number of runtime dependencies in npm metadata."""
    dependencies = metadata.get("dependencies") or {}
    return len(dependencies) if isinstance(dependencies, dict) else 0



def fetch_registry_metadata(
    package,
    session=requests,
    timeout=DEFAULT_REQUEST_TIMEOUT,
):
    """Fetch and return npm registry metadata for ``package``."""
    response = session.get(get_registry_metadata_url(package), timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise NpmHealthPayloadError("The npm registry returned a non-object payload.")
    return data



def clamp(value, minimum=0.0, maximum=1.0):
    """Clamp a numeric value to an inclusive range."""
    return max(minimum, min(maximum, value))



def normalize_metric_value(value):
    """Normalize bool, 0..1, or percentage metric values to 0..1."""
    if isinstance(value, bool):
        return float(value)
    if not isinstance(value, int | float):
        raise NpmHealthPayloadError(f"Unsupported metric value: {value!r}")
    normalized = float(value)
    if normalized > 1.0:
        normalized /= 100.0
    return clamp(normalized)



def normalize_metrics(payload):
    """Return normalized metrics from a direct or nested collector payload."""
    if not isinstance(payload, dict):
        raise NpmHealthPayloadError("Metrics payload must be a JSON object.")
    values = payload.get("metrics", payload)
    if not isinstance(values, dict):
        raise NpmHealthPayloadError("Metrics must be a JSON object.")
    return {
        name: normalize_metric_value(value)
        for name, value in values.items()
        if isinstance(name, str)
    }



def collect_registry_metrics(metadata):
    """Return baseline health signals available from npm registry metadata."""
    completeness = sum(
        (
            bool(get_repository_url(metadata)),
            bool(get_homepage_url(metadata)),
            bool(get_license(metadata)),
        )
    ) / 3
    return {
        "metadata_completeness": completeness,
        "maintainer_presence": clamp(get_maintainer_count(metadata) / 3),
        "dependency_simplicity": 1.0 - clamp(get_dependency_count(metadata) / 50),
    }



def merge_metrics(*metric_sets):
    """Merge normalized metric mappings from left to right."""
    merged = {}
    for metrics in metric_sets:
        if metrics:
            merged.update(normalize_metrics(metrics))
    return merged



def normalize_weights(weights=None):
    """Return positive numeric scoring weights."""
    weights = weights or DEFAULT_METRIC_WEIGHTS
    return {
        name: float(value)
        for name, value in weights.items()
        if isinstance(name, str) and isinstance(value, int | float) and value > 0
    }



def compute_health_score(metrics, weights=None):
    """Return a weighted package health score from 0 to 100."""
    metrics = normalize_metrics(metrics)
    weights = normalize_weights(weights)
    weighted = [
        (value, weights[name])
        for name, value in metrics.items()
        if name in weights
    ]
    denominator = sum(weight for _, weight in weighted)
    if not denominator:
        return 0.0
    numerator = sum(value * weight for value, weight in weighted)
    return round((numerator / denominator) * 100, 2)



def classify_health_score(score):
    """Return a qualitative classification for a numeric health score."""
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "needs-attention"
    return "high-risk"



def parse_timestamp(value):
    """Return an aware UTC datetime parsed from an ISO timestamp."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)



def is_stale(snapshot, max_age_days=DEFAULT_CACHE_MAX_AGE_DAYS, now=None):
    """Return True when a cached npm-health snapshot is missing or too old."""
    if not isinstance(snapshot, dict):
        return True
    collected_at = parse_timestamp(snapshot.get("collected_at"))
    if not collected_at:
        return True
    now = now or datetime.now(UTC)
    return now - collected_at > timedelta(days=max_age_days)



def build_collection_targets(metadata):
    """Return source locations useful to external health collectors."""
    return {
        "repository_url": get_repository_url(metadata),
        "tarball_url": get_tarball_url(metadata),
        "homepage_url": get_homepage_url(metadata),
    }



def build_command_context(purl, metadata, output):
    """Return safe substitutions for an external collector command."""
    targets = build_collection_targets(metadata)
    return {
        "purl": purl,
        "repository_url": targets["repository_url"],
        "tarball_url": targets["tarball_url"],
        "output": str(output),
    }



def render_metrics_command(command_template, context):
    """Render a command template to an argument list without a shell."""
    if not command_template or not isinstance(command_template, str):
        raise NpmHealthCommandError("npm_health_metrics_command is not configured.")
    try:
        rendered = command_template.format_map(context)
    except KeyError as error:
        raise NpmHealthCommandError(
            f"Unknown npm-health command placeholder: {error.args[0]}"
        ) from error
    args = shlex.split(rendered)
    if not args:
        raise NpmHealthCommandError("The rendered metrics command is empty.")
    return args



def run_metrics_command(args, cwd=None, timeout=DEFAULT_COMMAND_TIMEOUT):
    """Run an external metrics collector and return its completed process."""
    completed = subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode:
        details = (completed.stderr or completed.stdout or "").strip()
        raise NpmHealthCommandError(
            f"External metrics collector failed ({completed.returncode}): {details}"
        )
    return completed



def load_metrics_json(location):
    """Load and normalize metrics from a JSON output file."""
    location = Path(location)
    if not location.is_file():
        raise NpmHealthCommandError(
            f"External metrics output was not created: {location}"
        )
    try:
        payload = json.loads(location.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        message = "External metrics output is invalid JSON."
        raise NpmHealthPayloadError(message) from error
    return normalize_metrics(payload)



def collect_external_metrics(
    command_template,
    purl,
    metadata,
    output,
    cwd=None,
):
    """Run a configured external collector and return normalized metrics."""
    context = build_command_context(purl, metadata, output)
    args = render_metrics_command(command_template, context)
    run_metrics_command(args=args, cwd=cwd)
    return load_metrics_json(output)



def build_snapshot(purl, metadata, metrics, score, collected_at=None):
    """Return the persisted npm-health result structure."""
    return {
        "purl": purl,
        "collected_at": collected_at or datetime.now(UTC).isoformat(),
        "score": score,
        "classification": classify_health_score(score),
        "metrics": normalize_metrics(metrics),
        "sources": build_collection_targets(metadata),
    }



def get_cached_snapshot(project):
    """Return the cached npm-health snapshot from project.extra_data."""
    data = project.extra_data or {}
    snapshot = data.get(NPM_HEALTH_EXTRA_DATA_KEY)
    return snapshot if isinstance(snapshot, dict) else None



def cache_snapshot(project, snapshot):
    """Persist one npm-health snapshot in Project.extra_data."""
    project.update_extra_data({NPM_HEALTH_EXTRA_DATA_KEY: snapshot})
    return snapshot



def write_snapshot(project, snapshot):
    """Write one npm-health JSON result into the project output directory."""
    output = project.get_output_file_path("npm-health", "json")
    output.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output

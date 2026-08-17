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

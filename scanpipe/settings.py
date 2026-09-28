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
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

"""
Runtime settings for the scanpipe app, resolved lazily on each access.

Resolution order for each setting:
  1. SCANPIPE = {"KEY": value} in the host Django settings: explicit override.
  2. SCANCODEIO_KEY environment variable: set via .env or the shell.
  3. DEFAULTS below: the built-in fallback.

Usage in scanpipe code:
  from scanpipe.settings import scanpipe_settings
  scanpipe_settings.WORKSPACE_LOCATION

To override in tests:
  from django.test import override_settings
  with override_settings(SCANPIPE={"WORKSPACE_LOCATION": "/tmp/test"}):
      ...

This module is intentionally separate from scancodeio/settings.py, which is
evaluated once at boot to build Django's own configuration (databases, middleware,
etc.). Settings here are resolved at call time, so they support override_settings
in tests and can be consumed by any host app that installs scanpipe as a library.
"""

import os

from django.conf import settings
from django.core.signals import setting_changed

ENV_PREFIX = "SCANCODEIO_"

DEFAULTS = {
    "ASYNC": False,
    "CONFIG_DIR": ".scancode",
    "CONFIG_FILE": "scancode-config.yml",
    "ENABLE_ADMIN_SITE": False,
    # Syntax in .env: SCANCODEIO_FETCH_BASIC_AUTH="host=user,password;"
    "FETCH_BASIC_AUTH": {},
    # Syntax in .env: SCANCODEIO_FETCH_DIGEST_AUTH="host=user,password;"
    "FETCH_DIGEST_AUTH": {},
    # Syntax in .env: SCANCODEIO_FETCH_HEADERS="host=Header1=value,Header2=value;"
    "FETCH_HEADERS": {},
    # This webhook will be added as WebhookSubscription for each new project.
    # Syntax in .env: SCANCODEIO_GLOBAL_WEBHOOK=target_url=https://webhook.url,
    # trigger_on_each_run=False,include_summary=True,include_results=False
    "GLOBAL_WEBHOOK": {},
    # Maximum file size, in bytes, served inline in the browser rather than
    # forced as an attachment download. Above this size, the browser tab
    # rendering the file (e.g. a large JSON) risks hanging.
    "INLINE_DOWNLOAD_MAX_SIZE": 10_000_000,
    # Default limit for "most common" entries in QuerySets.
    "MOST_COMMON_LIMIT": 7,
    # Syntax in .env: SCANCODEIO_NETRC_LOCATION="~/.netrc"
    "NETRC_LOCATION": "",
    # List views pagination, controls the number of items displayed per page.
    # Syntax in .env: SCANCODEIO_PAGINATE_BY=project=10,project_error=10
    "PAGINATE_BY": {
        "project": 20,
        "error": 50,
        "resource": 100,
        "package": 100,
        "dependency": 100,
        "license": 100,
        "relation": 100,
    },
    # This setting defines the additional locations ScanCode.io will search for
    # pipelines. This should be set to a list of strings containing full paths
    # to your additional pipelines directories.
    "PIPELINES_DIRS": [],
    "POLICIES_FILE": "policies.yml",
    # Set the number of parallel processes to use for ScanCode related scan execution.
    # If the SCANCODEIO_PROCESSES argument is not set, defaults to an optimal number of
    # CPUs available on the machine.
    "PROCESSES": None,
    # Default to 2 minutes.
    "SCAN_FILE_TIMEOUT": 120,
    # Default to None which scans all files
    "SCAN_MAX_FILE_SIZE": None,
    # The base URL (e.g., https://hostname/) of this application instance.
    # Required for generating URLs to reference objects within the app,
    # such as in webhook notifications.
    "SITE_URL": "",
    # Syntax in .env: SCANCODEIO_SKOPEO_AUTHFILE_LOCATION="/path/to/auth.json"
    "SKOPEO_AUTHFILE_LOCATION": "",
    # Syntax in .env: SCANCODEIO_SKOPEO_CREDENTIALS="host1=user:password,
    # host2=user:password"
    "SKOPEO_CREDENTIALS": {},
    # Maximum time allowed for a pipeline to complete.
    "TASK_TIMEOUT": "24h",
    "WORKSPACE_LOCATION": "var",
}

# Explicit types only for settings whose default is None (type cannot be inferred).
_TYPES = {
    "PROCESSES": int,
    "SCAN_MAX_FILE_SIZE": int,
}


def _parse_fetch_headers(env_value):
    """Parse FETCH_HEADERS format: host=Header1=val,Header2=val;host2=Header3=val."""
    result = {}
    for entry in env_value.split(";"):
        if not entry.strip():
            continue
        host, headers_string = entry.split("=", 1)
        result[host] = dict(
            pair.split("=", 1) for pair in headers_string.split(",") if "=" in pair
        )
    return result


# Custom parsers for settings whose env var format cannot be inferred from the type.
_CUSTOM_PARSERS = {
    "FETCH_HEADERS": _parse_fetch_headers,
}


def _cast(setting_name, env_value, default_value):
    """Cast an env var string to the type inferred from the default value."""
    if setting_name in _CUSTOM_PARSERS:
        return _CUSTOM_PARSERS[setting_name](env_value)
    cast_type = _TYPES.get(setting_name) or type(default_value)
    if cast_type is bool:
        return env_value.lower() in ("true", "1", "yes")
    if cast_type is int:
        return int(env_value)
    if cast_type is list:
        return [item.strip() for item in env_value.split(",") if item.strip()]
    if cast_type is dict:
        return dict(pair.split("=", 1) for pair in env_value.split(",") if "=" in pair)
    return env_value


class ScanpipeSettings:
    """Lazy settings object: resolves each value on access, never at import time."""

    @property
    def overrides(self):
        """Return the SCANPIPE dict from Django settings, cached until reload()."""
        if not hasattr(self, "_overrides"):
            self._overrides = getattr(settings, "SCANPIPE", {})
        return self._overrides

    def __getattr__(self, attr):
        """Resolve a setting: overrides -> env var -> DEFAULTS."""
        if attr not in DEFAULTS:
            raise AttributeError(f"Invalid scanpipe setting: {attr!r}")
        if attr in self.overrides:
            return self.overrides[attr]
        env_key = f"{ENV_PREFIX}{attr}"
        if env_key in os.environ:
            return _cast(attr, os.environ[env_key], DEFAULTS[attr])
        return DEFAULTS[attr]

    def reload(self):
        """Clear the overrides cache so the next access re-reads Django settings."""
        if hasattr(self, "_overrides"):
            delattr(self, "_overrides")


scanpipe_settings = ScanpipeSettings()


def _reload_scanpipe_settings(*, setting, **kwargs):
    if setting == "SCANPIPE":
        scanpipe_settings.reload()


setting_changed.connect(_reload_scanpipe_settings)

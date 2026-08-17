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

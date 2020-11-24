# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

import tempfile
from pathlib import Path

# Using exec() instead of "import *" to avoid any side effects
with Path(__file__).resolve().parent.joinpath("base.py").open() as parent_config:
    exec(parent_config.read())


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATES[0]["OPTIONS"]["debug"] = True

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "::1"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Run celery task in the current thread, no need to start workers in dev mode.
CELERY_TASK_ALWAYS_EAGER = True

# The following loggers will be output to the console, except if running the tests.
if IS_TESTS:
    LOGGING["loggers"]["scanner.tasks"]["handlers"] = None
    # Do not pollute the workspace during testing
    SCANCODEIO_WORKSPACE_LOCATION = tempfile.mkdtemp()
else:
    # No API Key needed in dev mode.
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (
        "rest_framework.permissions.AllowAny",
    )

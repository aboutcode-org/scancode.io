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

import os
import sys
from pathlib import Path

from django.conf import settings

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from scancodeio.celery import app as celery_app

__version__ = "1.0.6"

SCAN_NOTICE = Path(__file__).resolve().parent.joinpath("scan.NOTICE").read_text()


def get_workspace_location():
    """
    Return the workspace directory location
    from the `SCANCODEIO_WORKSPACE_LOCATION` settings/env.
    Default to a local `var/` directory if not set.
    """
    workspace_location = (
        getattr(settings, "SCANCODEIO_WORKSPACE_LOCATION", None)
        or os.environ.get("SCANCODEIO_WORKSPACE_LOCATION", None)
        or "var"
    )
    return str(Path(workspace_location).resolve().absolute())


WORKSPACE_LOCATION = get_workspace_location()


def command_line():
    """
    Command line entry point.
    """
    from django.core.management import execute_from_command_line

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scancodeio.settings")
    execute_from_command_line(sys.argv)

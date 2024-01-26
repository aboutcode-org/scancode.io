#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scancode_config import __version__ as scancode_toolkit_version

from scancodeio import __version__ as scancodeio_version
from scancodeio import settings


def versions(request):
    return {
        "SCANCODEIO_VERSION": scancodeio_version.lstrip("v"),
        "SCANCODE_TOOLKIT_VERSION": scancode_toolkit_version,
        "VULNERABLECODE_URL": settings.VULNERABLECODE_URL,
    }

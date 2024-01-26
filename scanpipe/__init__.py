#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#


def humanize_time(seconds):
    """Convert the provided ``seconds`` number into human-readable time."""
    message = f"{seconds:.0f} seconds"

    if seconds > 86400:
        message += f" ({seconds / 86400:.1f} days)"
    if seconds > 3600:
        message += f" ({seconds / 3600:.1f} hours)"
    elif seconds > 60:
        message += f" ({seconds / 60:.1f} minutes)"

    return message

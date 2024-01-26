#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.pipelines import Pipeline


class StepsAsAttribute(Pipeline):
    """Declare steps as attribute."""

    def step1(self):
        return

    steps = (step1,)

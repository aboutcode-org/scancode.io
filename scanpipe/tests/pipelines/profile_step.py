#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import profile


class ProfileStep(Pipeline):
    """Profile a step using the @profile decorator."""

    @classmethod
    def steps(cls):
        return (cls.step,)

    @profile
    def step(self):
        pass

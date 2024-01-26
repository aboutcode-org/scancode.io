#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.pipelines import Pipeline


class DoNothing(Pipeline):
    """
    Do nothing, in 2 steps.

    Description section of the doc string.
    """

    @classmethod
    def steps(cls):
        return (
            cls.step1,
            cls.step2,
        )

    def step1(self):
        """Step1 doc."""
        pass

    def step2(self):
        """Step2 doc."""
        pass

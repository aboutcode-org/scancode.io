#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.tests.pipelines.do_nothing import DoNothing


class RegisterFromFile(DoNothing):
    """Register from its file path."""

    @classmethod
    def steps(cls):
        return (cls.step1,)

    def step1(self):
        pass

#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.test import TestCase

from scancodeio import extract_short_commit


class ScanCodeIOTest(TestCase):
    def test_scancodeio_extract_short_commit(self):
        self.assertEqual(extract_short_commit(""), "")
        self.assertEqual(extract_short_commit("v32.6.0-44-ga8980bd"), "a8980bd")
        self.assertEqual(extract_short_commit("v1.0.0-1-g123456"), "123456")
        self.assertEqual(extract_short_commit("v2.0.0-5-abcdefg"), "abcdefg")
        self.assertEqual(extract_short_commit("v1.5.0-2-ghijkl"), "hijkl")

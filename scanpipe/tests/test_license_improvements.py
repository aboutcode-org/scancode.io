from django.test import TestCase
from scanpipe.pipes.scancode import normalize_spdx_identifier


class TestLicenseImprovements(TestCase):
    
    def test_normalize_gpl_2(self):
        result = normalize_spdx_identifier("GPL-2.0")
        self.assertEqual(result, "GPL-2.0-only")

    def test_normalize_gpl_3(self):
        result = normalize_spdx_identifier("GPL-3.0")
        self.assertEqual(result, "GPL-3.0-only")

    def test_normalize_lgpl_21(self):
        result = normalize_spdx_identifier("LGPL-2.1")
        self.assertEqual(result, "LGPL-2.1-only")

    def test_normalize_pass_through(self):
        result = normalize_spdx_identifier("MIT")
        self.assertEqual(result, "MIT")

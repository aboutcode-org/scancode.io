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

from django.test import TestCase

from scanpipe.pipes import utils

class ScanPipeUtilsTest(TestCase):

    def test_evaluate_license_mismatch_simple_OR_condition(self):
        package_lic = "mit OR apache-2.0"
        detected_lic_list = ["mit", "apache-2.0"]
        expected = {
            'missing': [],
            'extra': [],
            'is_match': True,
            'details': 'match'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected


    def test_evaluate_license_mismatch_simple_AND_condition(self):
        package_lic = "mit AND apache-2.0"
        detected_lic_list = ["mit", "apache-2.0"]
        expected = {
            'missing': [],
            'extra': [],
            'is_match': True,
            'details': 'match'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected


    def test_evaluate_license_mismatch_simple_OR_condition_1(self):
        package_lic = "mit OR apache-2.0"
        detected_lic_list = ["mit"]
        expected = {
            'missing': [],
            'extra': [],
            'is_match': True,
            'details': 'match'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_detected_lic_missing_AND_condition(self):
        package_lic = "mit AND apache-2.0"
        detected_lic_list = ["mit"]
        expected = {
            'missing': ["apache-2.0"],
            'extra': [],
            'is_match': False,
            'details': 'Missing: apache-2.0'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected


    def test_evaluate_license_mismatch_simple_AND_condition_detected_lic_has_OR(self):
        package_lic = "mit AND apache-2.0"
        detected_lic_list = ["mit or bsd-new", "apache-2.0"]
        expected = {
            'missing': [],
            'extra': [],
            'is_match': True,
            'details': 'match'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected


    def test_evaluate_license_mismatch_detected_lic_has_extra(self):
        package_lic = "mit AND apache-2.0"
        detected_lic_list = ["mit AND bsd-new", "apache-2.0"]
        expected = {
            'missing': [],
            'extra': ["bsd-new"],
            'is_match': False,
            'details': 'Extra: bsd-new'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_detected_lic_has_extra_1(self):
        package_lic = "mit AND apache-2.0"
        detected_lic_list = ["mit", "bsd-new", "apache-2.0"]
        expected = {
            'missing': [],
            'extra': ["bsd-new"],
            'is_match': False,
            'details': 'Extra: bsd-new'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_AND_condition_with_OR(self):
        package_lic = "(bsd-new OR apache-2.0) AND apache-2.0 AND mit"
        detected_lic_list = ["mit", "apache-2.0"]
        expected = {
            'missing': [],
            'extra': [],
            'is_match': True,
            'details': 'match'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_WITH_AND_OR_Missing(self):
        package_lic = "(bsd-new AND apache-2.0) AND apache-2.0 AND (mit OR public-domain)"
        detected_lic_list = ["mit", "apache-2.0"]
        expected = {
            'missing': ["bsd-new"],
            'extra': [],
            'is_match': False,
            'details': 'Missing: bsd-new'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_WITH_AND_OR(self):
        package_lic = "(bsd-new OR apache-2.0) AND apache-2.0 AND (mit OR public-domain)"
        detected_lic_list = ["mit", "apache-2.0"]
        expected = {
            'missing': [],
            'extra': [],
            'is_match': True,
            'details': 'match'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_missing_extra_AND(self):
        package_lic = "bsd-new AND apache-2.0"
        detected_lic_list = ["mit"]
        expected = {
            'missing': ['apache-2.0', 'bsd-new'],
            'extra': ['mit'],
            'is_match': False,
            'details': 'Missing: apache-2.0, bsd-new; Extra: mit'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_missing_extra_OR(self):
        package_lic = "bsd-new OR apache-2.0"
        detected_lic_list = ["mit"]
        expected = {
            'missing': ['apache-2.0', 'bsd-new'],
            'extra': ['mit'],
            'is_match': False,
            'details': 'Missing: apache-2.0, bsd-new; Extra: mit'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_some_missing_extra(self):
        package_lic = "(bsd-new OR apache-2.0) AND mit AND (apache-1.1 AND gpl-2.0)"
        detected_lic_list = ["mit", "lgpl-2.1"]
        expected = {
            'missing': ['apache-1.1', 'apache-2.0', 'bsd-new', 'gpl-2.0'],
            'extra': ['lgpl-2.1'],
            'is_match': False,
            'details': 'Missing: apache-1.1, apache-2.0, bsd-new, gpl-2.0; Extra: lgpl-2.1'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_WITH_WITH_Exception(self):
        package_lic = "bsd-new OR gpl-2.0 WITH classpath-exception-2.0"
        detected_lic_list = ["bsd-new"]
        expected = {
            'missing': [],
            'extra': [],
            'is_match': True,
            'details': 'match'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_WITH_WITH_Exception_missing(self):
        package_lic = "bsd-new AND gpl-2.0 WITH classpath-exception-2.0"
        detected_lic_list = ["bsd-new", "gpl-2.0"]
        expected = {
            'missing': ['classpath-exception-2.0'],
            'extra': [],
            'is_match': False,
            'details': 'Missing: classpath-exception-2.0'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

    def test_evaluate_license_mismatch_WITH_WITH_Exception_extra(self):
        package_lic = "bsd-new AND gpl-2.0"
        detected_lic_list = ["bsd-new", "gpl-2.0 WITH classpath-exception-2.0"]
        expected = {
            'missing': [],
            'extra': ['classpath-exception-2.0'],
            'is_match': False,
            'details': 'Extra: classpath-exception-2.0'
        }
        result = utils.evaluate_license_mismatch(package_lic, detected_lic_list)
        assert result == expected

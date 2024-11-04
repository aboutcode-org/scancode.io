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

from pathlib import Path

from django.apps import apps
from django.core.exceptions import ValidationError
from django.test import TestCase

from scanpipe.policies import load_policies_file
from scanpipe.policies import load_policies_yaml
from scanpipe.policies import make_license_policy_index
from scanpipe.policies import validate_policies
from scanpipe.tests import global_policies
from scanpipe.tests import license_policies_index

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipePoliciesTest(TestCase):
    data = Path(__file__).parent / "data"

    def test_scanpipe_policies_load_policies_yaml(self):
        policies_yaml = "{wrong format"
        with self.assertRaises(ValidationError):
            load_policies_yaml(policies_yaml)

        policies_files = self.data / "policy" / "policies.yml"
        policies_dict = load_policies_yaml(policies_files.read_text())
        self.assertIn("license_policies", policies_dict)

    def test_scanpipe_policies_load_policies_file(self):
        policies_files = self.data / "policy" / "policies.yml"
        policies_dict = load_policies_file(policies_files)
        self.assertIn("license_policies", policies_dict)

    def test_scanpipe_policies_validate_policies(self):
        error_msg = "The `policies_dict` argument must be a dictionary."
        policies_dict = None
        with self.assertRaisesMessage(ValidationError, error_msg):
            validate_policies(policies_dict)

        policies_dict = []
        with self.assertRaisesMessage(ValidationError, error_msg):
            validate_policies(policies_dict)

        error_msg = "The `license_policies` key is missing from provided policies data."
        policies_dict = {}
        with self.assertRaisesMessage(ValidationError, error_msg):
            validate_policies(policies_dict)

        policies_dict = {"missing": "data"}
        with self.assertRaisesMessage(ValidationError, error_msg):
            validate_policies(policies_dict)

        policies_dict = global_policies
        self.assertTrue(validate_policies(policies_dict))

    def test_scanpipe_policies_make_license_policy_index(self):
        policies_dict = {"missing": "data"}
        with self.assertRaises(ValidationError):
            make_license_policy_index(policies_dict)

        self.assertEqual(
            license_policies_index, make_license_policy_index(global_policies)
        )

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
from unittest import mock

from django.apps import apps
from django.core.exceptions import ValidationError
from django.test import TestCase

from scanpipe.pipes.input import copy_input
from scanpipe.policies import load_policies_file
from scanpipe.policies import load_policies_yaml
from scanpipe.policies import make_license_policy_index
from scanpipe.policies import validate_policies
from scanpipe.tests import global_policies
from scanpipe.tests import license_policies_index
from scanpipe.tests import make_project

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipePoliciesTest(TestCase):
    data = Path(__file__).parent / "data"

    def test_scanpipe_policies_load_policies_yaml(self):
        policies_yaml = "{wrong format"
        with self.assertRaises(ValidationError):
            load_policies_yaml(policies_yaml)

        policies_files = self.data / "policies" / "policies.yml"
        policies_dict = load_policies_yaml(policies_files.read_text())
        self.assertIn("license_policies", policies_dict)

    def test_scanpipe_policies_load_policies_file(self):
        policies_files = self.data / "policies" / "policies.yml"
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

        error_msg = (
            "At least one of the following policy types must be present: "
            "license_clarity_thresholds, license_policies, "
            "scorecard_score_thresholds"
        )
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

    def test_scanpipe_policies_scan_codebase_pipeline_integration(self):
        pipeline_name = "scan_codebase"
        project1 = make_project()

        input_location = self.data / "policies" / "include_policies_file.zip"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        # Capture the real method's return value
        real_get_license_policy_index = project1.get_license_policy_index

        with mock.patch(
            "scanpipe.models.Project.get_license_policy_index"
        ) as mock_get_index:
            mock_get_index.side_effect = real_get_license_policy_index
            exitcode, out = pipeline.execute()
        mock_get_index.assert_called_once()

        self.assertEqual(0, exitcode, msg=out)
        resource_qs = project1.codebaseresources
        self.assertEqual(6, resource_qs.count())

        resource = resource_qs.get(name="apache-2.0.LICENSE")
        self.assertEqual("apache-2.0", resource.detected_license_expression)
        self.assertEqual("ok", resource.compliance_alert)
        resource = resource_qs.get(name="gpl-2.0.LICENSE")
        self.assertEqual("gpl-2.0", resource.detected_license_expression)
        self.assertEqual("error", resource.compliance_alert)
        resource = resource_qs.get(name="public-domain.LICENSE")
        self.assertEqual("public-domain", resource.detected_license_expression)
        self.assertEqual("missing", resource.compliance_alert)

        resource = resource_qs.get(name="policies.yml")
        self.assertEqual("ignored-pattern", resource.status)
        self.assertEqual("", resource.detected_license_expression)
        self.assertEqual("", resource.compliance_alert)

        expected = "codebase/include_policies_file.zip-extract/policies.yml"
        project_policies_file = project1.get_input_policies_file()
        self.assertTrue(str(project_policies_file).endswith(expected))
        self.assertTrue(project1.license_policies_enabled)
        expected_index = {
            "apache-2.0": {"license_key": "apache-2.0", "compliance_alert": ""},
            "gpl-2.0": {"license_key": "gpl-2.0", "compliance_alert": "error"},
        }
        self.assertEqual(expected_index, project1.get_license_policy_index())

    def test_scanpipe_policies_through_scancode_config_file(self):
        project1 = make_project()
        self.assertEqual({}, project1.get_env())

        test_config_file = self.data / "policies" / "scancode-config.yml"
        copy_input(test_config_file, project1.input_path)

        expected = {
            "policies": [
                {
                    "license_policies": [
                        {"license_key": "mpl-2.0", "compliance_alert": "warning"},
                        {"license_key": "gpl-3.0", "compliance_alert": "error"},
                    ]
                }
            ]
        }
        self.assertEqual(expected, project1.get_env())

        config = {"policies": None}
        project1.settings = config
        project1.save()
        self.assertEqual(expected, project1.get_env())

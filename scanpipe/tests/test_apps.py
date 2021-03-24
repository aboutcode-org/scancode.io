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
from django.test import TestCase
from django.test import override_settings

from scanpipe.apps import ScanPipeConfig
from scanpipe.tests import license_policies
from scanpipe.tests import license_policies_index

scanpipe_app_config = apps.get_app_config("scanpipe")


class ScanPipeAppsTest(TestCase):
    data_location = Path(__file__).parent / "data"

    def test_scanpipe_apps_get_policies_index(self):
        self.assertEqual({}, ScanPipeConfig.get_policies_index([], "license_key"))
        policies_index = ScanPipeConfig.get_policies_index(
            policies_list=license_policies,
            key="license_key",
        )
        self.assertEqual(license_policies_index, policies_index)

    def test_scanpipe_apps_set_policies(self):
        scanpipe_app_config.license_policies_index = {}
        policies_files = None
        with override_settings(POLICIES_FILE=policies_files):
            scanpipe_app_config.set_policies()
            self.assertEqual({}, scanpipe_app_config.license_policies_index)

        scanpipe_app_config.license_policies_index = {}
        policies_files = "not_existing"
        with override_settings(POLICIES_FILE=policies_files):
            scanpipe_app_config.set_policies()
            self.assertEqual({}, scanpipe_app_config.license_policies_index)

        scanpipe_app_config.license_policies_index = {}
        policies_files = self.data_location / "policies.yml"
        with override_settings(POLICIES_FILE=policies_files):
            scanpipe_app_config.set_policies()
            self.assertEqual(
                license_policies_index, scanpipe_app_config.license_policies_index
            )

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


from unittest import mock

from django.test import TestCase

from license_expression import Licensing

from scanpipe.pipes import flag
from scanpipe.pipes import utils


class ScanPipeUtilsTest(TestCase):
    def setUp(self):
        self.licensing = Licensing()

    @mock.patch("scanpipe.models.CodebaseResource")
    @mock.patch("scanpipe.models.DiscoveredPackage")
    @mock.patch("scanpipe.models.Project")
    def test_validate_package_license_integrity_mismatch(
        self, mock_project_class, mock_package_class, mock_resource_class
    ):
        mock_project = mock_project_class()
        mock_package = mock_package_class()

        mock_package.type = "pypi"
        mock_package.package_uid = "pkg:pypi/test@1.0"
        mock_package.get_declared_license_expression.return_value = "mit"
        mock_package.datafile_paths = ["src/main.py"]
        mock_package.extra_data = {}

        mock_project.discoveredpackages.all.return_value = [mock_package]

        mock_resource = mock_resource_class()
        mock_resource.path = "src/main.py"
        mock_resource.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource.detected_license_expression = "gpl-3.0"

        mock_project.codebaseresources.has_license_expression.return_value = [
            mock_resource
        ]

        mock_data_path = mock_resource_class()
        mock_data_path.extra_data = {}
        mock_project.codebaseresources.get.return_value = mock_data_path

        utils.validate_package_license_integrity(mock_project)

        package_update_args = mock_package.update_extra_data.call_args.args[0]
        self.assertEqual(
            package_update_args["issues"][0]["issue_type"], "License Mismatch"
        )
        self.assertEqual(
            package_update_args["issues"][0]["detected_codebase_license"], "gpl-3.0"
        )

        mock_data_path.update.assert_called_once_with(status=flag.LICENSE_ISSUE)

    def test_contains_ignore_pattern(self):
        ignore_patterns = ["*test*", "*.sh"]
        self.assertTrue(
            utils.contains_ignore_pattern("src/test_main.py", ignore_patterns)
        )
        self.assertTrue(
            utils.contains_ignore_pattern("scripts/build.sh", ignore_patterns)
        )
        self.assertFalse(utils.contains_ignore_pattern("src/main.py", ignore_patterns))

    def test_filter_ignored_licenses(self):
        exp1 = self.licensing.parse("mit")
        self.assertEqual(
            str(utils.filter_ignored_licenses(exp1, self.licensing)), "mit"
        )

        exp2 = self.licensing.parse("unknown")
        self.assertIsNone(utils.filter_ignored_licenses(exp2, self.licensing))

        exp3 = self.licensing.parse("mit AND unknown")
        self.assertEqual(
            str(utils.filter_ignored_licenses(exp3, self.licensing)), "mit"
        )

        exp4 = self.licensing.parse("unknown-spdx OR free-unknown")
        self.assertIsNone(utils.filter_ignored_licenses(exp4, self.licensing))

    def test_collect_detected_licenses(self):
        mock_resource1 = mock.Mock()
        mock_resource1.path = "src/main.py"
        mock_resource1.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource1.detected_license_expression = "mit AND unknown"

        mock_resource2 = mock.Mock()
        mock_resource2.path = "test/test_main.py"
        mock_resource2.for_packages = ["pkg:pypi/test@1.0"]
        mock_resource2.detected_license_expression = "gpl-3.0"

        mock_resource3 = mock.Mock()
        mock_resource3.path = "src/other.py"
        mock_resource3.for_packages = ["pkg:pypi/test@2.0"]
        mock_resource3.detected_license_expression = "apache-2.0"

        resources = [mock_resource1, mock_resource2, mock_resource3]
        ignore_patterns = ["*test*"]

        result = utils.collect_detected_licenses(
            resources, ignore_patterns, package_uid="pkg:pypi/test@1.0"
        )

        self.assertEqual(result, ["(mit)"])

    def test_handle_operator_expression_and(self):
        expr = self.licensing.parse("mit AND apache-2.0")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertEqual(str(result), "mit AND apache-2.0")

    def test_handle_operator_expression_or(self):
        expr = self.licensing.parse("mit OR bsd-3-clause")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.OR
        )
        self.assertEqual(str(result), "mit OR bsd-3-clause")

    def test_handle_operator_expression_filters_to_single_arg(self):
        # 'unknown' gets filtered out to None, leaving only 'mit' (len == 1)
        expr = self.licensing.parse("mit AND unknown")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertEqual(str(result), "mit")

    def test_handle_operator_expression_all_filtered_out(self):
        # Both 'unknown' and 'free-unknown' get filtered out, leaving empty args
        expr = self.licensing.parse("unknown AND free-unknown")
        result = utils.handle_operator_expression(
            expr, self.licensing, self.licensing.AND
        )
        self.assertIsNone(result)

    @mock.patch("scanpipe.pipes.utils.shutil.which")
    @mock.patch("scanpipe.pipes.utils.subprocess.run")
    def test_check_docker_command_success(self, mock_subprocess_run, mock_shutil_which):
        mock_shutil_which.return_value = "/usr/bin/docker"
        mock_subprocess_run.return_value = mock.Mock(returncode=0)

        self.assertTrue(utils.check_docker_command())

    @mock.patch("scanpipe.pipes.utils.shutil.which")
    def test_check_docker_command_not_found(self, mock_shutil_which):
        mock_shutil_which.return_value = None

        self.assertFalse(utils.check_docker_command())

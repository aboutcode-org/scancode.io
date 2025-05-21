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

from scanpipe.models import CodebaseResource
from scanpipe.pipes.compliance import get_project_compliance_alerts
from scanpipe.tests import make_package
from scanpipe.tests import make_project
from scanpipe.tests import make_resource_file


class ScanPipeCompliancePipesTest(TestCase):
    def test_scanpipe_compliance_get_project_compliance_alerts(self):
        project = make_project()
        make_resource_file(
            project,
            path="path/",
            compliance_alert=CodebaseResource.Compliance.WARNING,
        )
        make_package(
            project,
            package_url="pkg:generic/name@1.0",
            compliance_alert=CodebaseResource.Compliance.ERROR,
        )

        compliance_alerts = get_project_compliance_alerts(project)
        expected = {"packages": {"error": ["pkg:generic/name@1.0"]}}
        self.assertEqual(expected, compliance_alerts)

        compliance_alerts = get_project_compliance_alerts(project, fail_level="warning")
        expected = {
            "packages": {"error": ["pkg:generic/name@1.0"]},
            "resources": {"warning": ["path/"]},
        }
        self.assertEqual(expected, compliance_alerts)

        # Testing the compliance alert ordering by severity
        make_resource_file(
            project,
            path="path2/",
            compliance_alert=CodebaseResource.Compliance.ERROR,
        )
        make_package(
            project,
            package_url="pkg:generic/name@2.0",
            compliance_alert=CodebaseResource.Compliance.ERROR,
        )
        make_package(
            project,
            package_url="pkg:generic/name@3.0",
            compliance_alert=CodebaseResource.Compliance.MISSING,
        )
        compliance_alerts = get_project_compliance_alerts(project, fail_level="missing")
        expected = {
            "packages": {
                "error": ["pkg:generic/name@1.0", "pkg:generic/name@2.0"],
                "missing": ["pkg:generic/name@3.0"],
            },
            "resources": {"error": ["path2/"], "warning": ["path/"]},
        }
        self.assertEqual(expected, compliance_alerts)

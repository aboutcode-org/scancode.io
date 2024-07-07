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

from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import clamav
from scanpipe.tests import make_resource_file


class ScanPipeClamAVPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    @mock.patch("clamd.ClamdNetworkSocket.multiscan")
    def test_scanpipe_pipes_clamav_scan_for_virus(self, mock_multiscan):
        project = Project.objects.create(name="project")
        r1 = make_resource_file(project=project, path="eicar.zip")
        r2 = make_resource_file(project=project, path="eicar.zip-extract/eicar.com")

        mock_multiscan.return_value = {
            r1.location: ("FOUND", "Win.Test.EICAR_HDB-1"),
            r2.location: ("FOUND", "Win.Test.EICAR_HDB-1"),
        }

        clamav.scan_for_virus(project)
        self.assertEqual(2, len(project.projectmessages.all()))
        error_message = project.projectmessages.all()[0]
        self.assertEqual("error", error_message.severity)
        self.assertEqual("Virus detected", error_message.description)
        self.assertEqual("ScanForVirus", error_message.model)
        expected_details = {
            "reason": "Win.Test.EICAR_HDB-1",
            "status": "FOUND",
            "resource_path": "eicar.zip",
        }
        self.assertEqual(expected_details, error_message.details)

        resource1 = project.codebaseresources.first()
        expected_virus_report_extra_data = {
            "virus_report": {
                "calmav": {
                    "status": "FOUND",
                    "reason": "Win.Test.EICAR_HDB-1",
                }
            }
        }
        self.assertEqual(expected_virus_report_extra_data, resource1.extra_data)

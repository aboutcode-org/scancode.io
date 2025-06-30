# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from pathlib import Path

from django.conf import settings

import clamd


def scan_for_virus(project):
    """
    Run a ClamAV scan to detect virus infection.
    Create one Project error message per found virus and store the detection data
    on the related codebase resource ``extra_data`` field.
    """
    if settings.CLAMD_USE_TCP:
        clamd_socket = clamd.ClamdNetworkSocket(settings.CLAMD_TCP_ADDR)
    else:
        clamd_socket = clamd.ClamdUnixSocket()

    try:
        scan_response = clamd_socket.multiscan(file=str(project.codebase_path))
    except clamd.ClamdError as e:
        raise Exception(f"Error with the ClamAV service: {e}")

    for resource_location, results in scan_response.items():
        status, reason = results
        resource_path = Path(resource_location).relative_to(project.codebase_path)

        resource = project.codebaseresources.get(path=resource_path)
        virus_report = {
            "calmav": {
                "status": status,
                "reason": reason,
            }
        }
        resource.update_extra_data({"virus_report": virus_report})

        project.add_error(
            description="Virus detected",
            model="ScanForVirus",
            details={
                "status": status,
                "reason": reason,
                "resource_path": str(resource_path),
            },
        )

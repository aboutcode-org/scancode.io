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

import logging
from pathlib import Path

from django.conf import settings

import clamd

logger = logging.getLogger(__name__)


def scan_for_virus(project):
    """
    Run a ClamAV scan to detect virus infection.
    - Avoid crashes when ClamAV reports files not indexed in CodebaseResource.
    - Avoid per-file DB queries by preloading valid resource paths.
    - Record a project-level error for any detected virus.
    """
    if settings.CLAMD_USE_TCP:
        clamd_socket = clamd.ClamdNetworkSocket(settings.CLAMD_TCP_ADDR)
    else:
        clamd_socket = clamd.ClamdUnixSocket()

    try:
        scan_response = clamd_socket.multiscan(file=str(project.codebase_path))
    except clamd.ClamdError as e:
        raise Exception(f"Error with the ClamAV service: {e}")

    # Preload all valid indexed resource paths
    valid_paths = set(project.codebaseresources.values_list("path", flat=True))

    missing_resources = []

    for resource_location, results in scan_response.items():
        status, reason = results

        if status != "FOUND":
            continue

        resource_path = Path(resource_location).relative_to(project.codebase_path)
        resource_path_str = str(resource_path)

        if resource_path_str not in valid_paths:
            missing_resources.append(resource_path_str)
            logger.warning(
                "ClamAV detected virus in non-indexed file: %s",
                resource_path_str,
            )
            continue

        resource = project.codebaseresources.filter(path=resource_path_str).first()

        virus_report = {
            "clamav": {
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
                "resource_path": resource_path_str,
            },
        )

    if missing_resources:
        project.add_error(
            description="ClamAV detected virus in files not indexed in DB",
            model="ScanForVirus",
            details={"missing_resources": missing_resources},
        )

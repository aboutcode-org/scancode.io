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

import sys
from pathlib import Path

from django.core.management.base import BaseCommand

from scancode_config import __version__ as scancode_version

from scanner.models import Scan


class Command(BaseCommand):
    help = (
        "Remove the Scan results files older than the current ScanCode-toolkit "
        "version.\n"
        "This will only impact outdated results on successful Scans that have a "
        "results file available for the current ScanCode-toolkit version."
    )

    def handle(self, *args, **options):
        self.stdout.write(f"ScanCode-toolkit version: {scancode_version}")

        completed_scans = Scan.objects.completed()
        up_to_date_scans = completed_scans.filter(scancode_version=scancode_version)
        old_scan_results = []

        for scan in up_to_date_scans:
            output_file_path = Path(str(scan.output_file))
            parent_dir = output_file_path.parent
            output_file_name = output_file_path.name
            to_delete = [
                path
                for path in parent_dir.iterdir()
                if path.name.startswith("scan_")
                and path.name.endswith(".json")
                and path.name != output_file_name
            ]
            old_scan_results.extend(to_delete)

        old_scan_results_len = len(old_scan_results)
        if not old_scan_results:
            self.stdout.write(self.style.SUCCESS("No Scan data to remove."))
            sys.exit()

        confirm = input(
            f"{old_scan_results_len} scan results files found for deletion.\n"
            f"Are you sure you want to do this? \n"
            f"Type 'yes' to continue, or 'no' to cancel: "
        )
        if confirm == "yes":
            for file_path in old_scan_results:
                file_path.unlink()
            self.stdout.write(self.style.SUCCESS(f"{old_scan_results_len} deleted."))
        else:
            self.stdout.write("Deletion cancelled.\n")

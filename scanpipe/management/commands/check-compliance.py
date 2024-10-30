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

from scanpipe.management.commands import ProjectCommand
from scanpipe.pipes.compliance import get_project_compliance_alerts


class Command(ProjectCommand):
    help = (
        "Check for compliance issues in Project. Exit with a non-zero status if "
        "compliance issues are present in the project."
        "The compliance alert indicates how the license expression complies with "
        "provided policies."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--fail-level",
            default="ERROR",
            choices=["ERROR", "WARNING", "MISSING"],
            help=(
                "Compliance alert level that will cause the command to exit with a "
                "non-zero status. Default is ERROR."
            ),
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)
        fail_level = options["fail_level"]
        compliance_alerts = get_project_compliance_alerts(self.project, fail_level)

        compliance_alerts_count = sum(
            len(issues_by_severity)
            for model_alerts in compliance_alerts.values()
            for issues_by_severity in model_alerts.values()
        )
        if not compliance_alerts_count:
            sys.exit(0)

        if self.verbosity > 0:
            msg = [
                f"{compliance_alerts_count} compliance issues detected on "
                f"this project."
            ]
            for label, issues in compliance_alerts.items():
                msg.append(f"[{label}]")
                for severity, entries in issues.items():
                    msg.append(f" > {severity.upper()}: {len(entries)}")
                    if self.verbosity > 1:
                        msg.append("   " + "\n   ".join(entries))

            self.stderr.write("\n".join(msg))

        sys.exit(1)

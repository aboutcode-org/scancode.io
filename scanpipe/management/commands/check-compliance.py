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
        parser.add_argument(
            "--fail-on-vulnerabilities",
            action="store_true",
            help=(
                "Exit with a non-zero status if known vulnerabilities are detected in "
                "discovered packages and dependencies. "
                "Requires the `find_vulnerabilities` pipeline to be executed "
                "beforehand."
            ),
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)
        exit_code = 0

        if self.check_compliance(options["fail_level"]):
            exit_code = 1

        if options["fail_on_vulnerabilities"] and self.check_vulnerabilities():
            exit_code = 1

        sys.exit(exit_code)

    def check_compliance(self, fail_level):
        alerts = get_project_compliance_alerts(self.project, fail_level)
        count = sum(
            len(issues) for model in alerts.values() for issues in model.values()
        )

        clarity_alert = self.project.get_license_clarity_compliance_alert()
        has_clarity_issue = clarity_alert not in (None, "ok")

        scorecard_alert = self.project.get_scorecard_compliance_alert()
        has_scorecard_issue = scorecard_alert not in (None, "ok")

        total_issues = (
            count + (1 if has_clarity_issue else 0) + (1 if has_scorecard_issue else 0)
        )

        if total_issues and self.verbosity > 0:
            self.stderr.write(f"{total_issues} compliance issues detected.")
            for label, model in alerts.items():
                self.stderr.write(f"[{label}]")
                for severity, entries in model.items():
                    self.stderr.write(f" > {severity.upper()}: {len(entries)}")
                    if self.verbosity > 1:
                        self.stderr.write("   " + "\n   ".join(entries))

            if has_clarity_issue:
                self.stderr.write("[license clarity]")
                self.stderr.write(f" > {clarity_alert.upper()}")

            if has_scorecard_issue:
                self.stderr.write("[scorecard compliance]")
                self.stderr.write(f" > {scorecard_alert.upper()}")

        return total_issues > 0

    def check_vulnerabilities(self):
        all_vulnerabilities = self.project.vulnerabilities
        vulnerabilities_count = len(all_vulnerabilities)

        if self.verbosity > 0:
            if vulnerabilities_count:
                self.stderr.write(f"{vulnerabilities_count} vulnerabilities found:")
                for vulnerability_id, vulnerability_data in all_vulnerabilities.items():
                    self.stderr.write(str(vulnerability_id))
                    for affected_obj in vulnerability_data.get("affects", []):
                        self.stderr.write(f" > {affected_obj}")
            else:
                self.stdout.write("No vulnerabilities found")

        return vulnerabilities_count > 0

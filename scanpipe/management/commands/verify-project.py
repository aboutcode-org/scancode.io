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

from django.core.management import CommandError

from scanpipe.management.commands import ProjectCommand


class Command(ProjectCommand):
    help = "Verify project analysis results against expected counts"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--packages",
            type=int,
            default=None,
            help="Expected number of packages",
        )
        parser.add_argument(
            "--vulnerable-packages",
            type=int,
            default=None,
            help="Expected number of vulnerable packages",
        )
        parser.add_argument(
            "--dependencies",
            type=int,
            default=None,
            help="Expected number of dependencies",
        )
        parser.add_argument(
            "--vulnerable-dependencies",
            type=int,
            default=None,
            help="Expected number of vulnerable dependencies",
        )
        parser.add_argument(
            "--vulnerabilities",
            type=int,
            default=None,
            help=(
                "Expected number of unique vulnerabilities. "
                "Combines vulnerabilities from both packages and dependencies"
            ),
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Assert on strict count equality instead of minimum threshold",
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)

        expected_packages = options["packages"]
        expected_vulnerable_packages = options["vulnerable_packages"]
        expected_dependencies = options["dependencies"]
        expected_vulnerable_dependencies = options["vulnerable_dependencies"]
        expected_vulnerabilities = options["vulnerabilities"]
        strict = options["strict"]

        project = self.project
        packages = project.discoveredpackages
        dependencies = project.discovereddependencies
        vulnerabilities = project.vulnerabilities

        # Check all counts (only if expected value is provided)
        checks = [
            (
                packages.count(),
                expected_packages,
                "packages",
            ),
            (
                packages.vulnerable().count(),
                expected_vulnerable_packages,
                "vulnerable packages",
            ),
            (
                dependencies.count(),
                expected_dependencies,
                "dependencies",
            ),
            (
                dependencies.vulnerable().count(),
                expected_vulnerable_dependencies,
                "vulnerable dependencies",
            ),
            (
                len(vulnerabilities),
                expected_vulnerabilities,
                "vulnerabilities on the project",
            ),
        ]

        errors = []
        for actual, expected, label in checks:
            if expected is not None:  # Only check if value was provided
                if error := self.check_count(actual, expected, label, strict):
                    errors.append(error)

        if errors:
            raise CommandError("Project verification failed:\n" + "\n".join(errors))

        self.stdout.write("Project verification passed.", self.style.SUCCESS)

    @staticmethod
    def check_count(actual, expected, label, strict):
        """
        Check if actual count meets expectations.

        In strict mode, checks for exact equality.
        Otherwise, checks if actual is at least the expected value.

        Returns an error message string if check fails.
        """
        if strict and actual != expected:
            return f"Expected exactly {expected} {label}, found {actual}"

        if not strict and actual < expected:
            return f"Expected at least {expected} {label}, found {actual}"

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
            default=0,
            help="Minimum number of packages expected (default: 0)",
        )
        parser.add_argument(
            "--vulnerable-packages",
            type=int,
            default=0,
            help="Minimum number of vulnerable packages expected (default: 0)",
        )
        parser.add_argument(
            "--dependencies",
            type=int,
            default=0,
            help="Minimum number of dependencies expected (default: 0)",
        )
        parser.add_argument(
            "--vulnerable-dependencies",
            type=int,
            default=0,
            help="Minimum number of vulnerable dependencies expected (default: 0)",
        )
        parser.add_argument(
            "--vulnerabilities",
            type=int,
            default=0,
            help=(
                "Minimum number of unique vulnerabilities expected (default: 0). "
                "Combines vulnerabilities from both packages and dependencies"
            ),
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)

        expected_packages = options["packages"]
        expected_vulnerable_packages = options["vulnerable_packages"]
        expected_dependencies = options["dependencies"]
        expected_vulnerable_dependencies = options["vulnerable_dependencies"]
        expected_vulnerabilities = options["vulnerabilities"]

        project = self.project
        packages = project.discoveredpackages
        package_count = packages.count()
        vulnerable_package_count = packages.vulnerable().count()
        dependencies = project.discovereddependencies.all()
        dependency_count = dependencies.count()
        vulnerable_dependency_count = dependencies.vulnerable().count()
        vulnerability_count = len(project.vulnerabilities)
        errors = []

        if package_count < expected_packages:
            errors.append(
                f"Expected at least {expected_packages} packages, found {package_count}"
            )
        if vulnerable_package_count < expected_vulnerable_packages:
            errors.append(
                f"Expected at least {expected_vulnerable_packages} vulnerable packages,"
                f" found {vulnerable_package_count}"
            )
        if dependency_count < expected_dependencies:
            errors.append(
                f"Expected at least {expected_dependencies} dependencies, "
                f"found {dependency_count}"
            )
        if vulnerable_dependency_count < expected_vulnerable_dependencies:
            errors.append(
                f"Expected at least {expected_vulnerable_dependencies} "
                f"vulnerable dependencies, found {vulnerable_dependency_count}"
            )
        if vulnerability_count < expected_vulnerabilities:
            errors.append(
                f"Expected at least {expected_vulnerabilities} "
                f"vulnerabilities total on the project, "
                f"found {vulnerability_count}"
            )

        if errors:
            raise CommandError("Project verification failed:\n" + "\n".join(errors))

        self.stdout.write("Project verification passed.", self.style.SUCCESS)

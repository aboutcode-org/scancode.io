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

import sys

from scanpipe.management.commands import ProjectCommand


class Command(ProjectCommand):
    help = "Delete a project and its related work directory."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt the user for input of any kind.",
        )

    def handle(self, *inputs, **options):
        super().handle(*inputs, **options)

        if options["interactive"]:
            confirm = input(
                f"You have requested the deletion of the {self.project} project.\n"
                f"This will IRREVERSIBLY DESTROY all data related to that project.\n"
                f"Are you sure you want to do this?\n"
                f"Type 'yes' to continue, or 'no' to cancel: "
            )
            if confirm != "yes":
                if self.verbosity > 0:
                    self.stdout.write("Deletion cancelled.")
                sys.exit(0)

        self.project.delete()

        if self.verbosity > 0:
            msg = f"All the {self.project} project data have been removed."
            self.stdout.write(msg, self.style.SUCCESS)

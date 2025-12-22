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

from django.core.management import CommandError

from scanpipe.management.commands import ProjectCommand
from scanpipe.models import RunInProgressError


class Command(ProjectCommand):
    help = (
        "Reset a project removing all database entries and all data on disks "
        "except for the input/ directory."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt the user for input of any kind.",
        )
        parser.add_argument(
            "--remove-input",
            action="store_true",
            help="Remove the input directory and input sources when resetting.",
        )
        parser.add_argument(
            "--remove-webhook",
            action="store_true",
            help="Remove webhook subscriptions when resetting.",
        )
        parser.add_argument(
            "--restore-pipelines",
            action="store_true",
            help="Restore all pipelines that were previously existing on the project.",
        )
        parser.add_argument(
            "--execute-now",
            action="store_true",
            help="Execute the restored pipelines immediately after restoration.",
        )

    def handle(self, *inputs, **options):
        super().handle(*inputs, **options)

        if options["interactive"]:
            confirm = input(
                f"You have requested the reset of the {self.project} project.\n"
                f"This will IRREVERSIBLY DESTROY all data, except inputs, related to "
                f"that project. \n"
                f"Are you sure you want to do this?\n"
                f"Type 'yes' to continue, or 'no' to cancel: "
            )
            if confirm != "yes":
                if self.verbosity > 0:
                    self.stdout.write("Reset cancelled.")
                sys.exit(0)

        keep_input = not options["remove_input"]
        keep_webhook = not options["remove_webhook"]

        try:
            self.project.reset(
                keep_input=keep_input,
                keep_webhook=keep_webhook,
                restore_pipelines=options["restore_pipelines"],
                execute_now=options["execute_now"],
            )
        except RunInProgressError as error:
            raise CommandError(error)

        if self.verbosity > 0:
            msg = f"The {self.project} project has been reset."
            self.stdout.write(msg, self.style.SUCCESS)

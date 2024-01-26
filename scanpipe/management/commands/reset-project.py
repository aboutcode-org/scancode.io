#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import sys

from scanpipe.management.commands import ProjectCommand


class Command(ProjectCommand):
    help = (
        "Reset a project removing all database entrie and all data on disks "
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
                self.stdout.write("Reset cancelled.")
                sys.exit(0)

        self.project.reset(keep_input=True)

        msg = (
            f"All data, except inputs, for the {self.project} project have been "
            f"removed."
        )
        self.stdout.write(msg, self.style.SUCCESS)

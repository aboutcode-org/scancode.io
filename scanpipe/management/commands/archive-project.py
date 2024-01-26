#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import sys

from django.core.management import CommandError

from scanpipe.management.commands import ProjectCommand
from scanpipe.models import RunInProgressError


class Command(ProjectCommand):
    help = "Archive a project and remove selected work directories."

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
            dest="remove_input",
            help="Remove the input/ directory.",
        )
        parser.add_argument(
            "--remove-codebase",
            action="store_true",
            dest="remove_codebase",
            help="Remove the codebase/ directory.",
        )
        parser.add_argument(
            "--remove-output",
            action="store_true",
            dest="remove_output",
            help="Remove the output/ directory.",
        )

    def handle(self, *inputs, **options):
        super().handle(*inputs, **options)

        if options["interactive"]:
            confirm = input(
                f"You have requested to archive the {self.project} project.\n"
                f"Are you sure you want to do this?\n"
                f"Type 'yes' to continue, or 'no' to cancel: "
            )
            if confirm != "yes":
                self.stdout.write("Archive cancelled.")
                sys.exit(0)

        try:
            self.project.archive(
                remove_input=options["remove_input"],
                remove_codebase=options["remove_codebase"],
                remove_output=options["remove_output"],
            )
        except RunInProgressError as error:
            raise CommandError(error)

        msg = f"The {self.project} project has been archived."
        self.stdout.write(msg, self.style.SUCCESS)

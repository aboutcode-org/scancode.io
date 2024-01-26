#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from scanpipe.management.commands import ProjectCommand
from scanpipe.management.commands import RunStatusCommandMixin


class Command(ProjectCommand, RunStatusCommandMixin):
    help = "Display status information about the provided project."

    def handle(self, *args, **options):
        super().handle(*args, **options)

        # The `status` command is very verbose by default compared to the
        # `list-project` command.
        verbosity = options["verbosity"] + 2
        self.display_status(self.project, verbosity)

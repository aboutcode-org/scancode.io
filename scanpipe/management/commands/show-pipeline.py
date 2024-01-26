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
    help = "Show pipelines of a project."

    def handle(self, *args, **options):
        super().handle(*args, **options)

        for run in self.project.runs.all():
            status_code = self.get_run_status_code(run)
            self.stdout.write(f" [{status_code}] {run.pipeline_name}")

#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#


from django.core.management.base import BaseCommand

from scanpipe.filters import ProjectFilterSet
from scanpipe.management.commands import RunStatusCommandMixin


class Command(BaseCommand, RunStatusCommandMixin):
    help = "Lists ScanPipe projects."
    separator = "-" * 50

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--search", help="Limit the projects list to this search results."
        )
        parser.add_argument(
            "--include-archived",
            action="store_true",
            dest="include_archived",
            help="Include archived projects.",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        filter_data = {"search": options["search"]}

        if options["include_archived"]:
            filter_data["is_archived"] = None

        projects = ProjectFilterSet(filter_data).qs
        project_count = len(projects)

        for index, project in enumerate(projects, start=1):
            self.display_status(project, verbosity)

            if index != project_count and verbosity > 1:
                self.stdout.write(f"\n{self.separator}\n\n")

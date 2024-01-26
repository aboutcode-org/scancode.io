#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.template.defaultfilters import pluralize

from scanpipe.management.commands import ProjectCommand
from scanpipe.management.commands import validate_pipelines


class Command(ProjectCommand):
    help = "Add pipelines to a project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "args",
            metavar="PIPELINE_NAME",
            nargs="+",
            help="One or more pipeline names.",
        )

    def handle(self, *pipeline_names, **options):
        super().handle(*pipeline_names, **options)

        pipeline_names = validate_pipelines(pipeline_names)
        for pipeline_name in pipeline_names:
            self.project.add_pipeline(pipeline_name)

        msg = (
            f"Pipeline{pluralize(pipeline_names)} {', '.join(pipeline_names)} "
            f"added to the project"
        )
        self.stdout.write(msg, self.style.SUCCESS)

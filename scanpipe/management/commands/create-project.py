#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.core.management import call_command
from django.core.management.base import BaseCommand

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import validate_copy_from
from scanpipe.management.commands import validate_input_files
from scanpipe.management.commands import validate_pipelines
from scanpipe.models import Project


class Command(AddInputCommandMixin, BaseCommand):
    help = "Create a ScanPipe project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("name", help="Project name.")
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            default=list(),
            help=(
                "Pipelines names to add to the project."
                "The pipelines are added and executed based on their given order."
            ),
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the pipelines right after the project creation.",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            help=(
                "Add the pipeline run to the tasks queue for execution by a worker "
                "instead of running in the current thread. "
                "Applies only when --execute is provided."
            ),
        )
        parser.add_argument(
            "--notes",
            help="Optional notes about the project.",
        )

    def handle(self, *args, **options):
        name = options["name"]
        pipeline_names = options["pipelines"]
        inputs_files = options["inputs_files"]
        input_urls = options["input_urls"]
        copy_from = options["copy_codebase"]
        execute = options["execute"]

        project = Project(name=name)
        if notes := options["notes"]:
            project.notes = notes

        try:
            project.full_clean(exclude=["slug"])
        except ValidationError as e:
            raise CommandError("\n".join(e.messages))

        # Run validation before creating the project in the database
        pipeline_names = validate_pipelines(pipeline_names)
        validate_input_files(inputs_files)
        validate_copy_from(copy_from)

        if execute and not pipeline_names:
            raise CommandError("The --execute option requires one or more pipelines.")

        project.save()
        msg = f"Project {name} created with work directory {project.work_directory}"
        self.stdout.write(msg, self.style.SUCCESS)

        for pipeline_name in pipeline_names:
            project.add_pipeline(pipeline_name)

        self.project = project
        if inputs_files:
            self.validate_input_files(inputs_files)
            self.handle_input_files(inputs_files)

        if input_urls:
            self.handle_input_urls(input_urls)

        if copy_from:
            self.handle_copy_codebase(copy_from)

        if execute:
            call_command(
                "execute",
                project=project,
                stderr=self.stderr,
                stdout=self.stdout,
                **{"async": options["async"]},
            )

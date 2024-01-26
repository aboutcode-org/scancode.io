#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import sys

from django.conf import settings
from django.core.management import CommandError

from scanpipe import tasks
from scanpipe.management.commands import ProjectCommand


class Command(ProjectCommand):
    help = "Run pipelines on a project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--async",
            action="store_true",
            dest="async",
            help=(
                "Add the pipeline run to the tasks queue for execution by a worker "
                "instead of running in the current thread."
            ),
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)

        run = self.project.get_next_run()

        if not run:
            raise CommandError(f"No pipelines to run on project {self.project}")

        if options["async"]:
            if not settings.SCANCODEIO_ASYNC:
                msg = "SCANCODEIO_ASYNC=False is not compatible with --async option."
                raise CommandError(msg)

            run.start()
            msg = f"{run.pipeline_name} added to the tasks queue for execution."
            self.stdout.write(msg, self.style.SUCCESS)
            sys.exit(0)

        self.stdout.write(f"Start the {run.pipeline_name} pipeline execution...")

        try:
            tasks.execute_pipeline_task(run.pk)
        except KeyboardInterrupt:
            run.set_task_stopped()
            raise CommandError("Pipeline execution stopped.")
        except Exception as e:
            run.set_task_ended(exitcode=1, output=str(e))
            raise CommandError(e)

        run.refresh_from_db()

        if run.task_succeeded:
            msg = f"{run.pipeline_name} successfully executed on project {self.project}"
            self.stdout.write(msg, self.style.SUCCESS)
        else:
            msg = f"Error during {run.pipeline_name} execution:\n{run.task_output}"
            raise CommandError(msg)

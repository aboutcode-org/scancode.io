# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

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

            run.execute_task_async()
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

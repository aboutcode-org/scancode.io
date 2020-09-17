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

from django.core.management import CommandError

from scanpipe.management.commands import ProjectCommand


class Command(ProjectCommand):
    help = "Run pipelines of a project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--show",
            action="store_true",
            dest="show",
            default=False,
            help="Shows all available pipeline runs for the current project",
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)

        if options["show"]:
            for run in self.project.runs.all():
                status = self.get_run_status_code(run)
                self.stdout.write(f" [{status}] {run.pipeline}")
            sys.exit(0)

        run = self.project.get_next_run()
        if not run:
            raise CommandError(f"No pipelines to run on Project {self.project}")

        msg = f"Pipeline {run.pipeline} run in progress..."
        self.stdout.write(self.style.SUCCESS(msg))
        run.run_pipeline_task_async()

    def get_run_status_code(self, run):
        status = " "
        if run.task_succeeded:
            status = self.style.SUCCESS("V")
        elif run.task_exitcode and run.task_exitcode > 0:
            status = self.style.ERROR("E")
        return status

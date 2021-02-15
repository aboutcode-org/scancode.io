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

    def handle(self, *args, **options):
        super().handle(*args, **options)

        run = self.project.get_next_run()

        if not run:
            raise CommandError(f"No pipelines to run on project {self.project}")

        self.stdout.write(f"Pipeline {run.pipeline_name} run in progress...")
        run.run_pipeline_task_async()
        run.refresh_from_db()

        if run.task_succeeded:
            msg = f"{run.pipeline_name} successfully executed on project {self.project}"
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            msg = f"Error during {run.pipeline_name} execution:\n"
            self.stderr.write(self.style.ERROR(msg))
            self.stderr.write(run.task_output)
            sys.exit(1)

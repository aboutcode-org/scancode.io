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

from django.apps import apps
from django.utils import timezone

from celery import shared_task
from celery.utils.log import get_task_logger

from scanner.tasks import run_command

tasks_logger = get_task_logger(__name__)
python = sys.executable


def info(message, pk):
    tasks_logger.info(f"Run[{pk}] {message}")


def get_run_instance(run_pk):
    """
    Return the run instance using the `run_pk`.
    """
    run_model = apps.get_model("scanpipe", "Run")
    return run_model.objects.get(pk=run_pk)


def start_run(run, task_id):
    """
    Set the `task_id` and `task_start_date`.
    """
    run.task_id = task_id
    run.task_start_date = timezone.now()
    run.save()


def update_run(run, exitcode, output):
    """
    Update the `run` instance "task_" fields following its execution.
    """
    # WARNING: Always refresh the instance with the latest data from the
    # database before saving to avoid loosing values set on the instance
    # during the pipeline run.
    run.refresh_from_db()
    run.task_exitcode = exitcode
    run.task_output = output
    run.task_end_date = timezone.now()
    run.save()


def start_next_run_task(run):
    """
    Create and start the next Pipeline Run in the Project queue, if any.
    """
    next_run = run.project.get_next_run()
    if next_run:
        next_run.run_pipeline_task_async()


@shared_task(bind=True)
def run_pipeline_task(self, run_pk):
    task_id = self.request.id
    info(f"Enter `{self.name}` Task.id={task_id}", run_pk)

    run = get_run_instance(run_pk)
    start_run(run, task_id)

    info(f'Run pipeline: "{run.pipeline}" on project: "{run.project.name}"', run_pk)
    cmd = f"{python} {run.pipeline} run --project {run.project.name}"
    exitcode, output = run_command(cmd)

    info("Update Run instance with exitcode, output, and end_date", run_pk)
    update_run(run, exitcode, output)

    if run.task_succeeded:
        # We keep the temporary files available for resume in case of error
        run.project.clear_tmp_directory()
        start_next_run_task(run)


@shared_task(bind=True)
def resume_pipeline_task(self, run_pk):
    task_id = self.request.id
    info(f"Enter `{self.name}` Task.id={task_id}", run_pk)

    run = get_run_instance(run_pk)
    run.reset_task_values()
    start_run(run, task_id)
    run_id = run.get_run_id()

    info(f'Resume pipeline: "{run.pipeline}" on project: "{run.project.name}"', run_pk)
    cmd = f"{python} {run.pipeline} resume --origin-run-id {run_id}"
    exitcode, output = run_command(cmd)

    info("Update Run instance with exitcode, output, and end_date", run_pk)
    update_run(run, exitcode, output)

    if run.task_succeeded:
        # We keep the temporary files available for resume in case of error
        run.project.clear_tmp_directory()
        start_next_run_task(run)

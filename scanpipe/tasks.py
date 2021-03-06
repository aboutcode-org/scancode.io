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

from django.apps import apps

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

tasks_logger = get_task_logger(__name__)


def info(message, pk):
    tasks_logger.info(f"Run[{pk}] {message}")


def get_run_instance(run_pk):
    """
    Return the run instance using the `run_pk`.
    """
    run_model = apps.get_model("scanpipe", "Run")
    return run_model.objects.get(pk=run_pk)


@shared_task(bind=True)
def execute_pipeline_task(self, run_pk):
    task_id = self.request.id
    info(f"Enter `{self.name}` Task.id={task_id}", run_pk)

    run = get_run_instance(run_pk)
    project = run.project

    run.reset_task_values()
    run.set_task_started(task_id)

    info(f'Run pipeline: "{run.pipeline_name}" on project: "{project.name}"', run_pk)

    pipeline = run.make_pipeline_instance()

    try:
        exitcode, output = pipeline.execute()
    except SoftTimeLimitExceeded:
        info("SoftTimeLimitExceeded", run_pk)
        exitcode, output = 1, "SoftTimeLimitExceeded"

    info("Update Run instance with exitcode, output, and end_date", run_pk)
    run.set_task_ended(exitcode, output, refresh_first=True)

    if run.task_succeeded:
        # We keep the temporary files available for debugging in case of error
        project.clear_tmp_directory()

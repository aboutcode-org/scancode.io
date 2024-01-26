#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import logging

from django.apps import apps

logger = logging.getLogger(__name__)


def info(message, pk):
    logger.info(f"Run[{pk}] {message}")


def get_run_instance(run_pk):
    """Return the run instance using the `run_pk`."""
    Run = apps.get_model("scanpipe", "Run")
    return Run.objects.get(pk=run_pk)


def report_failure(job, connection, type, value, traceback):
    """
    Report a job failure as a call back when an exception is raised during the Job
    execution but was not caught by the task itself.
    """
    Run = apps.get_model("scanpipe", "Run")
    try:
        run = get_run_instance(run_pk=job.id)
    except Run.DoesNotExist:
        info(f"FAILURE to get the Run instance with job.id={job.id}", "Unknown")
        return

    run.set_task_ended(exitcode=1, output=f"value={value} trace={traceback}")


def execute_pipeline_task(run_pk):
    info(f"Enter `execute_pipeline_task` Run.pk={run_pk}", run_pk)

    run = get_run_instance(run_pk)
    project = run.project

    run.reset_task_values()
    run.set_scancodeio_version()
    run.set_task_started(run_pk)

    info(f'Run pipeline: "{run.pipeline_name}" on project: "{project.name}"', run_pk)

    pipeline = run.make_pipeline_instance()
    exitcode, output = pipeline.execute()

    info("Update Run instance with exitcode, output, and end_date", run_pk)
    run.set_task_ended(exitcode, output)
    run.deliver_project_subscriptions()

    if run.task_succeeded:
        # We keep the temporary files available for debugging in case of error
        project.clear_tmp_directory()
        if next_run := project.get_next_run():
            next_run.start()

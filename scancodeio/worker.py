#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.apps import apps

from rq.queue import Queue
from rq.worker import Worker

scanpipe_app = apps.get_app_config("scanpipe")


class ScanCodeIOWorker(Worker):
    """Modified version of RQ Worker including ScanCode.io customizations."""

    def run_maintenance_tasks(self):
        """
        Add Runs and Jobs synchronization to the periodic maintenance tasks.
        Maintenance tasks should run on first worker startup or every 10 minutes.

        During the maintenance, one of the worker will acquire a "cleaning lock" and
        will run the registries cleanup.
        During that cleanup, started Jobs that haven't sent a heartbeat in the past 90
        seconds (job_monitoring_interval + 60) will be considered failed and will be
        moved to the FailedJobRegistry.
        This happens when the Job process is killed (voluntary or not) and the heartbeat
        is the RQ approach to determine if the job is stills active.
        The `sync_runs_and_jobs` will see this Job as failed and will update its related
        Run accordingly.
        """
        super().run_maintenance_tasks()

        # The Runs and Jobs synchronization needs to be executed after the
        # `self.clean_registries()` that takes place in the parent
        # `super().run_maintenance_tasks()`.
        scanpipe_app.sync_runs_and_jobs()


class ScanCodeIOQueue(Queue):
    """Modified version of RQ Queue including ScanCode.io customizations."""

    # Reduce the "cleaning lock" ttl from default hardcoded 899 seconds to 59 seconds.
    cleaning_lock_ttl = 59

    def acquire_maintenance_lock(self) -> bool:
        """Return a boolean indicating if a lock to clean this queue is acquired."""
        lock_acquired = self.connection.set(
            self.registry_cleaning_key, 1, nx=1, ex=self.cleaning_lock_ttl
        )
        if not lock_acquired:
            return False
        return lock_acquired

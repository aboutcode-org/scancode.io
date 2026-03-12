# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from django import db as django_db
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


class ScanCodeIOTlsWorker(ScanCodeIOWorker):
    """
    Modified version of RQ Worker including ScanCode.io customizations for
    maintenance tasks and TLS.
    """

    def execute_job(self, job, queue):
        """
        Terminate existing database connection to avoid issues with TLS.
        https://github.com/aboutcode-org/scancode.io/issues/1523
        """
        django_db.connection.close()
        super().execute_job(job, queue)


class ScanCodeIOQueue(Queue):
    """Modified version of RQ Queue including ScanCode.io customizations."""

    # Reduce the "cleaning lock" ttl from default hardcoded 899 seconds to 59 seconds.
    cleaning_lock_ttl = 59

    def acquire_maintenance_lock(self) -> bool:
        """Return a boolean indicating if a lock to clean this queue is acquired."""
        lock_acquired = self.connection.set(
            self.registry_cleaning_key, 1, nx=True, ex=self.cleaning_lock_ttl
        )
        if not lock_acquired:
            return False
        return lock_acquired

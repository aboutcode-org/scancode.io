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

import time
import traceback

from django.core.management.base import BaseCommand

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import CreateProjectCommandMixin
from scanpipe.management.commands import execute_project
from scanpipe.models import Run
from scanpipe.pipes import purldb


class Command(CreateProjectCommandMixin, AddInputCommandMixin, BaseCommand):
    help = "Get a Package to be scanned from PurlDB and return the results"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--sleep",
            type=int,
            default=0,
            action="store",
            help="Number in seconds how long the loop should sleep for before polling.",
        )

        parser.add_argument(
            "--max-loops",
            dest="max_loops",
            type=int,
            default=0,
            action="store",
            help="Limit the number of loops to a maximum number. "
            "0 means no limit. Used only for testing.",
        )

        parser.add_argument(
            "--max-concurrent-projects",
            dest="max_concurrent_projects",
            type=int,
            default=1,
            action="store",
            help="Limit the number of Projects that can be run at once.",
        )

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        sleep = options["sleep"]
        run_async = options["async"]
        max_loops = options["max_loops"]
        max_concurrent_projects = options["max_concurrent_projects"]

        loop_count = 0
        while True:
            if max_loops and loop_count >= max_loops:
                self.stdout.write("loop max reached")
                break

            time.sleep(sleep)
            loop_count += 1

            # Usually, a worker can only run one Run at a time
            queued_or_running = Run.objects.queued_or_running()
            queued_or_running_count = queued_or_running.count()
            if queued_or_running_count >= max_concurrent_projects:
                self.stdout.write(
                    "Continuing: number of queued or running Runs"
                    f"({queued_or_running_count}) is greater "
                    "than the number of max concurrent projects "
                    f"({max_concurrent_projects})"
                )
                continue

            # 1. Get download url from purldb
            response = purldb.get_next_download_url()
            if response:
                scannable_uri_uuid = response["scannable_uri_uuid"]
                download_url = response["download_url"]
                pipelines = response["pipelines"]
                webhook_url = response["webhook_url"]
            else:
                self.stderr.write("Bad response from PurlDB: unable to get next job.")
                continue

            if not (download_url and scannable_uri_uuid):
                self.stdout.write("No new job from PurlDB.")
                continue
            else:
                formatted_pipeline_names = [f"\t\t{pipeline}" for pipeline in pipelines]
                formatted_pipeline_names = "\n".join(formatted_pipeline_names)
                msg = (
                    "New job from PurlDB:\n"
                    "\tscannable_uri_uuid:\n"
                    f"\t\t{scannable_uri_uuid}\n"
                    "\tdownload_url:\n"
                    f"\t\t{download_url}\n"
                    "\tpipelines:\n"
                ) + formatted_pipeline_names
                self.stdout.write(msg)

            try:
                # 2. Create and run project
                project = create_scan_project(
                    command=self,
                    scannable_uri_uuid=scannable_uri_uuid,
                    download_url=download_url,
                    pipelines=pipelines,
                    webhook_url=webhook_url,
                    run_async=run_async,
                )

                self.stdout.write(
                    f"Project {project.name} has been created",
                    self.style.SUCCESS,
                )

            except Exception:
                tb = traceback.format_exc()
                error_log = f"Exception occurred during scan project:\n\n{tb}"
                purldb.update_status(
                    scannable_uri_uuid,
                    status="failed",
                    scan_log=error_log,
                )
                self.stderr.write(error_log)


def create_scan_project(
    command, scannable_uri_uuid, download_url, pipelines, webhook_url, run_async=False
):
    """
    Create and return a Project for the scan project request with ID of
    `scannable_uri_uuid`, where the target at `download_url` is fetched, and the
    pipelines from `pipelines` is then run.

    If `run_async` is True, the pipelines on the Project is run in a separate
    thread.
    """
    name = purldb.create_project_name(download_url, scannable_uri_uuid)
    input_urls = [download_url]
    project = command.create_project(
        name=name,
        pipelines=pipelines,
        input_urls=input_urls,
    )
    project.update_extra_data(
        {
            "scannable_uri_uuid": scannable_uri_uuid,
        }
    )
    project.add_webhook_subscription(
        target_url=webhook_url,
        trigger_on_each_run=False,
        include_summary=True,
        include_results=True,
    )
    execute_project(project=project, run_async=run_async, command=command)
    return project

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

import time
from traceback import format_tb

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import create_project
from scanpipe.pipes import output
from scanpipe.pipes import purldb


class Command(AddInputCommandMixin, BaseCommand):
    help = "Create a ScanPipe project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--sleep",
            type=int,
            help="Number in seconds how long the loop should sleep for before polling.",
        )

    def handle(self, *args, **options):
        sleep = options["sleep"]

        while True:
            # 1. get download url from purldb
            response = purldb.get_next_job()
            if response:
                download_url, scannable_uri_uuid = response
            else:
                self.stdout.write("bad response")

            if not download_url or not scannable_uri_uuid:
                self.stdout.write("no new job")
            else:
                try:
                    # 2. create and run project
                    name = create_project_name(download_url, scannable_uri_uuid)
                    pipelines = ["scan_and_fingerprint_package"]
                    input_urls = [download_url]
                    project = create_project(
                        self,
                        name=name,
                        pipelines=pipelines,
                        input_urls=input_urls,
                    )

                    call_command(
                        "execute",
                        project=project,
                        stderr=self.stderr,
                        stdout=self.stdout,
                    )

                    # 3. poll project results
                    error_log = poll_run_status(
                        command=self,
                        project=project,
                        scannable_uri_uuid=scannable_uri_uuid,
                        sleep=sleep,
                    )

                    if error_log:
                        # send error response to purldb
                        purldb.update_status(
                            scannable_uri_uuid,
                            status="failed",
                            scan_log=error_log,
                        )
                    else:
                        # 4. get project results and send to purldb
                        scan_output_location = output.to_json(project)
                        purldb.send_results_to_purldb(
                            scannable_uri_uuid, scan_output_location
                        )

                except Exception as e:
                    traceback = ""
                    if hasattr(e, "__traceback__"):
                        traceback = "".join(format_tb(e.__traceback__))
                    purldb.update_status(
                        scannable_uri_uuid,
                        status="failed",
                        scan_log=traceback,
                    )

            time.sleep(sleep)


def create_project_name(download_url, scannable_uri_uuid):
    """Create a project name from `download_url` and `scannable_uri_uuid`"""
    if len(download_url) > 50:
        download_url = download_url[0:50]
    return f"{slugify(download_url)}-{scannable_uri_uuid[0:8]}"


def poll_run_status(command, project, sleep=10):
    """
    Poll the status of the first run of `project`. Return the log of the run if
    the run has stopped, failed, or gone stale, otherwise return an empty
    string.
    """
    run = project.runs.first()
    if purldb.poll_until_success(
        check=get_run_status,
        sleep=sleep,
        run=run
    ):
        return ""
    else:
        error_log = run.log
        command.stderr.write(error_log)
        return error_log


def get_run_status(run, **kwargs):
    """Refresh the values of `run` and return its status"""
    run.refresh_from_db()
    return run.status

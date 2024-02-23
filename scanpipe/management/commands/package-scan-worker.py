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

from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.core.management import call_command
from django.core.management.base import BaseCommand

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import extract_group_from_pipelines
from scanpipe.management.commands import validate_pipelines
from scanpipe.models import Project
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
                time.sleep(sleep)
                continue

            if not download_url or not scannable_uri_uuid:
                self.stdout.write("no new job")
                time.sleep(sleep)
                continue

            # 2. create and run project
            # TODO: create name based off of purl + uuid
            name = scannable_uri_uuid
            project = Project(name=name)
            try:
                project.full_clean(exclude=["slug"])
            except ValidationError as e:
                raise CommandError("\n".join(e.messages))

            # Run validation before creating the project in the database
            pipelines = ["scan_and_fingerprint_package"]
            pipelines_data = extract_group_from_pipelines(pipelines)
            pipelines_data = validate_pipelines(pipelines_data)
            project.save()
            self.project = project
            msg = f"Project {name} created with work directory {project.work_directory}"
            self.stdout.write(msg, self.style.SUCCESS)

            for pipeline_name, selected_groups in pipelines_data.items():
                self.project.add_pipeline(
                    pipeline_name, selected_groups=selected_groups
                )

            input_urls = [download_url]
            self.handle_input_urls(input_urls)

            call_command(
                "execute",
                project=project,
                stderr=self.stderr,
                stdout=self.stdout,
            )

            # 3. poll project results
            # TODO: consider refactoring `purldb.poll_until_success` to work here
            run = project.runs.first()
            status = run.Status
            error_log = ""
            scan_started = False
            while True:
                run_status = run.status
                if run_status == status.SUCCESS:
                    break

                if run_status in [
                    status.NOT_STARTED,
                    status.QUEUED,
                    status.RUNNING,
                ]:
                    if run_status == status.RUNNING and not scan_started:
                        scan_started = True
                        scan_project_url = project.get_absolute_url()
                        purldb.update_status(
                            scannable_uri_uuid,
                            status="in progress",
                            scan_project_url=scan_project_url,
                        )
                    time.sleep(sleep)
                    continue

                if run_status in [
                    status.FAILURE,
                    status.STOPPED,
                    status.STALE,
                ]:
                    error_log = run.log
                    self.stderr.write(run.log)
                    break

                time.sleep(sleep)

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
                purldb.send_results_to_purldb(scannable_uri_uuid, scan_output_location)

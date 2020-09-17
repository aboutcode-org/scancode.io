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

import shutil
import sys
from pathlib import Path

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from scanpipe.models import Project

scanpipe_app_config = apps.get_app_config("scanpipe")


class Command(BaseCommand):
    help = "Create a ScanPipe project."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Project name.")
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            default=list(),
            help=(
                "Pipelines locations to add on the project. "
                "The pipelines are added and ran respecting this provided order."
            ),
        )
        parser.add_argument(
            "--input",
            action="append",
            dest="inputs",
            default=list(),
            help="Input file locations to copy in the input/ work directory.",
        )

    def handle(self, *args, **options):
        name = options["name"]
        pipelines = options["pipelines"]
        inputs = options["inputs"]

        project = Project(name=name)
        try:
            project.full_clean()
        except ValidationError as e:
            self.stderr.write(str(e))
            sys.exit(1)

        for pipeline_location in pipelines:
            if not scanpipe_app_config.is_valid(pipeline_location):
                self.stderr.write(f"{pipeline_location} is not a valid pipeline")
                sys.exit(1)

        for input_location in inputs:
            input_path = Path(input_location)
            if not input_path.is_file():
                self.stderr.write(f"{input_location} not found or not a file.")
                sys.exit(1)

        project.save()
        msg = f"Project {name} created with work directory {project.work_directory}"
        self.stdout.write(self.style.SUCCESS(msg))

        for pipeline_location in pipelines:
            project.add_pipeline(pipeline_location)

        for input_location in inputs:
            shutil.copyfile(input_location, project.input_path)

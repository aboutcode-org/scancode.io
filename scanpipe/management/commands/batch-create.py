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

from datetime import datetime
from pathlib import Path

from django.core.management import CommandError
from django.core.management.base import BaseCommand

from scanpipe.management.commands import CreateProjectCommandMixin
from scanpipe.management.commands import PipelineCommandMixin
from scanpipe.pipes.output import safe_filename


class Command(CreateProjectCommandMixin, PipelineCommandMixin, BaseCommand):
    help = (
        "Processes files in the specified input directory by creating a project "
        "for each file. Each project is uniquely named using the filename and a "
        "timestamp. Supports specifying pipelines and asynchronous execution."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "input-directory",
            help=(
                "The path to the directory containing the input files to process. "
                "Ensure the directory exists and contains the files you want to use."
            ),
        )
        parser.add_argument(
            "--project-name-suffix",
            help=(
                "Optional custom suffix to append to project names. If not provided, "
                "a timestamp (in the format [YYMMDD_HHMMSS]) will be used."
            ),
        )

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        pipelines = options["pipelines"]
        notes = options["notes"]
        labels = options["labels"]
        execute = options["execute"]
        run_async = options["async"]
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        project_name_suffix = options.get("project_name_suffix") or timestamp
        input_directory = options["input-directory"]

        directory = Path(input_directory)
        if not directory.exists():
            raise CommandError("The directory does not exist.")

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                project_name = f"{safe_filename(file_path.name)} {project_name_suffix}"

                self.create_project(
                    name=project_name,
                    pipelines=pipelines,
                    input_files=[str(file_path)],
                    notes=notes,
                    labels=labels,
                    execute=execute,
                    run_async=run_async,
                )

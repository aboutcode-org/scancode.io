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

import csv
from datetime import datetime
from pathlib import Path

from django.core.management import CommandError
from django.core.management.base import BaseCommand

import requests

from scanpipe.management.commands import CreateProjectCommandMixin
from scanpipe.management.commands import PipelineCommandMixin
from scanpipe.pipes import fetch


class Command(CreateProjectCommandMixin, PipelineCommandMixin, BaseCommand):
    help = (
        "Processes files in the specified input directory by creating a project "
        "for each file. Each project is uniquely named using the filename and a "
        "timestamp. Supports specifying pipelines and asynchronous execution."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--input-directory",
            help=(
                "The path to the directory containing the input files to process. "
                "Ensure the directory exists and contains the files you want to use."
            ),
        )
        parser.add_argument(
            "--input-list",
            metavar="FILENAME.csv",
            help=(
                "Path to a CSV file with project names and input URLs. "
                "The first column must contain project names, and the second column "
                "should list comma-separated input URLs (e.g., Download URL, PURL, or "
                "Docker reference). "
                "In place of a local path, a download URL to the CSV file is supported."
            ),
        )
        parser.add_argument(
            "--project-name-suffix",
            help=(
                "Optional custom suffix to append to project names. If not provided, "
                "a timestamp (in the format [YYMMDD_HHMMSS]) will be used."
            ),
        )
        parser.add_argument(
            "--create-global-webhook",
            action="store_true",
            default=False,
            help=(
                "Create the global webhook for each project, "
                "if enabled in the settings. "
                "If not provided, the global webhook subscriptions are not created."
            ),
        )

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        self.created_project_count = 0

        input_directory = options["input_directory"]
        input_list = options["input_list"]

        if not (input_directory or input_list):
            raise CommandError(
                "You must provide either --input-directory or --input-list as input."
            )

        if input_directory:
            self.handle_input_directory(**options)

        if input_list:
            self.handle_input_list(**options)

        if self.verbosity > 0 and self.created_project_count:
            msg = f"{self.created_project_count} projects created."
            self.stdout.write(msg, self.style.SUCCESS)

    def handle_input_directory(self, **options):
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        project_name_suffix = options.get("project_name_suffix") or timestamp

        directory = Path(options["input_directory"])
        if not directory.exists():
            raise CommandError("The directory does not exist.")

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                project_name = f"{file_path.name} {project_name_suffix}"
                self.create_project(
                    name=project_name,
                    pipelines=options["pipelines"],
                    input_files=[str(file_path)],
                    notes=options["notes"],
                    labels=options["labels"],
                    execute=options["execute"],
                    run_async=options["async"],
                    create_global_webhook=options["create_global_webhook"],
                )
                self.created_project_count += 1

    def handle_input_list(self, **options):
        input_file = options["input_list"]

        if input_file.startswith("http"):
            try:
                download = fetch.fetch_http(input_file)
            except requests.exceptions.RequestException as e:
                raise CommandError(e)
            input_file = download.path

        input_file = Path(input_file)
        if not input_file.exists():
            raise CommandError(f"The {input_file} file does not exist.")

        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        project_name_suffix = options.get("project_name_suffix") or timestamp

        project_list = process_csv(input_file)
        for project_data in project_list:
            project_name = project_data["project_name"]
            project_name = f"{project_name} {project_name_suffix}"
            input_urls = project_data["input_urls"].split(",")
            self.create_project(
                name=project_name,
                pipelines=options["pipelines"],
                input_urls=input_urls,
                notes=options["notes"],
                labels=options["labels"],
                execute=options["execute"],
                run_async=options["async"],
                create_global_webhook=options["create_global_webhook"],
            )
            self.created_project_count += 1


def process_csv(file_path):
    required_headers = {"project_name", "input_urls"}

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        # Validate headers
        if not required_headers.issubset(reader.fieldnames):
            raise ValueError(
                f"The CSV file must contain the headers: {', '.join(required_headers)}"
            )

        project_list = [
            {"project_name": row["project_name"], "input_urls": row["input_urls"]}
            for row in reader
        ]
        return project_list

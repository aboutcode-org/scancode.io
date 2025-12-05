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

from collections import defaultdict
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils.crypto import get_random_string

from scanpipe.management.commands import extract_tag_from_input_file
from scanpipe.pipes.fetch import SCHEME_TO_FETCHER_MAPPING


class Command(BaseCommand):
    help = "Run a pipeline and print the results."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "pipelines",
            metavar="PIPELINE_NAME",
            nargs="+",
            help=(
                "One or more pipeline to run. "
                "The pipelines executed based on their given order. "
                'Groups can be provided using the "pipeline_name:option1,option2" '
                "syntax."
            ),
        )
        parser.add_argument(
            "input_location",
            help=(
                "Input location: file, directory, and URL supported."
                'Multiple values can be provided using the "input1,input2" syntax.'
            ),
        )
        parser.add_argument("--project", required=False, help="Project name.")
        parser.add_argument(
            "--format",
            default="json",
            choices=["json", "spdx", "cyclonedx", "attribution", "ort-package-list"],
            help="Specifies the output serialization format for the results.",
        )

    def handle(self, *args, **options):
        pipelines = options["pipelines"]
        input_location = options["input_location"]
        output_format = options["format"]
        # Generate a random name for the project if not provided
        project_name = options["project"] or get_random_string(10)

        create_project_options = {
            "pipeline": pipelines,
            "execute": True,
            "verbosity": 0,
            **self.get_input_options(input_location),
        }

        # Run the database migrations in case the database is not created or outdated.
        call_command("migrate", verbosity=0, interactive=False)
        # Create a project with proper inputs and execute the pipeline(s)
        call_command("create-project", project_name, **create_project_options)
        # Print the results for the specified format on stdout
        call_command("output", project=project_name, format=[output_format], print=True)

    @staticmethod
    def get_input_options(input_location):
        """
        Parse a comma-separated list of input locations and convert them into options
        for the `create-project` command.
        """
        input_options = defaultdict(list)

        for location in input_location.split(","):
            if location.startswith(tuple(SCHEME_TO_FETCHER_MAPPING.keys())):
                input_options["input_urls"].append(location)

            else:
                cleaned_location, _ = extract_tag_from_input_file(location)
                input_path = Path(cleaned_location)
                if not input_path.exists():
                    raise CommandError(f"{location} not found.")
                if input_path.is_file():
                    input_options["input_files"].append(location)
                else:
                    if input_options["copy_codebase"]:
                        raise CommandError(
                            "Only one codebase directory can be provided as input."
                        )
                    input_options["copy_codebase"] = location

        return input_options

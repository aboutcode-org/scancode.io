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

from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils.crypto import get_random_string

from scanpipe.management.commands import validate_pipeline


class Command(BaseCommand):
    help = "Run a pipeline and print the results."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("pipeline", help="Pipeline name to run.")
        parser.add_argument("codebase_location", help="Codebase location.")
        parser.add_argument("--project", required=False, help="Project name.")
        parser.add_argument(
            "--format",
            default="json",
            choices=["json", "spdx", "cyclonedx", "attribution"],
            help="Specifies the output serialization format for the results.",
        )

    def handle(self, *args, **options):
        pipeline = options["pipeline"]
        codebase_location = options["codebase_location"]
        output_format = options["format"]
        # Generate a random name for the project if not provided
        project_name = options.get("project") or get_random_string(10)

        validate_pipeline(pipeline)
        if not Path(codebase_location).exists():
            raise CommandError(f"{codebase_location} not found.")

        # Run the database migrations in case the database is not created or outdated.
        call_command("migrate", verbosity=0, interactive=False)
        call_command(
            "create-project",
            project_name,
            copy_codebase=codebase_location,
            pipeline=[pipeline],
            execute=True,
            verbosity=0,
        )
        call_command("output", project=project_name, format=[output_format], print=True)

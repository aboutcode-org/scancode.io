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

from django.core.management import CommandError
from django.core.management.base import BaseCommand

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import CreateProjectCommandMixin


class Command(CreateProjectCommandMixin, AddInputCommandMixin, BaseCommand):
    help = "Create a ScanPipe project."
    verbosity = 1

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("name", help="Project name.")
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            default=list(),
            help=(
                "Pipelines names to add to the project. "
                "The pipelines are added and executed based on their given order. "
                'Groups can be provided using the "pipeline_name:group1,group2" syntax.'
            ),
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the pipelines right after the project creation.",
        )
        parser.add_argument(
            "--notes",
            help="Optional notes about the project.",
        )

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        name = options["name"]
        pipelines = options["pipelines"]
        input_files = options["input_files"]
        input_urls = options["input_urls"]
        copy_from = options["copy_codebase"]
        notes = options["notes"]
        execute = options["execute"]
        run_async = options["async"]

        if execute and not pipelines:
            raise CommandError("The --execute option requires one or more pipelines.")

        self.create_project(
            name=name,
            pipelines=pipelines,
            input_files=input_files,
            input_urls=input_urls,
            copy_from=copy_from,
            notes=notes,
            execute=execute,
            run_async=run_async,
        )

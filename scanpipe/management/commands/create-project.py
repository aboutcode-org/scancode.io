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

from django.core.management.base import BaseCommand

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import CreateProjectCommandMixin
from scanpipe.management.commands import PipelineCommandMixin


class Command(
    CreateProjectCommandMixin, AddInputCommandMixin, PipelineCommandMixin, BaseCommand
):
    help = "Create a ScanPipe project."
    verbosity = 1

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("name", help="Project name.")

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        self.create_project(
            name=options["name"],
            pipelines=options["pipelines"],
            input_files=options["input_files"],
            input_urls=options["input_urls"],
            copy_from=options["copy_codebase"],
            notes=options["notes"],
            labels=options["labels"],
            execute=options["execute"],
            run_async=options["async"],
            create_global_webhook=not options["no_global_webhook"],
        )

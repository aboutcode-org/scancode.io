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

from pathlib import Path
from timeit import default_timer as timer

from django.core.management import CommandError
from django.core.management.base import BaseCommand

from aboutcode.pipeline import humanize_time
from scanpipe.models import Project
from scanpipe.pipes import filename_now
from scanpipe.pipes import output


class Command(BaseCommand):
    help = "Report of selected projects."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--output-directory",
            help=(
                "The path to the directory where the report file will be created. "
                "If not provided, the report file will be created in the current "
                "working directory."
            ),
        )
        parser.add_argument(
            "--model",
            required=True,
            choices=list(output.object_type_to_model_name.keys()),
            help="Specifies the model to include in the XLSX report.",
        )
        parser.add_argument(
            "--search",
            help="Select projects searching for the provided string in their name.",
        )
        parser.add_argument(
            "--label",
            action="append",
            dest="labels",
            default=list(),
            help=(
                "Filter projects by the provided label(s). Multiple labels can be "
                "provided by using this argument multiple times."
            ),
        )

    def handle(self, *args, **options):
        start_time = timer()
        self.verbosity = options["verbosity"]

        output_directory = options["output_directory"]
        labels = options["labels"]
        search = options["search"]
        model = options["model"]

        if not (labels or search):
            raise CommandError(
                "You must provide either --label or --search to select projects."
            )

        project_qs = Project.objects.all()
        if labels:
            project_qs = project_qs.filter(labels__name__in=labels)
        if search:
            project_qs = project_qs.filter(name__icontains=search)
        project_count = project_qs.count()

        if not project_count:
            raise CommandError("No projects found for the provided criteria.")

        if self.verbosity > 0:
            msg = f"{project_count} project(s) will be included in the report."
            self.stdout.write(msg, self.style.SUCCESS)

        filename = f"scancodeio-report-{filename_now()}.xlsx"
        if output_directory:
            output_file = Path(f"{output_directory}/{filename}")
        else:
            output_file = Path(filename)

        output_file = output.get_xlsx_report(project_qs, model, output_file)

        run_time = timer() - start_time
        if self.verbosity > 0:
            msg = f"Report generated at {output_file} in {humanize_time(run_time)}."
            self.stdout.write(msg, self.style.SUCCESS)

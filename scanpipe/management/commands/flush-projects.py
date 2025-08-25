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

import datetime
import sys

from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize
from django.utils import timezone

from scanpipe.models import Project


class Command(BaseCommand):
    help = (
        "Delete all project data and their related work directories created more than "
        "a specified number of days ago."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--retain-days",
            type=int,
            help=(
                "Optional. Specify the number of days to retain data. "
                "All data older than this number of days will be deleted. "
                "Defaults to 0 (delete all data)."
            ),
            default=0,
        )
        parser.add_argument(
            "--label",
            action="append",
            dest="labels",
            default=list(),
            help=(
                "Filter projects by the provided label. "
                "Multiple labels can be provided by using this argument multiple times."
            ),
        )
        parser.add_argument(
            "--pipeline",
            action="append",
            dest="pipelines",
            default=list(),
            help=(
                "Filter projects by the provided pipeline name. "
                "Multiple pipeline name can be provided by using this argument multiple"
                " times."
            ),
        )
        parser.add_argument(
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt the user for input of any kind.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Do not delete any projects; just print the ones that would be flushed."
            ),
        )

    def handle(self, *inputs, **options):
        verbosity = options["verbosity"]
        retain_days = options["retain_days"]
        labels = options["labels"]
        pipelines = options["pipelines"]
        dry_run = options["dry_run"]
        projects = Project.objects.order_by("-created_date").distinct()

        if retain_days:
            cutoff_date = timezone.now() - datetime.timedelta(days=retain_days)
            projects = projects.filter(created_date__lt=cutoff_date)

        if labels:
            projects = projects.filter(labels__name__in=labels)

        if pipelines:
            projects = projects.filter(runs__pipeline_name__in=pipelines)

        projects_count = projects.count()
        if projects_count == 0:
            if verbosity > 0:
                self.stdout.write("No projects to delete.")
            sys.exit(0)

        if dry_run:
            msg = self.style.WARNING(f"{projects_count} projects would be deleted:")
            self.stdout.write(msg)
            self.stdout.write("\n".join([f"- {project.name}" for project in projects]))
            return

        if options["interactive"]:
            confirm = input(
                f"You have requested the deletion of {projects_count} "
                f"project{pluralize(projects_count)}.\n"
                "This will IRREVERSIBLY DESTROY all data related to those projects.\n"
                "Are you sure you want to do this?\n"
                "Type 'yes' to continue, or 'no' to cancel: "
            )
            if confirm != "yes":
                if verbosity > 0:
                    self.stdout.write("Flush cancelled.")
                sys.exit(0)

        deletion_count = 0
        for project in projects:
            project.delete()
            deletion_count += 1

        if verbosity > 0:
            msg = (
                f"{deletion_count} project{pluralize(deletion_count)} and "
                f"{pluralize(deletion_count, 'its,their')} related data have been "
                f"removed."
            )
            self.stdout.write(msg, self.style.SUCCESS)

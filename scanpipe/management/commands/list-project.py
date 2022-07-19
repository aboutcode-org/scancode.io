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


from django.core.management.base import BaseCommand

from scanpipe.filters import ProjectFilterSet
from scanpipe.management.commands import RunStatusCommandMixin


class Command(BaseCommand, RunStatusCommandMixin):
    help = "Lists ScanPipe projects."
    separator = "-" * 50

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--search", help="Limit the projects list to this search results."
        )
        parser.add_argument(
            "--include-archived",
            action="store_true",
            dest="include_archived",
            help="Include archived projects.",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        filter_data = {"search": options["search"]}

        if options["include_archived"]:
            filter_data["is_archived"] = None

        projects = ProjectFilterSet(filter_data).qs
        project_count = len(projects)

        for index, project in enumerate(projects, start=1):
            self.display_status(project, verbosity)

            if index != project_count and verbosity > 1:
                self.stdout.write(f"\n{self.separator}\n\n")

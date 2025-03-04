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

from django.template.defaultfilters import pluralize

from scanpipe.management.commands import ProjectCommand
from scanpipe.management.commands import extract_group_from_pipelines
from scanpipe.management.commands import validate_pipelines


class Command(ProjectCommand):
    help = "Add pipelines to a project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "args",
            metavar="PIPELINE_NAME",
            nargs="+",
            help="One or more pipeline names.",
        )

    def handle(self, *pipelines, **options):
        super().handle(*pipelines, **options)

        pipelines_data = extract_group_from_pipelines(pipelines)
        pipelines_data = validate_pipelines(pipelines_data)

        for pipeline_name, selected_groups in pipelines_data.items():
            self.project.add_pipeline(pipeline_name, selected_groups=selected_groups)

        pipeline_names = pipelines_data.keys()

        if self.verbosity > 0:
            msg = (
                f"Pipeline{pluralize(pipeline_names)} {', '.join(pipeline_names)} "
                f"added to the project"
            )
            self.stdout.write(msg, self.style.SUCCESS)

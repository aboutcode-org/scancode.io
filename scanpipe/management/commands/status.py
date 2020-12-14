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

from scanpipe.management.commands import ProjectCommand
from scanpipe.management.commands import RunStatusCommandMixin
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import ProjectError
from scanpipe.pipes import count_group_by


class Command(ProjectCommand, RunStatusCommandMixin):
    help = "Display status information about the provided project."

    def handle(self, *args, **options):
        super().handle(*args, **options)

        message = [
            f"Project: {self.project.name}",
            f"Create date: {self.project.created_date.strftime('%b %d %Y %H:%M')}",
            f"Work directory: {self.project.work_directory}",
            "\n",
            "Database:",
        ]

        for model_class in [CodebaseResource, DiscoveredPackage, ProjectError]:
            queryset = model_class.objects.project(self.project)
            message.append(f" - {model_class.__name__}: {queryset.count()}")

            if model_class == CodebaseResource:
                status_summary = count_group_by(queryset, "status")
                for status, count in status_summary.items():
                    status = status or "(no status)"
                    message.append(f"   - {status}: {count}")

        runs = self.project.runs.all()
        if runs:
            message.append("\nPipelines:")
            for run in runs:
                status_code = self.get_run_status_code(run)
                message.append(f" [{status_code}] {run.pipeline}")

        for line in message:
            self.stdout.write(line)

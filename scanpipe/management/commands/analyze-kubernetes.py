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
from django.core.management.base import CommandError
from django.utils.text import slugify

from scanpipe.management.commands import CreateProjectCommandMixin
from scanpipe.management.commands import execute_project

# As a single project:
# scanpipe analyze-kubernetes kube-analysis-single --execute

# As multiple projects:
# scanpipe analyze-kubernetes kube-analysis-multi --multi --execute


def get_images():
    # kubectl get pods -o jsonpath="{.items[*].spec.containers[*].image}"
    # nginx:latest redis:alpine
    images = ["nginx:latest", "redis:alpine"]
    return images


class Command(CreateProjectCommandMixin, BaseCommand):
    help = "Analyze all images of a Kubernetes cluster."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("name", help="Project name.")
        parser.add_argument(
            "--multi",
            action="store_true",
            help="Create multiple projects instead of a single one.",
        )
        parser.add_argument(
            "--find-vulnerabilities",
            action="store_true",
            help="Run the find_vulnerabilities pipeline during the analysis.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Execute the pipelines right after the project creation.",
        )

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        project_name = options["name"]
        pipelines = ["analyze_docker_image"]
        create_multiple_projects = options["multi"]
        execute = options["execute"]
        run_async = options["async"]
        labels = options["labels"]
        notes = options["notes"]
        created_projects = []

        if options["find_vulnerabilities"]:
            pipelines.append("find_vulnerabilities")

        images = get_images()

        create_project_options = {
            "pipelines": pipelines,
            "notes": notes,
            "labels": labels,
        }

        if create_multiple_projects:
            labels.append(f"k8s-{slugify(project_name)}")
            for reference in images:
                project = self.create_project(
                    **create_project_options,
                    name=f"{project_name}: {reference}",
                    input_urls=[f"docker://{reference}"],
                )
                created_projects.append(project)

        else:
            project = self.create_project(
                **create_project_options,
                name=project_name,
                input_urls=[f"docker://{reference}" for reference in images],
            )
            created_projects.append(project)

        if execute:
            for project in created_projects:
                try:
                    execute_project(project=project, run_async=run_async, command=self)
                except CommandError as error:
                    self.stderr.write(str(error))

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

import subprocess
import sys

from django.core.management import CommandError
from django.core.management.base import BaseCommand

from scanpipe.management.commands import scanpipe_app_config
from scanpipe.pipelines import PipelineGraph
from scanpipe.pipelines import get_pipeline_class
from scanpipe.pipelines import get_pipeline_doc


def is_graphviz_installed():
    exitcode, _ = subprocess.getstatusoutput("which dot")
    if exitcode == 0:
        return True
    return False


class Command(BaseCommand):
    help = "Generate pipeline graph with Graphviz."

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="pipelines",
            nargs="*",
            help="One or more pipeline locations.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="Display a list of all available pipelines.",
        )
        parser.add_argument("--output", help="Output directory location.")

    def handle(self, *pipelines, **options):
        if options["list"]:
            for location, _ in scanpipe_app_config.pipelines:
                self.stdout.write("- " + self.style.SUCCESS(location))
                self.stdout.write(get_pipeline_doc(location), ending="\n\n")
            sys.exit(0)

        if not is_graphviz_installed():
            raise CommandError("Graphviz is not installed.")

        if not pipelines:
            self.stderr.write(self.style.ERROR("The pipelines argument is required."))
            sys.exit(1)

        outputs = []
        for pipeline_location in pipelines:
            try:
                pipeline_class = get_pipeline_class(pipeline_location)
            except ModuleNotFoundError:
                self.stderr.write(
                    self.style.ERROR(f"{pipeline_location} is not valid.")
                )
                sys.exit(1)
            pipeline_graph = PipelineGraph(pipeline_class)
            outputs.append(self.generate_graph(pipeline_graph, options.get("output")))

        separator = "\n - "
        msg = f"Graph(s) generated:{separator}" + separator.join(outputs)
        self.stdout.write(self.style.SUCCESS(msg))

    @staticmethod
    def generate_graph(pipeline_graph, output_directory):
        output_dot = pipeline_graph.output_dot(simplify=True)
        output_location = f"{pipeline_graph.name}.png"
        if output_directory:
            output_location = f"{output_directory}/{output_location}"
        dot_cmd = f'echo "{output_dot}" | dot -Tpng -o {output_location}'
        subprocess.getoutput(dot_cmd)
        return output_location

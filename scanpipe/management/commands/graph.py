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

from scanpipe.management.commands import indent
from scanpipe.management.commands import scanpipe_app_config
from scanpipe.pipelines import get_pipeline_class
from scanpipe.pipelines import get_pipeline_doc


def is_graphviz_installed():
    exitcode = subprocess.getstatusoutput("which dot")[0]
    if exitcode == 0:
        return True
    return False


def pipeline_graph_dot(pipeline_class, fontname="Helvetica", shape="record"):
    """
    Return the pipeline graph as DOT format compatible with Graphviz.
    """
    dot_output = [f"digraph {pipeline_class.__name__} {{", "rankdir=TB;"]

    edges = []
    nodes = []
    steps = pipeline_class.steps
    step_count = len(steps)

    for index, step in enumerate(steps, start=1):
        step_name = step.__name__
        edges.append(
            f'"{step_name}"'
            f'[label=<<b>{step_name}</b>> fontname="{fontname}" shape="{shape}"];'
        )
        if index < step_count:
            next_step = steps[index]
            nodes.append(f"{step_name} -> {next_step.__name__};")

    dot_output.extend(edges)
    dot_output.extend(nodes)
    dot_output.append("}")
    return "\n".join(dot_output)


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
                pipeline_doc = get_pipeline_doc(location)
                self.stdout.write(indent(pipeline_doc, by=2), ending="\n\n")
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

            output_directory = options.get("output")
            outputs.append(self.generate_graph_png(pipeline_class, output_directory))

        separator = "\n - "
        msg = f"Graph(s) generated:{separator}" + separator.join(outputs)
        self.stdout.write(self.style.SUCCESS(msg))

    @staticmethod
    def generate_graph_png(pipeline_class, output_directory):
        output_dot = pipeline_graph_dot(pipeline_class)
        output_location = f"{pipeline_class.__name__}.png"
        if output_directory:
            output_location = f"{output_directory}/{output_location}"
        dot_cmd = f'echo "{output_dot}" | dot -Tpng -o {output_location}'
        subprocess.getoutput(dot_cmd)
        return output_location

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
from textwrap import indent

from django.apps import apps
from django.core.management import CommandError
from django.core.management.base import BaseCommand

scanpipe_app = apps.get_app_config("scanpipe")


def is_graphviz_installed():
    exitcode = subprocess.getstatusoutput("which dot")[0]
    if exitcode == 0:
        return True
    return False


def pipeline_graph_dot(pipeline_name, pipeline_class):
    """Return the pipeline graph as DOT format compatible with Graphviz."""
    fontname = "Helvetica"
    shape = "record"
    dot_output = [f"digraph {pipeline_name} {{", "rankdir=TB;"]

    edges = []
    nodes = []
    steps = pipeline_class.get_steps()
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
            metavar="PIPELINE_NAME",
            nargs="*",
            help="One or more pipeline names.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="Display a list of all available pipelines.",
        )
        parser.add_argument("--output", help="Output directory location.")

    def handle(self, *pipeline_names, **options):
        if options["list"]:
            for pipeline_name, pipeline_class in scanpipe_app.pipelines.items():
                self.stdout.write("- " + pipeline_name, self.style.SUCCESS)
                self.stdout.write(indent(pipeline_class.get_doc(), "  "), ending="\n\n")
            sys.exit(0)

        if not is_graphviz_installed():
            raise CommandError("Graphviz is not installed.")

        if not pipeline_names:
            raise CommandError("The pipeline-names argument is required.")

        outputs = []
        for pipeline_name in pipeline_names:
            pipeline_class = scanpipe_app.pipelines.get(pipeline_name)
            if not pipeline_class:
                raise CommandError(f"{pipeline_name} is not valid.")

            output_directory = options.get("output")
            outputs.append(
                self.generate_graph_png(pipeline_name, pipeline_class, output_directory)
            )

        separator = "\n - "
        msg = f"Graph(s) generated:{separator}" + separator.join(outputs)
        self.stdout.write(msg, self.style.SUCCESS)

    @staticmethod
    def generate_graph_png(pipeline_name, pipeline_class, output_directory):
        output_location = f"{pipeline_name}.png"
        if output_directory:
            output_location = f"{output_directory}/{output_location}"

        output_dot = pipeline_graph_dot(pipeline_name, pipeline_class)
        dot_cmd = f'echo "{output_dot}" | dot -Tpng -o {output_location}'
        subprocess.getoutput(dot_cmd)

        return output_location

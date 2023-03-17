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

from django.core.management.base import CommandError

from scanpipe.management.commands import ProjectCommand
from scanpipe.pipes import output


class Command(ProjectCommand):
    help = "Output project results as JSON, XLSX, SPDX, and CycloneDX."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--format",
            default="json",
            choices=["json", "csv", "xlsx", "spdx", "cyclonedx"],
            help="Specifies the output serialization format for the results.",
        )
        parser.add_argument(
            "--print",
            action="store_true",
            help="Print the output to stdout.",
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)
        print_to_stdout = options["print"]
        format = options["format"]

        output_function = {
            "json": output.to_json,
            "csv": output.to_csv,
            "xlsx": output.to_xlsx,
            "spdx": output.to_spdx,
            "cyclonedx": output.to_cyclonedx,
        }.get(format)

        if print_to_stdout and format in ["xlsx", "csv"]:
            raise CommandError("--print is not compatible with xlsx and csv formats.")

        output_file = output_function(self.project)

        if isinstance(output_file, list):
            output_file = "\n".join([str(path) for path in output_file])

        if options["print"]:
            self.stdout.write(output_file.read_text())
        else:
            self.stdout.write(str(output_file), self.style.SUCCESS)

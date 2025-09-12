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

from django.core.management.base import CommandError

from scanpipe.management.commands import ProjectCommand
from scanpipe.pipes import output

SUPPORTED_FORMATS = [
    "json",
    "csv",
    "xlsx",
    "attribution",
    "spdx",
    "cyclonedx",
    "ort-package-list",
]


class Command(ProjectCommand):
    help = "Output project results as JSON, XLSX, Attribution, SPDX, and CycloneDX."
    print_to_stdout = False

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--format",
            default=["json"],
            nargs="+",
            metavar=f"{{{','.join(SUPPORTED_FORMATS)}}}",
            help=(
                "Specifies the output format for the results. "
                "To specify a CycloneDX spec version (default to latest), use the "
                'syntax "cyclonedx:VERSION", e.g. "cyclonedx:1.5".'
            ),
        )
        parser.add_argument(
            "--print",
            action="store_true",
            help="Print the output to stdout.",
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)
        self.print_to_stdout = options["print"]
        formats = options["format"]

        if self.print_to_stdout and len(formats) > 1:
            raise CommandError(
                "--print cannot be used when multiple formats are provided."
            )

        if self.print_to_stdout and ("xlsx" in formats or "csv" in formats):
            raise CommandError("--print is not compatible with xlsx and csv formats.")

        for output_format in formats:
            self.handle_output(output_format)

    def handle_output(self, output_format):
        output_kwargs = {}
        if ":" in output_format:
            output_format, version = output_format.split(":", maxsplit=1)
            if output_format not in ["cyclonedx", "spdx"]:
                raise CommandError(
                    'The ":" version syntax is only supported for the cyclonedx format.'
                )
            output_kwargs["version"] = version

        output_function = {
            "json": output.to_json,
            "csv": output.to_csv,
            "xlsx": output.to_xlsx,
            "spdx": output.to_spdx,
            "cyclonedx": output.to_cyclonedx,
            "attribution": output.to_attribution,
            "ort-package-list": output.to_ort_package_list_yml,
        }.get(output_format)

        if not output_function:
            msg = f"Error: argument --format: invalid choice: '{output_format}'"
            raise CommandError(msg)

        try:
            output_file = output_function(self.project, **output_kwargs)
        except Exception as e:
            raise CommandError(e)

        if isinstance(output_file, list):
            output_file = "\n".join([str(path) for path in output_file])

        if self.print_to_stdout:
            self.stdout.write(output_file.read_text())
        elif self.verbosity > 0:
            self.stdout.write(str(output_file), self.style.SUCCESS)

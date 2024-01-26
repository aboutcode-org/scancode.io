#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.core.management.base import CommandError

from scanpipe.management.commands import ProjectCommand
from scanpipe.pipes import output


class Command(ProjectCommand):
    help = "Output project results as JSON, XLSX, SPDX, and CycloneDX."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--format",
            default=["json"],
            nargs="+",
            choices=["json", "csv", "xlsx", "spdx", "cyclonedx", "attribution"],
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
        formats = options["format"]

        if print_to_stdout and len(formats) > 1:
            raise CommandError(
                "--print cannot be used when multiple formats are provided."
            )

        if print_to_stdout and ("xlsx" in formats or "csv" in formats):
            raise CommandError("--print is not compatible with xlsx and csv formats.")

        for format_ in formats:
            output_function = {
                "json": output.to_json,
                "csv": output.to_csv,
                "xlsx": output.to_xlsx,
                "spdx": output.to_spdx,
                "cyclonedx": output.to_cyclonedx,
                "attribution": output.to_attribution,
            }.get(format_)

            output_file = output_function(self.project)

            if isinstance(output_file, list):
                output_file = "\n".join([str(path) for path in output_file])

            if options["print"]:
                self.stdout.write(output_file.read_text())
            else:
                self.stdout.write(str(output_file), self.style.SUCCESS)

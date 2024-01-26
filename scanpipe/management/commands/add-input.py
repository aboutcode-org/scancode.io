#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.core.management import CommandError

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import ProjectCommand
from scanpipe.management.commands import validate_copy_from


class Command(AddInputCommandMixin, ProjectCommand):
    help = "Add input files in a project work directory."

    def handle(self, *args, **options):
        super().handle(*args, **options)
        inputs_files = options["inputs_files"]
        input_urls = options["input_urls"]
        copy_from = options["copy_codebase"]

        if not self.project.can_change_inputs:
            raise CommandError(
                "Cannot add inputs once a pipeline has started to execute on a project."
            )

        if not (inputs_files or input_urls or copy_from):
            raise CommandError(
                "Provide inputs with the --input-file, --input-url, or --copy-codebase"
            )

        if inputs_files:
            self.validate_input_files(inputs_files)
            self.handle_input_files(inputs_files)

        if input_urls:
            self.handle_input_urls(input_urls)

        if copy_from:
            validate_copy_from(copy_from)
            self.handle_copy_codebase(copy_from)

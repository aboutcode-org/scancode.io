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

from django.core.management import CommandError

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import ProjectCommand
from scanpipe.management.commands import validate_copy_from


class Command(AddInputCommandMixin, ProjectCommand):
    help = "Add input files in a project work directory."

    def handle(self, *args, **options):
        super().handle(*args, **options)
        input_files = options["input_files"]
        input_urls = options["input_urls"]
        copy_from = options["copy_codebase"]

        if not self.project.can_change_inputs:
            raise CommandError(
                "Cannot add inputs once a pipeline has started to execute on a project."
            )

        if not (input_files or input_urls or copy_from):
            raise CommandError(
                "Provide inputs with the --input-file, --input-url, or --copy-codebase"
            )

        if input_files:
            input_files_data = self.extract_tag_from_input_files(input_files)
            self.validate_input_files(input_files=input_files_data.keys())
            self.handle_input_files(input_files_data)

        if input_urls:
            self.handle_input_urls(input_urls)

        if copy_from:
            validate_copy_from(copy_from)
            self.handle_copy_codebase(copy_from)

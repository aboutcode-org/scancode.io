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

from django.core.management import CommandError

from scanpipe.management.commands import AddInputCommandMixin
from scanpipe.management.commands import ProjectCommand


class Command(AddInputCommandMixin, ProjectCommand):
    help = "Add input files in a project work directory."

    def handle(self, *args, **options):
        super().handle(*args, **options)
        inputs_files = options["inputs_files"]
        input_urls = options["input_urls"]

        if not (inputs_files or input_urls):
            raise CommandError(f"Provide inputs with the --input-file or --input-url")

        if inputs_files:
            self.validate_input_files(inputs_files)
            self.handle_input_files(inputs_files)

        if input_urls:
            self.handle_input_urls(input_urls)

    # def handle_input_files(self, inputs_files):
    #     """
    #     Copy provided `inputs_files` to the project `input` directory.
    #     """
    #     copied = []
    #     for file_location in inputs_files:
    #         self.project.copy_input_from(file_location)
    #         filename = Path(file_location).name
    #         copied.append(filename)
    #         self.project.add_input_source(filename, source="uploaded")
    #
    #     msg = "File(s) copied to the project inputs directory:"
    #     self.stdout.write(self.style.SUCCESS(msg))
    #     msg = "\n".join(["- " + filename for filename in copied])
    #     self.stdout.write(msg)
    #
    # @staticmethod
    # def validate_input_files(inputs_files):
    #     """
    #     Raise an error if one of the provided `inputs_files` is not an existing file.
    #     """
    #     for file_location in inputs_files:
    #         file_path = Path(file_location)
    #         if not file_path.is_file():
    #             raise CommandError(f"{file_location} not found or not a file")
    #
    # def handle_input_urls(self, input_urls):
    #     """
    #     Fetch provided `input_urls` and store to the project `input` directory.
    #     """
    #     downloads = []
    #     errors = []
    #
    #     for url in input_urls:
    #         try:
    #             downloaded = download(url)
    #             self.project.move_input_from(downloaded.file_path)
    #             self.project.add_input_source(downloaded.filename, downloaded.uri)
    #             downloads.append(downloaded)
    #         except Exception:
    #             errors.append(url)
    #
    #     if downloads:
    #         msg = "File(s) downloaded to the project inputs directory:"
    #         self.stdout.write(self.style.SUCCESS(msg))
    #         msg = "\n".join(["- " + downloaded.filename for downloaded in downloads])
    #         self.stdout.write(msg)
    #
    #     if errors:
    #         self.stdout.write(self.style.ERROR("Could not fetch URL(s):"))
    #         msg = "\n".join(["- " + url for url in errors])
    #         self.stdout.write(self.style.ERROR(msg))

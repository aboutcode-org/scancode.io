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

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import rootfs
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_inputs


class ScanCodebase(Pipeline):
    """
    Scan a codebase with ScanCode-toolkit.

    If the codebase consists of several packages and dependencies, it will try to
    resolve and scan those too.

    Input files are copied to the project's codebase/ directory and are extracted
    in place before running the scan.
    Alternatively, the code can be manually copied to the project codebase/
    directory.
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.tag_empty_files,
            cls.scan_for_application_packages,
            cls.scan_for_files,
        )

    # Set to True to extract recursively nested archives in archives.
    extract_recursively = False

    def copy_inputs_to_codebase_directory(self):
        """
        Copy input files to the project's codebase/ directory.
        The code can also be copied there prior to running the Pipeline.
        """
        copy_inputs(self.project.inputs(), self.project.codebase_path)

    def extract_archives(self):
        """Extract archives with extractcode."""
        extract_errors = scancode.extract_archives(
            location=self.project.codebase_path,
            recurse=self.extract_recursively,
        )

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        for resource_path in self.project.walk_codebase_path():
            pipes.make_codebase_resource(
                project=self.project,
                location=str(resource_path),
            )

    def tag_empty_files(self):
        """Flag empty files."""
        rootfs.tag_empty_codebase_resources(self.project)

    def scan_for_application_packages(self):
        """Scan unknown resources for packages information."""
        scancode.scan_for_application_packages(self.project)

    def scan_for_files(self):
        """Scan unknown resources for copyrights, licenses, emails, and urls."""
        scancode.scan_for_files(self.project)

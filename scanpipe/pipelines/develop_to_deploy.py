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
from scanpipe.pipes import d2d
from scanpipe.pipes import scancode
from scanpipe.pipes.scancode import extract_archives


class DevelopToDeploy(Pipeline):
    """Relate develop and deploy code tree."""

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.extract_inputs_to_codebase_directory,
            cls.get_inputs,
            cls.extract_archive_to_codebase_directory,
            cls.collect_and_create_codebase_resources,
            cls.checksum_match,
            cls.java_to_class_match,
            cls.path_match,
        )

    def get_inputs(self):
        """Locate the `from` and `to` archives."""
        from_file = list(self.project.inputs("from*"))
        to_file = list(self.project.inputs("to*"))

        if len(from_file) != 1:
            raise
        if len(to_file) != 1:
            raise

        self.from_file = from_file[0]
        self.to_file = to_file[0]

        self.from_path = self.project.codebase_path / "from"
        self.to_path = self.project.codebase_path / "to"

    def extract_inputs_to_codebase_directory(self):
        """Extract input files to the project's codebase/ directory."""
        errors = []
        errors += scancode.extract_archive(self.from_file, self.from_path)
        errors += scancode.extract_archive(self.to_file, self.to_path)

        if errors:
            self.add_error("\n".join(errors))

    def extract_archive_to_codebase_directory(self):
        """Extract from* and to* archives in place with extractcode."""
        extract_errors = extract_archives(self.project.codebase_path)

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        for resource_path in self.project.walk_codebase_path():
            pipes.make_codebase_resource(project=self.project, location=resource_path)

    def checksum_match(self):
        """Match using SHA1 checksum."""
        d2d.checksum_match(project=self.project, checksum_field="sha1")

    def java_to_class_match(self):
        """Match a .java source to its compiled .class"""
        d2d.java_to_class_match(project=self.project)
        d2d.java_to_inner_class_match(project=self.project)

    def path_match(self):
        """Match using path similarities."""
        d2d.path_match(project=self.project)

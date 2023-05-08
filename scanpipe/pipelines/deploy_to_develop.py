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

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import d2d
from scanpipe.pipes import flag
from scanpipe.pipes import purldb
from scanpipe.pipes import scancode
from scanpipe.pipes.scancode import extract_archives


class DeployToDevelop(Pipeline):
    """
    Relate deploy and develop code trees.

    This pipeline is expecting 2 archive files with "from-" and "to-" filename
    prefixes as inputs:
    - "from-[FILENAME]" archive containing the development source code
    - "to-[FILENAME]" archive containing the deployment compiled code
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.extract_inputs_to_codebase_directory,
            cls.extract_archives_in_place,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_and_ignored_files,
            cls.checksum_map,
            cls.find_java_packages,
            cls.java_to_class_map,
            cls.jar_to_source_map,
            cls.purldb_match,
            cls.path_map,
            cls.flag_mapped_resources_and_ignored_directories,
        )

    extract_recursively = True
    purldb_match_extensions = [".jar", ".war", ".zip"]

    def get_inputs(self):
        """Locate the `from` and `to` archives."""
        self.from_file, self.to_file = d2d.get_inputs(self.project)

        self.from_path = self.project.codebase_path / d2d.FROM
        self.to_path = self.project.codebase_path / d2d.TO

    def extract_inputs_to_codebase_directory(self):
        """Extract input files to the project's codebase/ directory."""
        errors = []
        errors += scancode.extract_archive(self.from_file, self.from_path)
        errors += scancode.extract_archive(self.to_file, self.to_path)

        if errors:
            self.add_error("\n".join(errors))

    def extract_archives_in_place(self):
        """Extract recursively from* and to* archives in place with extractcode."""
        extract_errors = extract_archives(
            self.project.codebase_path,
            recurse=self.extract_recursively,
        )

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        d2d.collect_and_create_codebase_resources(self.project)

    def flag_empty_and_ignored_files(self):
        """Flag empty and ignored files using names and extensions."""
        flag.flag_empty_codebase_resources(self.project)
        flag.flag_ignored_filenames(self.project, filenames=d2d.IGNORE_FILENAMES)
        flag.flag_ignored_extensions(self.project, extensions=d2d.IGNORE_EXTENSIONS)
        flag.flag_ignored_paths(self.project, paths=d2d.IGNORE_PATHS)

    def checksum_map(self):
        """Map using SHA1 checksum."""
        d2d.checksum_map(project=self.project, checksum_field="sha1", logger=self.log)

    def find_java_packages(self):
        """Find the java package of the .java source files."""
        d2d.find_java_packages(self.project, logger=self.log)

    def java_to_class_map(self):
        """Map a .class compiled file to its .java source."""
        d2d.java_to_class_map(project=self.project, logger=self.log)

    def jar_to_source_map(self):
        """Map a .class compiled file to its .java source."""
        d2d.jar_to_source_map(project=self.project, logger=self.log)

    def purldb_match(self):
        """Match selected files by extension in PurlDB."""
        if not purldb.is_available():
            self.log("PurlDB is not available. Skipping.")
            return

        d2d.purldb_match(
            project=self.project,
            extensions=self.purldb_match_extensions,
            logger=self.log,
        )

    def path_map(self):
        """Map using path similarities."""
        d2d.path_map(project=self.project, logger=self.log)

    def flag_mapped_resources_and_ignored_directories(self):
        """Flag all codebase resources that were mapped during the pipeline."""
        flag.flag_mapped_resources(self.project)
        flag.flag_ignored_directories(self.project)

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
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.map_about_files,
            cls.map_checksum,
            cls.find_java_packages,
            cls.map_java_to_class,
            cls.map_jar_to_source,
            cls.map_javascript,
            cls.match_purldb,
            cls.map_javascript_post_purldb_match,
            cls.map_javascript_path,
            cls.map_path,
            cls.flag_mapped_resources_and_ignored_directories,
            cls.scan_mapped_from_for_files,
        )

    purldb_package_extensions = [".jar", ".war", ".zip"]
    purldb_resource_extensions = [
        ".map",
        ".js",
        ".mjs",
        ".ts",
        ".d.ts",
        ".jsx",
        ".tsx",
        ".css",
        ".scss",
        ".less",
        ".sass",
        ".soy",
    ]

    def get_inputs(self):
        """Locate the ``from`` and ``to`` input files."""
        self.from_files, self.to_files = d2d.get_inputs(self.project)

    def extract_inputs_to_codebase_directory(self):
        """Extract input files to the project's codebase/ directory."""
        inputs_with_codebase_path_destination = [
            (self.from_files, self.project.codebase_path / d2d.FROM),
            (self.to_files, self.project.codebase_path / d2d.TO),
        ]

        errors = []
        for input_files, codebase_path in inputs_with_codebase_path_destination:
            for input_file_path in input_files:
                errors += scancode.extract_archive(input_file_path, codebase_path)

        if errors:
            self.add_error("\n".join(errors))

    def extract_archives_in_place(self):
        """Extract recursively from* and to* archives in place with extractcode."""
        extract_errors = scancode.extract_archives(
            self.project.codebase_path,
            recurse=self.env.get("extract_recursively", True),
        )

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        d2d.collect_and_create_codebase_resources(self.project)

    def map_about_files(self):
        """Map ``from/`` .ABOUT files to their related ``to/`` resources."""
        d2d.map_about_files(project=self.project, logger=self.log)

    def map_checksum(self):
        """Map using SHA1 checksum."""
        d2d.map_checksum(project=self.project, checksum_field="sha1", logger=self.log)

    def find_java_packages(self):
        """Find the java package of the .java source files."""
        d2d.find_java_packages(self.project, logger=self.log)

    def map_java_to_class(self):
        """Map a .class compiled file to its .java source."""
        d2d.map_java_to_class(project=self.project, logger=self.log)

    def map_jar_to_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_source(project=self.project, logger=self.log)

    def map_javascript(self):
        """
        Map a packed or minified JavaScript, TypeScript, CSS and SCSS
        to its source.
        """
        d2d.map_javascript(project=self.project, logger=self.log)

    def match_purldb(self):
        """Match selected files by extension in PurlDB."""
        if not purldb.is_available():
            self.log("PurlDB is not available. Skipping.")
            return

        d2d.match_purldb(
            project=self.project,
            extensions=self.purldb_package_extensions,
            matcher_func=d2d.match_purldb_package,
            logger=self.log,
        )

        d2d.match_purldb(
            project=self.project,
            extensions=self.purldb_resource_extensions,
            matcher_func=d2d.match_purldb_resource,
            logger=self.log,
        )

    def map_javascript_post_purldb_match(self):
        """Map minified javascript file based on existing PurlDB match."""
        d2d.map_javascript_post_purldb_match(project=self.project, logger=self.log)

    def map_javascript_path(self):
        """Map javascript file based on path."""
        d2d.map_javascript_path(project=self.project, logger=self.log)

    def map_path(self):
        """Map using path similarities."""
        d2d.map_path(project=self.project, logger=self.log)

    def flag_mapped_resources_and_ignored_directories(self):
        """Flag all codebase resources that were mapped during the pipeline."""
        flag.flag_mapped_resources(self.project)
        flag.flag_ignored_directories(self.project)

    def scan_mapped_from_for_files(self):
        """Scan mapped ``from/`` files for copyrights, licenses, emails, and urls."""
        resource_qs = self.project.codebaseresources
        mapped_from_files = resource_qs.from_codebase().files().has_relation()
        scancode.scan_for_files(self.project, mapped_from_files)

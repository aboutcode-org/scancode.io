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

from aboutcode.pipeline import optional_step
from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import d2d
from scanpipe.pipes import d2d_config
from scanpipe.pipes import flag
from scanpipe.pipes import input
from scanpipe.pipes import jvm
from scanpipe.pipes import matchcode
from scanpipe.pipes import purldb
from scanpipe.pipes import scancode


class DeployToDevelop(Pipeline):
    """
    Establish relationships between two code trees: deployment and development.

    This pipeline requires a minimum of two archive files, each properly tagged with:

    - **from** for archives containing the development source code.
    - **to** for archives containing the deployment compiled code.

    When using download URLs as inputs, the "from" and "to" tags can be
    provided by adding a "#from" or "#to" fragment at the end of the download URLs.

    When uploading local files:

    - **User Interface:** Use the "Edit flag" link in the "Inputs" panel of the Project
      details view.
    - **REST API:** Utilize the "upload_file_tag" field in addition to the
      "upload_file".
    - **Command Line Interface:** Tag uploaded files using the "filename:tag" syntax,
      for example, ``--input-file path/filename:tag``.
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.extract_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.fingerprint_codebase_directories,
            cls.flag_empty_files,
            cls.flag_whitespace_files,
            cls.flag_ignored_resources,
            cls.load_ecosystem_config,
            cls.map_ruby,
            cls.map_about_files,
            cls.map_checksum,
            cls.match_archives_to_purldb,
            cls.find_java_packages,
            cls.map_java_to_class,
            cls.map_jar_to_java_source,
            cls.find_scala_packages,
            cls.map_scala_to_class,
            cls.map_jar_to_scala_source,
            cls.find_kotlin_packages,
            cls.map_kotlin_to_class,
            cls.map_jar_to_kotlin_source,
            cls.find_grammar_packages,
            cls.map_grammar_to_class,
            cls.map_jar_to_grammar_source,
            cls.find_groovy_packages,
            cls.map_groovy_to_class,
            cls.map_jar_to_groovy_source,
            cls.find_aspectj_packages,
            cls.map_aspectj_to_class,
            cls.map_jar_to_aspectj_source,
            cls.find_clojure_packages,
            cls.map_clojure_to_class,
            cls.map_jar_to_clojure_source,
            cls.find_xtend_packages,
            cls.map_xtend_to_class,
            cls.map_javascript,
            cls.map_javascript_symbols,
            cls.map_javascript_strings,
            cls.get_symbols_from_binaries,
            cls.map_elf,
            cls.map_macho,
            cls.map_winpe,
            cls.map_go,
            cls.map_rust,
            cls.map_python,
            cls.match_directories_to_purldb,
            cls.match_resources_to_purldb,
            cls.map_javascript_post_purldb_match,
            cls.map_javascript_path,
            cls.map_javascript_colocation,
            cls.map_thirdparty_npm_packages,
            cls.map_path,
            cls.flag_mapped_resources_archives_and_ignored_directories,
            cls.perform_house_keeping_tasks,
            cls.match_purldb_resources_post_process,
            cls.remove_packages_without_resources,
            cls.scan_ignored_to_files,
            cls.scan_unmapped_to_files,
            cls.scan_mapped_from_for_files,
            cls.collect_and_create_license_detections,
            cls.flag_deployed_from_resources_with_missing_license,
            cls.create_local_files_packages,
        )

    def get_inputs(self):
        """Locate the ``from`` and ``to`` input files."""
        self.from_files, self.to_files = d2d.get_inputs(self.project)

    def extract_inputs_to_codebase_directory(self):
        """Extract input files to the project's codebase/ directory."""
        inputs_with_codebase_path_destination = [
            (self.from_files, self.project.codebase_path / d2d.FROM),
            (self.to_files, self.project.codebase_path / d2d.TO),
        ]

        for input_files, codebase_path in inputs_with_codebase_path_destination:
            for input_file_path in input_files:
                if input.is_archive(input_file_path):
                    self.extract_archive(input_file_path, codebase_path)
                else:
                    input.copy_input(input_file_path, codebase_path)

        # Reload the project env post-extraction as the scancode-config.yml file
        # may be located in one of the extracted archives.
        self.env = self.project.get_env()

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        pipes.collect_and_create_codebase_resources(self.project)

    def fingerprint_codebase_directories(self):
        """Compute directory fingerprints for matching"""
        matchcode.fingerprint_codebase_directories(self.project, to_codebase_only=True)

    def flag_whitespace_files(self):
        """Flag whitespace files with size less than or equal to 100 byte as ignored."""
        d2d.flag_whitespace_files(project=self.project)

    def load_ecosystem_config(self):
        """Load ecosystem specific configurations for d2d steps for selected options."""
        d2d_config.load_ecosystem_config(pipeline=self, options=self.selected_groups)

    @optional_step("Ruby")
    def map_ruby(self):
        """Load Ruby specific configurations for d2d steps."""
        pass

    def map_about_files(self):
        """Map ``from/`` .ABOUT files to their related ``to/`` resources."""
        d2d.map_about_files(project=self.project, logger=self.log)

    def map_checksum(self):
        """Map using SHA1 checksum."""
        d2d.map_checksum(project=self.project, checksum_field="sha1", logger=self.log)

    def match_archives_to_purldb(self):
        """Match selected package archives by extension to PurlDB."""
        if not purldb.is_available():
            self.log("PurlDB is not available. Skipping.")
            return

        d2d.match_purldb_resources(
            project=self.project,
            extensions=self.ecosystem_config.matchable_package_extensions,
            matcher_func=d2d.match_purldb_package,
            logger=self.log,
        )

    @optional_step("Java")
    def find_java_packages(self):
        """Find the java package of the .java source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.JavaLanguage, logger=self.log
        )

    @optional_step("Java")
    def map_java_to_class(self):
        """Map a .class compiled file to its .java source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.JavaLanguage, logger=self.log
        )

    @optional_step("Java")
    def map_jar_to_java_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_jvm_source(
            project=self.project, jvm_lang=jvm.JavaLanguage, logger=self.log
        )

    @optional_step("Scala")
    def find_scala_packages(self):
        """Find the java package of the .scala source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.ScalaLanguage, logger=self.log
        )

    @optional_step("Scala")
    def map_scala_to_class(self):
        """Map a .class compiled file to its .scala source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.ScalaLanguage, logger=self.log
        )

    @optional_step("Scala")
    def map_jar_to_scala_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_jvm_source(
            project=self.project, jvm_lang=jvm.ScalaLanguage, logger=self.log
        )

    @optional_step("Kotlin")
    def find_kotlin_packages(self):
        """Find the java package of the kotlin source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.KotlinLanguage, logger=self.log
        )

    @optional_step("Kotlin")
    def map_kotlin_to_class(self):
        """Map a .class compiled file to its kotlin source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.KotlinLanguage, logger=self.log
        )

    @optional_step("Kotlin")
    def map_jar_to_kotlin_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_jvm_source(
            project=self.project, jvm_lang=jvm.KotlinLanguage, logger=self.log
        )

    @optional_step("Grammar")
    def find_grammar_packages(self):
        """Find the java package of the .g/.g4 source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.GrammarLanguage, logger=self.log
        )

    @optional_step("Grammar")
    def map_grammar_to_class(self):
        """Map a .class compiled file to its .g/.g4 source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.GrammarLanguage, logger=self.log
        )

    @optional_step("Grammar")
    def map_jar_to_grammar_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_jvm_source(
            project=self.project, jvm_lang=jvm.GrammarLanguage, logger=self.log
        )

    @optional_step("Groovy")
    def find_groovy_packages(self):
        """Find the package of the .groovy source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.GroovyLanguage, logger=self.log
        )

    @optional_step("Groovy")
    def map_groovy_to_class(self):
        """Map a .class compiled file to its .groovy source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.GroovyLanguage, logger=self.log
        )

    @optional_step("Groovy")
    def map_jar_to_groovy_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_jvm_source(
            project=self.project, jvm_lang=jvm.GroovyLanguage, logger=self.log
        )

    @optional_step("AspectJ")
    def find_aspectj_packages(self):
        """Find the package of the .aj source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.AspectJLanguage, logger=self.log
        )

    @optional_step("AspectJ")
    def map_aspectj_to_class(self):
        """Map a .class compiled file to its .aj source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.AspectJLanguage, logger=self.log
        )

    @optional_step("AspectJ")
    def map_jar_to_aspectj_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_jvm_source(
            project=self.project, jvm_lang=jvm.AspectJLanguage, logger=self.log
        )

    @optional_step("Clojure")
    def find_clojure_packages(self):
        """Find the package of the .clj source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.ClojureLanguage, logger=self.log
        )

    @optional_step("Clojure")
    def map_clojure_to_class(self):
        """Map a .class compiled file to its .clj source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.ClojureLanguage, logger=self.log
        )

    @optional_step("Clojure")
    def map_jar_to_clojure_source(self):
        """Map .jar files to their related source directory."""
        d2d.map_jar_to_jvm_source(
            project=self.project, jvm_lang=jvm.ClojureLanguage, logger=self.log
        )

    @optional_step("Xtend")
    def find_xtend_packages(self):
        """Find the java package of the xtend source files."""
        d2d.find_jvm_packages(
            project=self.project, jvm_lang=jvm.XtendLanguage, logger=self.log
        )

    @optional_step("Xtend")
    def map_xtend_to_class(self):
        """Map a .class compiled file to its xtend source."""
        d2d.map_jvm_to_class(
            project=self.project, jvm_lang=jvm.XtendLanguage, logger=self.log
        )

    @optional_step("JavaScript")
    def map_javascript(self):
        """
        Map a packed or minified JavaScript, TypeScript, CSS and SCSS
        to its source.
        """
        d2d.map_javascript(project=self.project, logger=self.log)

    @optional_step("JavaScript")
    def map_javascript_symbols(self):
        """Map deployed JavaScript, TypeScript to its sources using symbols."""
        d2d.map_javascript_symbols(project=self.project, logger=self.log)

    @optional_step("JavaScript")
    def map_javascript_strings(self):
        """Map deployed JavaScript, TypeScript to its sources using string literals."""
        d2d.map_javascript_strings(project=self.project, logger=self.log)

    def get_symbols_from_binaries(self):
        """Extract symbols from Elf, Mach0 and windows binaries for mapping."""
        d2d.extract_binary_symbols(
            project=self.project,
            options=self.selected_groups,
            logger=self.log,
        )

    @optional_step("Elf")
    def map_elf(self):
        """Map ELF binaries to their sources using dwarf paths and symbols."""
        d2d.map_elfs_with_dwarf_paths(project=self.project, logger=self.log)
        d2d.map_elfs_binaries_with_symbols(project=self.project, logger=self.log)

    @optional_step("MacOS")
    def map_macho(self):
        """Map mach0 binaries to their sources using symbols."""
        d2d.map_macho_binaries_with_symbols(project=self.project, logger=self.log)

    @optional_step("Windows")
    def map_winpe(self):
        """Map winpe binaries to their sources using symbols."""
        d2d.map_winpe_binaries_with_symbols(project=self.project, logger=self.log)

    @optional_step("Go")
    def map_go(self):
        """Map Go binaries to their sources using paths and symbols."""
        d2d.map_go_paths(project=self.project, logger=self.log)
        d2d.map_go_binaries_with_symbols(project=self.project, logger=self.log)

    @optional_step("Rust")
    def map_rust(self):
        """Map Rust binaries to their sources using symbols."""
        d2d.map_rust_binaries_with_symbols(project=self.project, logger=self.log)

    @optional_step("Python")
    def map_python(self):
        """
        Map binaries from Python packages to their sources using dwarf paths and
        symbols.
        """
        d2d.map_python_pyx_to_binaries(project=self.project, logger=self.log)
        d2d.map_python_protobuf_files(project=self.project, logger=self.log)

    def match_directories_to_purldb(self):
        """Match selected directories in PurlDB."""
        if not purldb.is_available():
            self.log("PurlDB is not available. Skipping.")
            return

        d2d.match_purldb_directories(
            project=self.project,
            logger=self.log,
        )

    def match_resources_to_purldb(self):
        """Match selected files by extension in PurlDB."""
        if not purldb.is_available():
            self.log("PurlDB is not available. Skipping.")
            return

        d2d.match_purldb_resources(
            project=self.project,
            extensions=self.ecosystem_config.matchable_resource_extensions,
            matcher_func=d2d.match_purldb_resource,
            logger=self.log,
        )

    @optional_step("JavaScript")
    def map_javascript_post_purldb_match(self):
        """Map minified javascript file based on existing PurlDB match."""
        d2d.map_javascript_post_purldb_match(project=self.project, logger=self.log)

    @optional_step("JavaScript")
    def map_javascript_path(self):
        """Map javascript file based on path."""
        d2d.map_javascript_path(project=self.project, logger=self.log)

    @optional_step("JavaScript")
    def map_javascript_colocation(self):
        """Map JavaScript files based on neighborhood file mapping."""
        d2d.map_javascript_colocation(project=self.project, logger=self.log)

    @optional_step("JavaScript")
    def map_thirdparty_npm_packages(self):
        """Map thirdparty package using package.json metadata."""
        d2d.map_thirdparty_npm_packages(project=self.project, logger=self.log)

    def map_path(self):
        """Map using path similarities."""
        d2d.map_path(project=self.project, logger=self.log)

    def flag_mapped_resources_archives_and_ignored_directories(self):
        """Flag all codebase resources that were mapped during the pipeline."""
        flag.flag_mapped_resources(self.project)
        flag.flag_ignored_directories(self.project)
        d2d.flag_processed_archives(self.project)

    def perform_house_keeping_tasks(self):
        """
        On deployed side
            - Ignore specific files based on ecosystem based configurations.
            - PurlDB match files with ``no-java-source`` and empty status,
                if no match is found update status to ``requires-review``.
            - Update status for uninteresting files.
            - Flag the dangling legal files for review.

        On devel side
            - Update status for not deployed files.
        """
        d2d.match_resources_with_no_java_source(project=self.project, logger=self.log)
        d2d.handle_dangling_deployed_legal_files(project=self.project, logger=self.log)
        d2d.ignore_unmapped_resources_from_config(
            project=self.project,
            patterns_to_ignore=self.ecosystem_config.deployed_resource_path_exclusions,
            logger=self.log,
        )
        d2d.match_unmapped_resources(
            project=self.project,
            matched_extensions=self.ecosystem_config.matchable_resource_extensions,
            logger=self.log,
        )
        d2d.flag_undeployed_resources(project=self.project)

    def match_purldb_resources_post_process(self):
        """Choose the best package for PurlDB matched resources."""
        d2d.match_purldb_resources_post_process(self.project, logger=self.log)

    def remove_packages_without_resources(self):
        """Remove packages without any resources."""
        package_without_resources = self.project.discoveredpackages.filter(
            codebase_resources__isnull=True
        )
        package_without_resources.delete()

    def scan_ignored_to_files(self):
        """
        Scan status="ignored-from-config" ``to/`` files for copyrights,
        licenses, emails, and urls. These files are ignored based on
        ecosystem specific configurations. These files are not used for the
        D2D purpose, but scanning them may provide useful information about
        the deployed codebase.
        """
        d2d.scan_ignored_to_files(project=self.project, logger=self.log)

    def scan_unmapped_to_files(self):
        """
        Scan unmapped/matched ``to/`` files for copyrights, licenses,
        emails, and urls and update the status to `requires-review`.
        """
        d2d.scan_unmapped_to_files(project=self.project, logger=self.log)

    def scan_mapped_from_for_files(self):
        """Scan mapped ``from/`` files for copyrights, licenses, emails, and urls."""
        scan_files = d2d.get_from_files_for_scanning(self.project.codebaseresources)
        scancode.scan_for_files(self.project, scan_files, progress_logger=self.log)

    def collect_and_create_license_detections(self):
        """
        Collect and create unique license detections from resources and
        package data.
        """
        scancode.collect_and_create_license_detections(project=self.project)

    def create_local_files_packages(self):
        """Create local-files packages for codebase resources not part of a package."""
        d2d.create_local_files_packages(self.project)

    def flag_deployed_from_resources_with_missing_license(self):
        """Update the status for deployed from files with missing license."""
        d2d.flag_deployed_from_resources_with_missing_license(
            self.project,
            doc_extensions=self.ecosystem_config.doc_extensions,
        )

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

import json

from django.core.serializers.json import DjangoJSONEncoder

from commoncode.hash import multi_checksums

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import input
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_input
from scanpipe.pipes.input import is_archive

from scanpipe.pipes.resolve import get_pom_url_list
from scanpipe.pipes.resolve import download_and_scan_pom_file


class ScanMavenPackage(Pipeline):
    """
    Scan a single package archive (or package manifest file).

    This pipeline scans a single package for package metadata,
    declared dependencies, licenses, license clarity score and copyrights.

    The output is a summary of the scan results in JSON format.
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_package_input,
            cls.collect_input_information,
            cls.extract_input_to_codebase_directory,
            cls.extract_archives,
            cls.run_scan,
            cls.fetch_and_scan_remote_pom,
            cls.load_inventory_from_toolkit_scan,
            cls.make_summary_from_scan_results,
        )

    scancode_run_scan_args = {
        "copyright": True,
        "email": True,
        "info": True,
        "license": True,
        "license_text": True,
        "license_diagnostics": True,
        "license_text_diagnostics": True,
        "license_references": True,
        "package": True,
        "url": True,
        "classify": True,
        "summary": True,
        "todo": True,
    }

    def get_package_input(self):
        """Locate the package input in the project's input/ directory."""
        # Using the input_sources model property as it includes input sources instances
        # as well as any files manually copied into the input/ directory.
        input_sources = self.project.input_sources
        inputs = list(self.project.inputs("*"))

        if len(inputs) != 1 or len(input_sources) != 1:
            raise Exception("Only 1 input file supported")

        self.input_path = inputs[0]

    def collect_input_information(self):
        """Collect and store information about the project input."""
        self.project.update_extra_data(
            {
                "filename": self.input_path.name,
                "size": self.input_path.stat().st_size,
                **multi_checksums(self.input_path),
            }
        )

    def extract_input_to_codebase_directory(self):
        """Copy or extract input to project codebase/ directory."""
        if not is_archive(self.input_path):
            copy_input(self.input_path, self.project.codebase_path)
            return

        self.extract_archive(self.input_path, self.project.codebase_path)

        # Reload the project env post-extraction as the scancode-config.yml file
        # may be located in one of the extracted archives.
        self.env = self.project.get_env()

    def run_scan(self):
        """Scan extracted codebase/ content."""
        scan_output_path = self.project.get_output_file_path("scancode", "json")
        self.scan_output_location = str(scan_output_path.absolute())

        scanning_errors = scancode.run_scan(
            location=str(self.project.codebase_path),
            output_file=self.scan_output_location,
            run_scan_args=self.scancode_run_scan_args.copy(),
        )

        for resource_path, errors in scanning_errors.items():
            self.project.add_error(
                description="\n".join(errors),
                model=self.pipeline_name,
                details={"resource_path": resource_path.removeprefix("codebase/")},
            )

        if not scan_output_path.exists():
            raise FileNotFoundError("ScanCode output not available.")

    def fetch_and_scan_remote_pom(self):
        """Fetch the pom.xml file from from maven.org if not present in codebase."""
        # TODO Verify if the following filter actually work
        if not self.project.codebaseresources.files().filter(name="pom.xml").exists():
            with open(self.scan_output_location, 'r') as file:
                data = json.load(file)
                packages = data.get("packages", [])

            pom_url_list = get_pom_url_list(self.project.input_sources[0], packages)
            scanned_pom_packages, scanned_dependencies = download_and_scan_pom_file(pom_url_list)

            updated_pacakges = packages + scanned_pom_packages
            # Replace/Update the package and dependencies section
            data['packages'] = updated_pacakges
            # Need to update the dependencies
            # data['dependencies'] = scanned_dependencies
            with open(self.scan_output_location, 'w') as file:
                json.dump(data, file, indent=2)

    def load_inventory_from_toolkit_scan(self):
        """Process a JSON Scan results to populate codebase resources and packages."""
        input.load_inventory_from_toolkit_scan(self.project, self.scan_output_location)

    def make_summary_from_scan_results(self):
        """Build a summary in JSON format from the generated scan results."""
        summary = scancode.make_results_summary(self.project, self.scan_output_location)
        output_file = self.project.get_output_file_path("summary", "json")

        with output_file.open("w") as summary_file:
            summary_file.write(json.dumps(summary, indent=2, cls=DjangoJSONEncoder))

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
from collections import defaultdict
import time

from scanpipe.pipes import purldb
from scanpipe.pipes.output import to_json
from scanpipe.pipelines.scan_codebase import ScanCodebase

from scanpipe.pipes.d2d import create_package_from_purldb_data
from scanpipe.pipes import flag


class Matching(ScanCodebase):
    """
    Given an archive containing a codebase, match the contents against PurlDB
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.create_codebase_json,
            cls.match_to_purldb,
        )

    def create_codebase_json(self):
        """
        Copy input files to the project's codebase/ directory.
        The code can also be copied there prior to running the Pipeline.
        """
        self.scan_output_location = to_json(self.project)

    def match_to_purldb(self):
        # send scan to purldb
        response = purldb.send_project_json_to_matchcode(self.scan_output_location)
        url = response.get("url")
        results_url = url + "results/"

        # poll and get match results
        while True:
            response = purldb.request_get(results_url)
            if response.ok:
                match_results = response
                break
            time.sleep(10)

        # map match results
        matched_packages = match_results.get('packages', [])
        resource_results = match_results.get('files', [])
        for matched_package in matched_packages:
            package_uid = matched_package['package_uid']
            # Get resources
            resource_paths = []
            for resource in resource_results:
                if package_uid in resource.get('for_packages', []):
                    resource_paths.append(resource.path)
            resources = self.project.codebaseresources.filter(path__in=resource_paths)

            # Create package matche
            create_package_from_purldb_data(
                self.project,
                resources=resources,
                package_data=matched_package,
                status=flag.MATCHED_TO_PURLDB_PACKAGE,
            )


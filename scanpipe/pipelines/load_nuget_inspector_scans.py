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

import json

from commoncode.hash import multi_checksums

from scanpipe.models import CodebaseResource
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import update_or_create_package
from scanpipe.pipes.scancode import extract_archive


class LoadNugetInspectorScans(Pipeline):
    """Load one or more nuget-inspector scans as packages and refine metadata."""

    @classmethod
    def steps(cls):
        return (
            cls.get_nuget_inspector_scans,
            cls.load_nuget_inspector_scans,
        )

    def get_nuget_inspector_scans(self):
        """
        Locate all the nuget inspector scan files
        from the project's input/ directory.
        """
        inputs = list(self.project.inputs())
        self.archive_path = inputs[0]
        self.project.update_extra_data(
            {
                "filename": self.archive_path.name,
                "size": self.archive_path.stat().st_size,
                **multi_checksums(self.archive_path),
            }
        )
        extract_archive(self.archive_path, self.project.codebase_path)

    def load_nuget_inspector_scans(self):
        """Load nuget inspector scans and create Packages."""
        self.packages = []
        self.nuget_inspector_scan_locations = []
        for resource_path in self.project.walk_codebase_path():
            resource, _ = CodebaseResource.objects.get_or_create(
                project=self.project, path=str(resource_path.stem)
            )
            with open(resource_path) as f:
                json_data = json.load(f)
            packages = json_data.get("dependencies", [])
            for package_data in packages:
                update_or_create_package(
                    self.project, package_data, codebase_resources=[resource]
                )

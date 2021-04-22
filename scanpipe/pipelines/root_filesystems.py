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

import os

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import rootfs
from scanpipe.pipes import scancode


class RootFS(Pipeline):
    """
    A pipeline to analyze a Linux root filesystem aka. rootfs.
    """

    def extract_input_files_to_codebase_directory(self):
        """
        Extract root filesystem input archives with extractcode.
        """
        input_files = self.project.inputs("*")
        target_path = self.project.codebase_path
        extract_errors = []

        for input_file in input_files:
            extract_errors = scancode.extract(input_file, target_path)

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def find_root_filesystems(self):
        """
        Find the root filesystems in project codebase/.
        """
        self.root_filesystems = list(rootfs.RootFs.from_project_codebase(self.project))

    def collect_rootfs_information(self):
        """
        Collect rootfs information and store on project.
        """
        rootfs_data = {}
        for rfs in self.root_filesystems:
            rootfs_data["name"] = os.path.basename(rfs.location)
            rootfs_data["distro"] = rfs.distro.to_dict() if rfs.distro else {}

        self.project.extra_data.update({"images": rootfs_data})
        self.project.save()

    def collect_and_create_codebase_resources(self):
        """
        Collect and create all image files as CodebaseResource.
        """
        for rfs in self.root_filesystems:
            rootfs.create_codebase_resources(self.project, rfs)

    def collect_and_create_system_packages(self):
        """
        Collect installed system packages for each rootfs based on the distro.
        The collection of system packages is only available for known distros.
        """
        with self.save_errors(rootfs.DistroNotFound, rootfs.DistroNotSupported):
            for rfs in self.root_filesystems:
                rootfs.scan_rootfs_for_system_packages(self.project, rfs)

    def tag_uninteresting_codebase_resources(self):
        """
        Flag remaining files not from a system package if they are not worth tracking.
        """
        rootfs.tag_uninteresting_codebase_resources(self.project)

    def tag_empty_files(self):
        """
        Flag empty files.
        """
        rootfs.tag_empty_codebase_resources(self.project)

    def scan_for_application_packages(self):
        """
        Scan unknown resources for packages infos.
        """
        scancode.scan_for_application_packages(self.project, logger_func=self.log)

    def match_not_analyzed_to_system_packages(self):
        """
        Match not-yet-analyzed files to files already related to system packages.
        """
        rootfs.match_not_analyzed(
            self.project,
            reference_status="system-package",
            not_analyzed_status="",
        )

    def match_not_analyzed_to_application_packages(self):
        """
        Match not-yet-analyzed files to files already related to application packages.
        """
        # TODO: do it one rootfs at a time e.g. for rfs in self.root_filesystems:
        rootfs.match_not_analyzed(
            self.project,
            reference_status="application-package",
            not_analyzed_status="",
        )

    def scan_for_files(self):
        """
        Scan unknown resources for copyrights, licenses, emails, and urls.
        """
        scancode.scan_for_files(self.project, logger_func=self.log)

    def analyze_scanned_files(self):
        """
        Analyze single file scan results for completeness.
        """
        pipes.analyze_scanned_files(self.project)

    def tag_not_analyzed_codebase_resources(self):
        """
        Check for leftover files for sanity. We should have none.
        """
        pipes.tag_not_analyzed_codebase_resources(self.project)

    steps = (
        extract_input_files_to_codebase_directory,
        find_root_filesystems,
        collect_rootfs_information,
        collect_and_create_codebase_resources,
        collect_and_create_system_packages,
        tag_uninteresting_codebase_resources,
        tag_empty_files,
        scan_for_application_packages,
        match_not_analyzed_to_system_packages,
        scan_for_files,
        analyze_scanned_files,
        tag_not_analyzed_codebase_resources,
    )

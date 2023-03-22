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
    """Analyze a Linux root filesystem, aka rootfs."""

    @classmethod
    def steps(cls):
        return (
            cls.extract_input_files_to_codebase_directory,
            cls.find_root_filesystems,
            cls.collect_rootfs_information,
            cls.collect_and_create_codebase_resources,
            cls.collect_and_create_system_packages,
            cls.tag_uninteresting_codebase_resources,
            cls.tag_empty_files,
            cls.scan_for_application_packages,
            cls.match_not_analyzed_to_system_packages,
            cls.scan_for_files,
            cls.analyze_scanned_files,
            cls.tag_not_analyzed_codebase_resources,
        )

    def extract_input_files_to_codebase_directory(self):
        """Extract root filesystem input archives with extractcode."""
        input_files = self.project.inputs("*")
        target_path = self.project.codebase_path
        errors = []

        for input_file in input_files:
            extract_target = target_path / f"{input_file.name}-extract"
            extract_errors = scancode.extract_archive(input_file, extract_target)
            errors.extend(extract_errors)

        if errors:
            self.add_error("\n".join(errors))

    def find_root_filesystems(self):
        """Find root filesystems in the project's codebase/."""
        self.root_filesystems = list(rootfs.RootFs.from_project_codebase(self.project))

    def collect_rootfs_information(self):
        """Collect and stores rootfs information in the project."""
        rootfs_data = {}
        for rfs in self.root_filesystems:
            rootfs_data["name"] = os.path.basename(rfs.location)
            rootfs_data["distro"] = rfs.distro.to_dict() if rfs.distro else {}

        self.project.update_extra_data({"images": rootfs_data})

    def collect_and_create_codebase_resources(self):
        """Collect and label all image files as CodebaseResource."""
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
        """Flag files—not worth tracking—that don’t belong to any system packages."""
        rootfs.tag_uninteresting_codebase_resources(self.project)

    def tag_empty_files(self):
        """Flag empty files."""
        rootfs.tag_empty_codebase_resources(self.project)

    def scan_for_application_packages(self):
        """Scan unknown resources for packages information."""
        scancode.scan_for_application_packages(self.project)

    def match_not_analyzed_to_system_packages(self):
        """
        Match files with "not-yet-analyzed" status to files already belonging to
        system packages.
        """
        rootfs.match_not_analyzed(
            self.project,
            reference_status="system-package",
            not_analyzed_status="",
        )

    def match_not_analyzed_to_application_packages(self):
        """
        Match files with "not-yet-analyzed" status to files already belonging to
        application packages.
        """
        # TODO: do it one rootfs at a time e.g. for rfs in self.root_filesystems:
        rootfs.match_not_analyzed(
            self.project,
            reference_status="application-package",
            not_analyzed_status="",
        )

    def scan_for_files(self):
        """Scan unknown resources for copyrights, licenses, emails, and urls."""
        scancode.scan_for_files(self.project)

    def analyze_scanned_files(self):
        """Analyze single file scan results for completeness."""
        pipes.analyze_scanned_files(self.project)

    def tag_not_analyzed_codebase_resources(self):
        """Check for any leftover files for sanity; there should be none."""
        pipes.tag_not_analyzed_codebase_resources(self.project)

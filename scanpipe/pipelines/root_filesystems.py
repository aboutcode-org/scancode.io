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

# isort:skip_file

import os

import django

django.setup()

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import step
from scanpipe.pipes import rootfs


class RootfsPipeline(Pipeline):
    """
    A pipeline to analyze a Linux root filesystem aka. rootfs.
    """

    @step
    def start(self):
        """
        Load the Project instance.
        """
        self.project = self.get_project(self.project_name)
        self.next(self.find_root_filesystems)

    @step
    def find_root_filesystems(self):
        """
        Find the root filesystems in project codebase/.
        """
        self.root_filesystems = list(rootfs.RootFs.from_project_codebase(self.project))
        self.next(self.collect_rootfs_information)

    @step
    def collect_rootfs_information(self):
        """
        Collect rootfs information and store on project.
        """

        rootfs_data = {}
        for rfs in self.root_filesystems:
            rootfs_data["name"] = os.path.basename(rfs.location)
            rootfs_data["distro"] = rfs.distro.to_dict()
        self.project.extra_data.update({"images": rootfs_data})
        self.project.save()
        self.next(self.collect_and_create_codebase_resources)

    @step
    def collect_and_create_codebase_resources(self):
        """
        Collect and create all image files as CodebaseResource.
        """
        for rfs in self.root_filesystems:
            rootfs.create_codebase_resources(self.project, rfs)
        self.next(self.collect_and_create_system_packages)

    @step
    def collect_and_create_system_packages(self):
        """
        Collect installed system packages for each rootfs based on the distro.
        """
        for rfs in self.root_filesystems:
            rootfs.scan_rootfs_for_system_packages(self.project, rfs)
        self.next(self.tag_uninteresting_codebase_resources)

    @step
    def tag_uninteresting_codebase_resources(self):
        """
        Flag remaining files not from a system package if they are not worth tracking.
        """
        rootfs.tag_uninteresting_codebase_resources(self.project)
        self.next(self.scan_for_application_packages)

    @step
    def scan_for_application_packages(self):
        """
        Scan unknown resources for packages infos.
        """
        pipes.scan_for_application_packages(self.project)
        self.next(self.ignore_empty_files)

    @step
    def ignore_empty_files(self):
        """
        Skip and mark as ignored any empty file.
        """
        rootfs.tag_empty_codebase_resources(self.project)
        self.next(self.match_not_analyzed_to_system_packages)

    @step
    def match_not_analyzed_to_system_packages(self):
        """
        Match not-yet-analyzed files to files already related to system packages.
        """
        rootfs.match_not_analyzed(
            self.project,
            reference_status="system-package",
            not_analyzed_status="",
        )
        self.next(self.match_not_analyzed_to_application_packages)

    @step
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
        self.next(self.scan_for_files)

    @step
    def scan_for_files(self):
        """
        Scan unknown resources for copyrights, licenses, emails, and urls.
        """
        pipes.scan_for_files(self.project)
        self.next(self.analyze_scanned_files)

    @step
    def analyze_scanned_files(self):
        """
        Analyze single file scan results for completeness.
        """
        pipes.analyze_scanned_files(self.project)
        self.next(self.tag_not_analyzed_codebase_resources)

    @step
    def tag_not_analyzed_codebase_resources(self):
        """
        Check for leftover files for sanity. We should have none.
        """
        pipes.tag_not_analyzed_codebase_resources(self.project)
        self.next(self.end)

    @step
    def end(self):
        """
        Analysis completed.
        """


if __name__ == "__main__":
    RootfsPipeline()

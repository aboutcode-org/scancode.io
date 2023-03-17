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

from scanpipe.pipelines.docker import Docker
from scanpipe.pipes import docker
from scanpipe.pipes import rootfs
from scanpipe.pipes import windows


class DockerWindows(Docker):
    """Analyze Windows Docker images."""

    @classmethod
    def steps(cls):
        return (
            cls.extract_images,
            cls.extract_layers,
            cls.find_images_os_and_distro,
            cls.collect_images_information,
            cls.collect_and_create_codebase_resources,
            cls.collect_and_create_system_packages,
            cls.tag_known_software_packages,
            cls.tag_uninteresting_codebase_resources,
            cls.tag_program_files_dirs_as_packages,
            cls.tag_empty_files,
            cls.scan_for_application_packages,
            cls.scan_for_files,
            cls.analyze_scanned_files,
            cls.tag_data_files_with_no_clues,
            cls.tag_not_analyzed_codebase_resources,
        )

    def tag_known_software_packages(self):
        """Flag files from known software packages by checking common install paths."""
        windows.tag_known_software(self.project)

    def tag_uninteresting_codebase_resources(self):
        """Flag files that are known/labelled as uninteresting."""
        docker.tag_whiteout_codebase_resources(self.project)
        windows.tag_uninteresting_windows_codebase_resources(self.project)
        rootfs.tag_ignorable_codebase_resources(self.project)
        rootfs.tag_media_files_as_uninteresting(self.project)

    def tag_program_files_dirs_as_packages(self):
        """
        Report the immediate subdirectories of `Program Files` and `Program
        Files (x86)` as packages.
        """
        windows.tag_program_files(self.project)

    def tag_data_files_with_no_clues(self):
        """Flag data files that have no clues on their origin as uninteresting."""
        rootfs.tag_data_files_with_no_clues(self.project)

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

import logging
from pathlib import Path

from scanpipe.pipelines.analyze_docker import Docker
from scanpipe.pipes import docker
from scanpipe.pipes import rootfs
from scanpipe.pipes import windows
from scanpipe.pipes.fetch import store_package_archive
from scanpipe.pipes.input import is_archive

logger = logging.getLogger(__name__)


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
            cls.store_package_archives,
            cls.collect_and_create_system_packages,
            cls.flag_known_software_packages,
            cls.flag_uninteresting_codebase_resources,
            cls.flag_program_files_dirs_as_packages,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.scan_for_files,
            cls.analyze_scanned_files,
            cls.flag_data_files_with_no_clues,
            cls.flag_not_analyzed_codebase_resources,
        )

    def store_package_archives(self):
        """Store identified package archives for Windows images."""
        if not self.project.use_local_storage:
            logger.info(
                f"Local storage is disabled for project: {self.project.name}."
                "Skipping package storage."
            )
            return []

        logger.info(f"Storing package archives for project: {self.project.name}")
        stored_files = []

        package_files = [
            resource.path
            for resource in self.project.codebaseresources.all()
            if is_archive(resource.path)
        ]

        for package_path in package_files:
            if not Path(package_path).exists():
                logger.error(f"Invalid or missing package path: {package_path}")
                continue
            package_path_str = str(package_path)
            logger.info(f"Storing package archive: {package_path_str}")
            try:
                result = store_package_archive(
                    self.project, url=None, file_path=package_path_str
                )
                logger.info(f"Stored package archive {package_path_str}: {result}")
                stored_files.append(result)
            except Exception as e:
                logger.error(f"Failed to store {package_path_str}: {e}")

        return stored_files

    def flag_known_software_packages(self):
        """Flag files from known software packages by checking common install paths."""
        windows.flag_known_software(self.project)

    def flag_uninteresting_codebase_resources(self):
        """Flag files that are known/labelled as uninteresting."""
        docker.flag_whiteout_codebase_resources(self.project)
        windows.flag_uninteresting_windows_codebase_resources(self.project)
        rootfs.flag_ignorable_codebase_resources(self.project)
        rootfs.flag_media_files_as_uninteresting(self.project)

    def flag_program_files_dirs_as_packages(self):
        """
        Report the immediate subdirectories of ``Program Files`` and ``Program
        Files (x86)`` as packages.
        """
        windows.flag_program_files(self.project)

    def flag_data_files_with_no_clues(self):
        """Flag data files that have no clues on their origin as uninteresting."""
        rootfs.flag_data_files_with_no_clues(self.project)

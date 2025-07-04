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

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import scancode
from scanpipe.pipes.fetch import store_package_archive
from scanpipe.pipes.input import copy_inputs
from scanpipe.pipes.input import is_archive

logger = logging.getLogger(__name__)


class ScanCodebase(Pipeline):
    """
    Scan a codebase for application packages, licenses, and copyrights.

    This pipeline does not further scan the files contained in a package
    for license and copyrights and only considers the declared license
    of a package. It does not scan for system (Linux distro) packages.
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.store_package_archives,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.scan_for_files,
        )

    def copy_inputs_to_codebase_directory(self):
        """
        Copy input files to the project's codebase/ directory.
        The code can also be copied there prior to running the Pipeline.
        """
        copy_inputs(self.project.inputs("*"), self.project.codebase_path)

    def store_package_archives(self):
        """Store package archives locally if enabled."""
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

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        pipes.collect_and_create_codebase_resources(self.project)

    def scan_for_application_packages(self):
        """Scan unknown resources for packages information."""
        scancode.scan_for_application_packages(self.project, progress_logger=self.log)

    def scan_for_files(self):
        """Scan unknown resources for copyrights, licenses, emails, and urls."""
        scancode.scan_for_files(self.project, progress_logger=self.log)

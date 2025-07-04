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

from aboutcode.pipeline import group
from aboutcode.pipeline import optional_step
from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes import resolve
from scanpipe.pipes import scancode
from scanpipe.pipes.fetch import store_package_archive
from scanpipe.pipes.input import is_archive

logger = logging.getLogger(__name__)


class ResolveDependencies(ScanCodebase):
    """
    Resolve dependencies from package manifests and lockfiles.

    This pipeline collects lockfiles and manifest files
    that contain dependency requirements, and resolves these
    to a concrete set of package versions.

    Supports resolving packages for:
    - Python: using python-inspector, using requirements.txt and
    setup.py manifests as inputs
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_ignored_resources,
            cls.get_manifest_inputs,
            cls.store_manifest_files,
            cls.scan_for_application_packages,
            cls.store_package_archives,
            cls.create_packages_and_dependencies,
            cls.get_packages_from_manifest,
            cls.create_resolved_packages,
        )

    def get_manifest_inputs(self):
        """Locate package manifest files with a supported package resolver."""
        self.manifest_resources = resolve.get_manifest_resources(self.project)

    def store_manifest_files(self):
        """Store manifest files locally if enabled."""
        if not self.project.use_local_storage:
            logger.info(
                f"Local storage is disabled for project: {self.project.name}."
                "Skipping file storage."
            )
            return []

        logger.info(f"Storing manifest files for project: {self.project.name}")
        stored_files = []

        for resource in self.manifest_resources:
            resource_path = resource.path
            if not Path(resource_path).exists():
                logger.error(f"Invalid or missing file path: {resource_path}")
                continue
            resource_path_str = str(resource_path)
            logger.info(f"Storing manifest file: {resource_path_str}")
            try:
                result = store_package_archive(
                    self.project, url=None, file_path=resource_path_str
                )
                logger.info(f"Stored manifest file {resource_path_str}: {result}")
                stored_files.append(result)
            except Exception as e:
                logger.error(f"Failed to store {resource_path_str}: {e}")

        return stored_files

    @group("StaticResolver")
    def scan_for_application_packages(self):
        """
        Scan and assemble application packages from package manifests
        and lockfiles.
        """
        scancode.scan_for_application_packages(
            self.project,
            assemble=True,
            resource_qs=self.manifest_resources,
            progress_logger=self.log,
        )

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

    @group("StaticResolver")
    def create_packages_and_dependencies(self):
        """
        Create the statically resolved packages and their dependencies
        in the database.
        """
        scancode.process_package_data(self.project, static_resolve=True)

    @optional_step("DynamicResolver")
    def get_packages_from_manifest(self):
        """
        Resolve package data from lockfiles/requirement files with package
        requirements/dependencies.
        """
        self.resolved_packages = resolve.get_packages(
            project=self.project,
            package_registry=resolve.resolver_registry,
            manifest_resources=self.manifest_resources,
            model="get_packages_from_manifest",
        )

    @optional_step("DynamicResolver")
    def create_resolved_packages(self):
        """
        Create the dynamically resolved packages and their dependencies
        in the database.
        """
        resolve.create_packages_and_dependencies(
            project=self.project,
            packages=self.resolved_packages,
            resolved=True,
        )

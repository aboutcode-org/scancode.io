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
from aboutcode.pipeline import optional_step
from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes import scancode
from scanpipe.pipes.fetch import store_package_archive

logger = logging.getLogger(__name__)

class InspectPackages(ScanCodebase):
    """
    Inspect a codebase for packages and pre-resolved dependencies.

    This pipeline inspects a codebase for application packages
    and their dependencies using package manifests and dependency
    lockfiles. It does not resolve dependencies, it does instead
    collect already pre-resolved dependencies from lockfiles, and
    direct dependencies (possibly not resolved) as found in
    package manifests' dependency sections.

    See documentation for the list of supported package manifests and
    dependency lockfiles:
    https://scancode-toolkit.readthedocs.io/en/stable/reference/available_package_parsers.html
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.store_package_archives,
            cls.resolve_dependencies,
        )

    def scan_for_application_packages(self):
        """
        Scan resources for package information to add DiscoveredPackage
        and DiscoveredDependency objects from detected package data.
        """
        scancode.scan_for_application_packages(
            project=self.project,
            assemble=True,
            package_only=True,
            progress_logger=self.log,
        )

    def store_package_archives(self):
        """Store identified package archives locally if enabled."""
        if not self.project.use_local_storage:
            logger.info(f"Local storage is disabled for project: {self.project.name}."
                         "Skipping package storage.")
            return []

        logger.info(f"Storing package archives for project: {self.project.name}")
        stored_files = []
        package_files = [
            resource.path
            for resource in self.project.codebaseresources.filter(
                extension__in=[
                    ".zip", ".whl", ".tar.gz", ".deb", ".rpm", ".apk", ".nupkg", ".msi",
                      ".exe"]
            )
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
    def resolve_dependencies(self):
        """
        Create packages and dependency relationships from
        lockfiles or manifests containing pre-resolved
        dependencies.
        """
        scancode.resolve_dependencies(project=self.project)

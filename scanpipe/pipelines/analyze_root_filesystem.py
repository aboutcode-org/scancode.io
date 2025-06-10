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

from pathlib import Path

from extractcode import EXTRACT_SUFFIX

from scanpipe.models import DiscoveredPackage
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import flag
from scanpipe.pipes import rootfs
from scanpipe.pipes import scancode
from scanpipe.pipes.fetch import store_package_archive


class RootFS(Pipeline):
    """Analyze a Linux root filesystem, also known as rootfs."""

    @classmethod
    def steps(cls):
        return (
            cls.extract_input_files_to_codebase_directory,
            cls.find_root_filesystems,
            cls.collect_rootfs_information,
            cls.collect_and_create_codebase_resources,
            cls.collect_and_create_system_packages,
            cls.store_package_archives,
            cls.flag_uninteresting_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.scan_for_application_packages,
            cls.match_not_analyzed_to_system_packages,
            cls.scan_for_files,
            cls.analyze_scanned_files,
            cls.flag_not_analyzed_codebase_resources,
        )

    def extract_input_files_to_codebase_directory(self):
        """Extract root filesystem input archives with extractcode."""
        input_files = self.project.inputs("*")
        target_path = self.project.codebase_path

        for input_file in input_files:
            extract_target = target_path / f"{input_file.name}{EXTRACT_SUFFIX}"
            self.extract_archive(input_file, extract_target)

        # Reload the project env post-extraction as the scancode-config.yml file
        # may be located in one of the extracted archives.
        self.env = self.project.get_env()

    def find_root_filesystems(self):
        """Find root filesystems in the project's codebase/."""
        self.root_filesystems = list(rootfs.RootFs.from_project_codebase(self.project))

    def collect_rootfs_information(self):
        """Collect and stores rootfs information on the project."""
        rootfs_data = [
            rootfs.get_rootfs_data(root_fs) for root_fs in self.root_filesystems
        ]
        self.project.update_extra_data({"root_filesystems": rootfs_data})

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

    def store_package_archives(self):
        """
        Store package archives (.deb, .apk) found in the root filesystem or fetch
        them for detected system packages if configured to do so.
        """
        if not self.project.use_local_storage:
           self.log(f"Local storage is disabled for project: {self.project.name}."
                    "Skipping package storage.")
           return []
        if not self.env.get("STORE_DOWNLOADED_PACKAGES", True):
            self.log("Package storage skipped: STORE_DOWNLOADED_PACKAGES is disabled")
            return

        self.log(f"Storing package archives for project: {self.project.name}")
        stored_files = []

        package_files = [
            resource.path
            for resource in self.project.codebaseresources.filter(
                extension__in=[".deb", ".apk"]
            )
        ]
        for package_path in package_files:
            if not Path(package_path).exists():
                self.log(f"Package file not found: {package_path}", level="ERROR")
                continue
            result = store_package_archive(
                self.project, url=None, file_path=str(package_path)
            )
            self.log(f"Stored package archive: {package_path}, Result: {result}")
            stored_files.append(result)
        system_packages = DiscoveredPackage.objects.filter(project=self.project)
        self.log(f"Found {system_packages.count()} system packages")

        for pkg in system_packages:
            if "alpine" in pkg.purl:
                pkg_name = pkg.name
                pkg_version = pkg.version
                apk_url = f"http://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86_64/{pkg_name}-{pkg_version}.apk"
                try:
                    import requests

                    response = requests.get(apk_url, stream=True, timeout=10)
                    response.raise_for_status()
                    dest_path = (
                        Path(self.project.work_directory)
                        / "tmp"
                        / f"{pkg_name}-{pkg_version}.apk"
                    )
                    dest_path.parent.mkdir(exist_ok=True)
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    result = store_package_archive(
                        self.project, url=apk_url, file_path=str(dest_path)
                    )
                    self.log(
                        f"Stored system package archive: {pkg_name}, URL: {apk_url},"
                        "Result: {result}"
                    )
                    stored_files.append(result)
                except Exception as e:
                    self.log(
                        f"Failed to fetch/store {pkg_name} from {apk_url}: {e}",
                        level="WARNING",
                    )

        return stored_files

    def flag_uninteresting_codebase_resources(self):
        """Flag files—not worth tracking—that don’t belong to any system packages."""
        rootfs.flag_uninteresting_codebase_resources(self.project)

    def scan_for_application_packages(self):
        """Scan unknown resources for packages information."""
        scancode.scan_for_application_packages(self.project, progress_logger=self.log)

    def match_not_analyzed_to_system_packages(self):
        """
        Match files with "not-yet-analyzed" status to files already belonging to
        system packages.
        """
        rootfs.match_not_analyzed(
            self.project,
            reference_status=flag.SYSTEM_PACKAGE,
            not_analyzed_status=flag.NO_STATUS,
        )

    def match_not_analyzed_to_application_packages(self):
        """
        Match files with "not-yet-analyzed" status to files already belonging to
        application packages.
        """
        # TODO: do it one rootfs at a time e.g. for rfs in self.root_filesystems:
        rootfs.match_not_analyzed(
            self.project,
            reference_status=flag.APPLICATION_PACKAGE,
            not_analyzed_status=flag.NO_STATUS,
        )

    def scan_for_files(self):
        """Scan unknown resources for copyrights, licenses, emails, and urls."""
        scancode.scan_for_files(self.project, progress_logger=self.log)

    def analyze_scanned_files(self):
        """Analyze single file scan results for completeness."""
        flag.analyze_scanned_files(self.project)

    def flag_not_analyzed_codebase_resources(self):
        """Check for any leftover files for sanity; there should be none."""
        flag.flag_not_analyzed_codebase_resources(self.project)

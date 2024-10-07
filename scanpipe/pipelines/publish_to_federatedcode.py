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

import shutil

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode


class PublishToFederatedCode(Pipeline):
    """Publish package scan to FederatedCode Git repository."""

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.get_package,
            cls.get_package_repository,
            cls.clone_repository,
            cls.add_scan_result,
            cls.commit_and_push_changes,
            cls.delete_local_clone,
        )

    def get_package(self):
        has_single_package_scan = any(
            run.pipeline_name == "scan_single_package"
            for run in self.project.runs.all()
            if run.task_exitcode == 0
        )

        if not has_single_package_scan:
            raise Exception("Run ``scan_single_package`` pipeline to get package scan.")

        if not self.project.discoveredpackages.count() == 1:
            raise Exception("Scan should be for single package.")

        if not self.project.discoveredpackages.first().version:
            raise Exception("Scan package is missing version.")

        configured, error = federatedcode.is_configured()
        if not configured:
            raise Exception(error)

        self.package = self.project.discoveredpackages.first()

    def get_package_repository(self):
        self.package_scan_file, self.package_git_repo = (
            federatedcode.get_package_repository(package=self.package, logger=self.log)
        )

    def clone_repository(self):
        """Clone repository to local_path."""
        self.repo = federatedcode.clone_repository(
            package_repo_url=self.package_git_repo,
            logger=self.log,
        )

    def add_scan_result(self):
        self.relative_file_path = federatedcode.add_scan_result(
            project=self.project,
            repo=self.repo,
            package_scan_file=self.package_scan_file,
            logger=self.log,
        )

    def commit_and_push_changes(self):
        federatedcode.commit_and_push_changes(
            repo=self.repo,
            file_to_commit=str(self.relative_file_path),
            purl=self.package.purl,
            logger=self.log,
        )

    def delete_local_clone(self):
        shutil.rmtree(self.repo.working_dir)

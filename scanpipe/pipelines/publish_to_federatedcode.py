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
    """
    Publish package scan to FederatedCode.

    This pipeline commits the project scan result in FederatedCode Git repository.
    It uses ``Project PURL`` to determine the Git repository and the
    exact directory path where the scan should be stored.
    """

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            cls.get_package_repository,
            cls.clone_repository,
            cls.add_scan_result,
            cls.commit_and_push_changes,
            cls.delete_working_dir,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_eligibility(project=self.project)

    def create_federatedcode_working_dir(self):
        self.working_path = federatedcode.create_federatedcode_working_dir()

    def get_package_repository(self):
        """Get the Git repository URL and scan path for a given package."""
        self.package_repo_name, self.package_git_repo, self.package_scan_file = (
            federatedcode.get_package_repository(
                project_purl=self.project.purl, logger=self.log
            )
        )

    def clone_repository(self):
        """Clone repository to local_path."""
        self.repo = federatedcode.clone_repository(
            repo_url=self.package_git_repo,
            clone_path=self.working_path / self.package_repo_name,
            logger=self.log,
        )

    def add_scan_result(self):
        """Add package scan result to the local Git repository."""
        self.relative_file_path = federatedcode.add_scan_result(
            project=self.project,
            repo=self.repo,
            package_scan_file=self.package_scan_file,
            logger=self.log,
        )

    def commit_and_push_changes(self):
        """Commit and push changes to remote repository."""
        federatedcode.commit_and_push_changes(
            repo=self.repo,
            files_to_commit=[str(self.relative_file_path)],
            purls=[self.project.purl],
            logger=self.log,
        )
        self.log(
            f"Scan result for '{self.project.purl}' pushed to '{self.package_git_repo}'"
        )

    def delete_working_dir(self):
        """Remove temporary working dir."""
        shutil.rmtree(self.working_dir)

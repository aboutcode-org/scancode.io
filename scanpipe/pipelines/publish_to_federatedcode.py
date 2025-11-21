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
            cls.add_origin_curations,
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

    def add_origin_curations(self):
        """Add origin curations to the local Git repository."""
        deploy_options = {}
        if getattr(self.project, "extra_data", None):
            deploy_options = self.project.extra_data.get("origin_deploy", {}) or {}

        include_history = deploy_options.get("include_history", True)
        merge_strategy = deploy_options.get("merge_strategy", "latest")

        # Check if there are any curated relations
        curated_count = (
            self.project.codebaserelations.filter(curation_status__isnull=False)
            .exclude(curation_status="")
            .count()
        )

        if curated_count > 0:
            self.relative_curation_file_path = federatedcode.add_origin_curations(
                project=self.project,
                repo=self.repo,
                package_scan_file=self.package_scan_file,
                include_history=include_history,
                merge_strategy=merge_strategy,
                logger=self.log,
            )
            self.log(
                f"Origin curations ({curated_count} relations) added to repository "
                f"using '{merge_strategy}' strategy "
                f"{'with' if include_history else 'without'} history."
            )
        else:
            self.relative_curation_file_path = None
            self.log("No curated relations to export.")

        # Clean up deploy options to avoid re-use on future runs
        if getattr(self.project, "extra_data", None) and self.project.extra_data.get(
            "origin_deploy"
        ):
            extra_data = self.project.extra_data
            extra_data.pop("origin_deploy", None)
            self.project.extra_data = extra_data
            self.project.save(update_fields=["extra_data"])

    def commit_and_push_changes(self):
        """Commit and push changes to remote repository."""
        files_to_commit = [str(self.relative_file_path)]
        if (
            hasattr(self, "relative_curation_file_path")
            and self.relative_curation_file_path
        ):
            files_to_commit.append(str(self.relative_curation_file_path))

        federatedcode.commit_and_push_changes(
            repo=self.repo,
            files_to_commit=files_to_commit,
            purls=[self.project.purl],
            logger=self.log,
        )
        self.log(
            f"Scan result for '{self.project.purl}' pushed to '{self.package_git_repo}'"
        )

    def delete_working_dir(self):
        """Remove temporary working dir."""
        shutil.rmtree(self.working_dir)

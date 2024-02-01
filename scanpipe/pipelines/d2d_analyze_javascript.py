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

from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipes import d2d
from scanpipe.pipes import flag


class DeployToDevelopJavaScript(DeployToDevelop):
    """
    Establish relationships between two JavaScript code trees: deployment and
    development.

    This pipeline is expecting 2 archive files with "from-" and "to-" filename
    prefixes as inputs:
    - "from-[FILENAME]" archive containing the development source code
    - "to-[FILENAME]" archive containing the deployment compiled code

    Alternatively, when using download URLs as inputs, the from and to tag can be
    provided adding a "#from" / "#to" fragment at the end of the download URLs.
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.extract_inputs_to_codebase_directory,
            cls.extract_archives_in_place,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_whitespace_files,
            cls.flag_ignored_resources,
            cls.map_about_files,
            cls.map_checksum,
            cls.map_javascript,
            cls.map_javascript_path,
            cls.map_javascript_colocation,
            cls.map_thirdparty_npm_packages,
            cls.map_path,
            cls.flag_mapped_resources_archives_and_ignored_directories,
            cls.perform_house_keeping_tasks,
            cls.remove_packages_without_resources,
            cls.scan_unmapped_to_files,
            cls.scan_mapped_from_for_files,
            cls.flag_deployed_from_resources_with_missing_license,
            cls.create_local_files_packages,
        )

    def perform_house_keeping_tasks(self):
        """
        On deployed side
            - Flag the dangling legal files for review.
            - Flag file without status for review.

        On devel side
            - Update status for not deployed files.
        """
        d2d.handle_dangling_deployed_legal_files(project=self.project, logger=self.log)
        flag_deployed_resource_without_status_for_review(
            project=self.project, logger=self.log
        )
        d2d.flag_undeployed_resources(project=self.project)


def flag_deployed_resource_without_status_for_review(project, logger):
    project_files = project.codebaseresources.files()
    to_unmapped = project_files.to_codebase().no_status().exclude(is_media=True)

    to_unmapped.update(status=flag.REQUIRES_REVIEW)

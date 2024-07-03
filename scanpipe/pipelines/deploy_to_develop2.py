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

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import group
from scanpipe.pipes import d2d
from scanpipe.pipes import flag
from scanpipe.pipes import matchcode
from scanpipe.pipes import purldb
from scanpipe.pipes import scancode


class DeployToDevelop2(Pipeline):
    """
    Establish relationships between two code trees: deployment and development.

    This pipeline requires a minimum of two archive files, each properly tagged with:

    - **from** for archives containing the development source code.
    - **to** for archives containing the deployment compiled code.

    When using download URLs as inputs, the "from" and "to" tags can be
    provided by adding a "#from" or "#to" fragment at the end of the download URLs.

    When uploading local files:

    - **User Interface:** Use the "Edit flag" link in the "Inputs" panel of the Project
      details view.
    - **REST API:** Utilize the "upload_file_tag" field in addition to the
      "upload_file".
    - **Command Line Interface:** Tag uploaded files using the "filename:tag" syntax,
      for example, ``--input-file path/filename:tag``.
    """

    # Flag specifying whether to download missing inputs as an initial step.
    download_inputs = False
    # Flag indicating if the Pipeline is an add-on, meaning it cannot be run first.
    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.map_about_files2,
            cls.map_checksum,
            cls.match_archives_to_purldb,
            cls.find_java_packages,
            cls.map_java_to_class,
            cls.map_jar_to_source,
            cls.map_javascript,
            cls.map_elf,
            cls.map_go,
            cls.match_directories_to_purldb,
            cls.match_resources_to_purldb,
            cls.map_javascript_post_purldb_match,
            cls.map_javascript_path,
            cls.map_javascript_colocation,
            cls.map_thirdparty_npm_packages,
            cls.map_path,
            cls.flag_mapped_resources_archives_and_ignored_directories,
            cls.perform_house_keeping_tasks,
            cls.match_purldb_resources_post_process,
            cls.remove_packages_without_resources,
            cls.scan_unmapped_to_files,
            cls.scan_mapped_from_for_files,
            cls.flag_deployed_from_resources_with_missing_license,
            cls.create_local_files_packages,
        )

    def map_about_files2(self):
        """Map ``from/`` .ABOUT files to their related ``to/`` resources."""
        map_about_files2(project=self.project, logger=self.log)



def map_about_files2(project, logger=None):
    """Map ``from/`` .ABOUT files to their related ``to/`` resources."""
    project_resources = project.codebaseresources
    from_about_files = (
        project_resources.files().from_codebase().filter(extension=".ABOUT")
    )
    if not from_about_files.exists():
        return

    if logger:
        logger(
            f"Mapping {from_about_files.count():,d} .ABOUT files found in the from/ "
            f"codebase."
        )

    about_mapper = d2d.AboutFileMapper.from_codebaseresources(
        about_file_resources=from_about_files,
        logger=logger,
    )

    # Ignoring empty or ignored files as they are not relevant anyway
    to_resources = project_resources.to_codebase()

    mapped_to_resources = about_mapper.map_deployed_to_devel_using_about(
        to_resources=to_resources,
        logger=logger,
    )
    if logger:
        logger(
            f"Mapped {len(mapped_to_resources):,d} resources from the "
            f"to/ codebase to the About files in the from. codebase."
        )

    about_purls, mapped_about_resources = about_mapper.create_about_packages_relations(
        project=project,
    )
    if logger:
        logger(
            f"Created {len(about_purls):,d} new packages from "
            f"{len(mapped_about_resources):,d} About files which "
            f"were mapped to resources in the to/ side."
        )


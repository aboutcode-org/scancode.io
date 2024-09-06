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

from aboutcode.pipeline import group
from scanpipe import pipes
from scanpipe.pipelines.deploy_to_develop import DeployToDevelop
from scanpipe.pipes import d2d


class AndroidAPKDeployToDevelop(DeployToDevelop):
    """
    Establish relationships between two code trees: deployment and development for Android APKs.

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

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.extract_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.convert_dex_to_java
            cls.map_checksum,
            # substring matching step
            cls.find_java_packages,
            cls.map_java_to_class,
            cls.map_jar_to_source,
            cls.flag_mapped_resources_archives_and_ignored_directories,
            cls.remove_packages_without_resources,
            cls.flag_deployed_from_resources_with_missing_license,
            cls.create_local_files_packages,
        )

    def convert_dex_to_java(self):
        d2d.convert_dex_to_java(self.project)

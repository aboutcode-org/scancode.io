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

from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes import yara


class ScanAndMatchWithYara(ScanCodebase):
    """
    Scan a codebase and identify packages using YARA rules.

    This pipeline accepts archive files or source directories as input.
    It scans the codebase files using YARA pattern rules to detect
    packages.

    Currently supported packages:
    - jq
    - libass
    - libcurl
    - OpenSSL
    """

    results_url = "/project/{slug}/packages/"

    @classmethod
    def get_availability(cls):
        if not yara.is_available():
            return "yara-python is not installed."

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.match_resources_by_yara_rules,
        )

    def match_resources_by_yara_rules(self):
        """Match codebase files to packages using YARA pattern rules."""
        yara.match_resources_by_yara(self.project, logger=self.log)

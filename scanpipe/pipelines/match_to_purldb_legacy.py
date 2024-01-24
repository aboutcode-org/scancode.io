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

from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes import d2d
from scanpipe.pipes import purldb


class MatchToPurlDBLegacy(ScanCodebase):
    """
    Check CodebaseResources of a Project against PurlDB for Package matches.

    This involves creating a JSON scan of the Project codebase, sending it to
    MatchCode on PurlDB, waiting for match results, creating DiscoveredPackages
    from the match results Package data and associating the proper
    CodebaseResources to those DiscoveredPackges.
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.flag_empty_files,
            cls.flag_ignored_resources,
            cls.match_archives_to_purldb,
            cls.match_resources_to_purldb,
        )

    purldb_package_extensions = [".jar", ".war", ".zip"]
    purldb_resource_extensions = [
        ".map",
        ".js",
        ".mjs",
        ".ts",
        ".d.ts",
        ".jsx",
        ".tsx",
        ".css",
        ".scss",
        ".less",
        ".sass",
        ".soy",
        ".class",
    ]

    def match_archives_to_purldb(self):
        """Match selected package archives by extension to PurlDB."""
        if not purldb.is_available():
            self.log("PurlDB is not available. Skipping.")
            return

        d2d.match_purldb_resources2(
            project=self.project,
            extensions=self.purldb_package_extensions,
            matcher_func=d2d.match_purldb_package,
            logger=self.log,
        )

    def match_resources_to_purldb(self):
        """Match selected files by extension in PurlDB."""
        if not purldb.is_available():
            self.log("PurlDB is not available. Skipping.")
            return

        d2d.match_purldb_resources2(
            project=self.project,
            extensions=self.purldb_resource_extensions,
            matcher_func=d2d.match_purldb_resource,
            logger=self.log,
        )

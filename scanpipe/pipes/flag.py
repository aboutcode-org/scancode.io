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


NO_STATUS = ""

SCANNED = "scanned"
SCANNED_WITH_ERROR = "scanned-with-error"

SYSTEM_PACKAGE = "system-package"
APPLICATION_PACKAGE = "application-package"
INSTALLED_PACKAGE = "installed-package"

NO_LICENSES = "no-licenses"
UNKNOWN_LICENSE = "unknown-license"
NOT_ANALYZED = "not-analyzed"

RESOURCE_READ_ERROR = "resource-read-error"

IGNORED_WHITEOUT = "ignored-whiteout"
IGNORED_EMPTY_FILE = "ignored-empty-file"
IGNORED_WHITESPACE_FILE = "ignored-whitespace-file"
IGNORED_DIRECTORY = "ignored-directory"
IGNORED_PATTERN = "ignored-pattern"
IGNORED_MEDIA_FILE = "ignored-media-file"
IGNORED_NOT_INTERESTING = "ignored-not-interesting"
IGNORED_DEFAULT_IGNORES = "ignored-default-ignores"
IGNORED_DATA_FILE_NO_CLUES = "ignored-data-file-no-clues"
IGNORED_DOC_FILE = "ignored-doc-file"
IGNORED_FROM_CONFIG = "ignored-from-config"
IGNORED_BY_MAX_FILE_SIZE = "ignored-by-max-file-size"

COMPLIANCE_LICENSES = "compliance-licenses"
COMPLIANCE_SOURCEMIRROR = "compliance-sourcemirror"

ABOUT_MAPPED = "about-mapped"
MAPPED = "mapped"
MAPPED_BY_SYMBOL = "mapped-by-symbol"
ARCHIVE_PROCESSED = "archive-processed"
MATCHED_TO_PURLDB_PACKAGE = "matched-to-purldb-package"
MATCHED_TO_PURLDB_RESOURCE = "matched-to-purldb-resource"
MATCHED_TO_PURLDB_DIRECTORY = "matched-to-purldb-directory"
APPROXIMATE_MATCHED_TO_PURLDB_RESOURCE = "approximate-matched-to-purldb-resource"
TOO_MANY_MAPS = "too-many-maps"
NO_JAVA_SOURCE = "no-java-source"
NPM_PACKAGE_LOOKUP = "npm-package-lookup"
REQUIRES_REVIEW = "requires-review"
REVIEW_DANGLING_LEGAL_FILE = "review-dangling-legal-file"
NOT_DEPLOYED = "not-deployed"


# Target files that should be ignored during processing as those are related to the app
# configuration.
DEFAULT_IGNORED_PATTERNS = [
    "scancode-config.yml",  # when located in the root dir
    "*/scancode-config.yml",
    "policies.yml",  # when located in the root dir
    "*/policies.yml",
    "*/__MACOSX*",  # macOS metadata folder
]


def flag_empty_files(project):
    """Flag empty files as ignored."""
    qs = (
        project.codebaseresources.files()
        .empty()
        .filter(status__in=(NO_STATUS, NOT_ANALYZED))
    )
    return qs.update(status=IGNORED_EMPTY_FILE)


def flag_ignored_directories(project):
    """Flag directories as ignored."""
    qs = project.codebaseresources.no_status().directories()
    return qs.update(status=IGNORED_DIRECTORY)


def flag_ignored_patterns(codebaseresources, patterns, status=IGNORED_PATTERN):
    """Flag codebase resource as ``ignored`` status from list of ``patterns``."""
    if isinstance(patterns, str):
        patterns = patterns.splitlines()

    update_count = 0
    for pattern in patterns:
        qs = codebaseresources.path_pattern(pattern)
        update_count += qs.update(status=status)

    return update_count


def flag_and_ignore_files_over_max_size(resource_qs, file_size_limit):
    """
    Flag codebase resources which are over the max file size for scanning
    and return all other files within the file size limit.
    """
    if not file_size_limit:
        return resource_qs

    return resource_qs.filter(size__gte=file_size_limit).update(
        status=IGNORED_BY_MAX_FILE_SIZE
    )


def analyze_scanned_files(project):
    """Set the status for CodebaseResource to unknown or no license."""
    scanned_files = project.codebaseresources.files().status(SCANNED)
    scanned_files.has_no_license_detections().update(status=NO_LICENSES)
    scanned_files.unknown_license().update(status=UNKNOWN_LICENSE)


def flag_not_analyzed_codebase_resources(project):
    """Flag codebase resource as `not-analyzed`."""
    return project.codebaseresources.no_status().update(status=NOT_ANALYZED)


def flag_mapped_resources(project):
    """Flag all codebase resources that were mapped during the d2d pipeline."""
    resources = project.codebaseresources.has_relation().no_status()
    return resources.update(status=MAPPED)

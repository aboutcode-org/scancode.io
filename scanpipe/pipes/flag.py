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

from django.db.models import Q

NO_STATUS = ""

SCANNED = "scanned"
SCANNED_WITH_ERROR = "scanned-with-error"

SYSTEM_PACKAGE = "system-package"
APPLICATION_PACKAGE = "application-package"
INSTALLED_PACKAGE = "installed-package"

NO_LICENSES = "no-licenses"
UNKNOWN_LICENSE = "unknown-license"
NOT_ANALYZED = "not-analyzed"

IGNORED_WHITEOUT = "ignored-whiteout"
IGNORED_EMPTY_FILE = "ignored-empty-file"
IGNORED_DIRECTORY = "ignored-directory"
IGNORED_FILENAME = "ignored-filename"
IGNORED_EXTENSION = "ignored-extension"
IGNORED_PATH = "ignored-path"
IGNORED_MEDIA_FILE = "ignored-media-file"
IGNORED_NOT_INTERESTING = "ignored-not-interesting"
IGNORED_DEFAULT_IGNORES = "ignored-default-ignores"
IGNORED_DATA_FILE_NO_CLUES = "ignored-data-file-no-clues"
IGNORED_META_INF = "ignored-meta-inf"

COMPLIANCE_LICENSES = "compliance-licenses"
COMPLIANCE_SOURCEMIRROR = "compliance-sourcemirror"

MAPPED = "mapped"
MATCHED_TO_PURLDB = "matched-to-purldb"
TOO_MANY_MAPS = "too-many-maps"
NO_JAVA_SOURCE = "no-java-source"

RESOURCE_STATUSES = [
    SCANNED,
    SCANNED_WITH_ERROR,
    SYSTEM_PACKAGE,
    APPLICATION_PACKAGE,
    INSTALLED_PACKAGE,
    NO_LICENSES,
    UNKNOWN_LICENSE,
    NOT_ANALYZED,
    IGNORED_WHITEOUT,
    IGNORED_EMPTY_FILE,
    IGNORED_FILENAME,
    IGNORED_EXTENSION,
    IGNORED_PATH,
    IGNORED_MEDIA_FILE,
    IGNORED_NOT_INTERESTING,
    IGNORED_DEFAULT_IGNORES,
    IGNORED_DATA_FILE_NO_CLUES,
    COMPLIANCE_LICENSES,
    COMPLIANCE_SOURCEMIRROR,
    MAPPED,
    MATCHED_TO_PURLDB,
    TOO_MANY_MAPS,
    NO_JAVA_SOURCE,
]


def flag_empty_codebase_resources(project):
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


def flag_ignored_filenames(project, filenames):
    """Flag codebase resource as `ignored` status from list of `filenames`."""
    qs = project.codebaseresources.no_status().filter(name__in=filenames)
    return qs.update(status=IGNORED_FILENAME)


def flag_ignored_extensions(project, extensions):
    """Flag codebase resource as `ignored` status from list of `extensions`."""
    qs = project.codebaseresources.no_status().filter(extension__in=extensions)
    return qs.update(status=IGNORED_EXTENSION)


def flag_ignored_paths(project, paths):
    """Flag codebase resource as `ignored` status from list of `paths`."""
    lookups = Q()
    for path in paths:
        lookups |= Q(path__contains=path)

    qs = project.codebaseresources.no_status().filter(lookups)
    return qs.update(status=IGNORED_PATH)


def analyze_scanned_files(project):
    """Set the status for CodebaseResource to unknown or no license."""
    scanned_files = project.codebaseresources.files().status(SCANNED)
    scanned_files.has_no_license_detections().update(status=NO_LICENSES)
    scanned_files.unknown_license().update(status=UNKNOWN_LICENSE)


def tag_not_analyzed_codebase_resources(project):
    """Flag codebase resource as `not-analyzed`."""
    return project.codebaseresources.no_status().update(status=NOT_ANALYZED)


def flag_mapped_resources(project):
    """Flag all codebase resources that were mapped during the d2d pipeline."""
    resources = project.codebaseresources.has_relation().no_status()
    return resources.update(status=MAPPED)

#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

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
IGNORED_WHITESPACE_FILE = "ignored-whitespace-file"
IGNORED_DIRECTORY = "ignored-directory"
IGNORED_PATTERN = "ignored-pattern"
IGNORED_MEDIA_FILE = "ignored-media-file"
IGNORED_NOT_INTERESTING = "ignored-not-interesting"
IGNORED_DEFAULT_IGNORES = "ignored-default-ignores"
IGNORED_DATA_FILE_NO_CLUES = "ignored-data-file-no-clues"
IGNORED_DOC_FILE = "ignored-doc-file"

COMPLIANCE_LICENSES = "compliance-licenses"
COMPLIANCE_SOURCEMIRROR = "compliance-sourcemirror"

ABOUT_MAPPED = "about-mapped"
MAPPED = "mapped"
ARCHIVE_PROCESSED = "archive-processed"
MATCHED_TO_PURLDB_PACKAGE = "matched-to-purldb-package"
MATCHED_TO_PURLDB_RESOURCE = "matched-to-purldb-resource"
MATCHED_TO_PURLDB_DIRECTORY = "matched-to-purldb-directory"
TOO_MANY_MAPS = "too-many-maps"
NO_JAVA_SOURCE = "no-java-source"
NPM_PACKAGE_LOOKUP = "npm-package-lookup"
REQUIRES_REVIEW = "requires-review"
REVIEW_DANGLING_LEGAL_FILE = "review-dangling-legal-file"
NOT_DEPLOYED = "not-deployed"


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


def flag_ignored_patterns(project, patterns):
    """Flag codebase resource as ``ignored`` status from list of ``patterns``."""
    if isinstance(patterns, str):
        patterns = patterns.splitlines()

    update_count = 0
    for pattern in patterns:
        qs = project.codebaseresources.no_status().path_pattern(pattern)
        update_count += qs.update(status=IGNORED_PATTERN)

    return update_count


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

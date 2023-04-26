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


def flag_empty_codebase_resources(project):
    """Flag empty files as ignored."""
    qs = (
        project.codebaseresources.files()
        .empty()
        .filter(status__in=("", "not-analyzed"))
    )
    return qs.update(status="ignored-empty-file")


def flag_ignored_filenames(project, filenames):
    """Flag codebase resource as `ignored` status from list of `filenames`."""
    qs = project.codebaseresources.no_status().filter(name__in=filenames)
    return qs.update(status="ignored-filename")


def flag_ignored_extensions(project, extensions):
    """Flag codebase resource as `ignored` status from list of `extensions`."""
    qs = project.codebaseresources.no_status().filter(extension__in=extensions)
    return qs.update(status="ignored-extension")


def flag_ignored_paths(project, paths):
    """Flag codebase resource as `ignored` status from list of `paths`."""
    lookups = Q()
    for path in paths:
        lookups |= Q(path__contains=path)

    qs = project.codebaseresources.no_status().filter(lookups)
    return qs.update(status="ignored-path")


def analyze_scanned_files(project):
    """Set the status for CodebaseResource to unknown or no license."""
    scanned_files = project.codebaseresources.files().status("scanned")
    scanned_files.has_no_licenses().update(status="no-licenses")
    scanned_files.unknown_license().update(status="unknown-license")


def tag_not_analyzed_codebase_resources(project):
    """Flag codebase resource as `not-analyzed`."""
    project.codebaseresources.no_status().update(status="not-analyzed")


def flag_mapped_resources(project):
    """Flag all codebase resources that were mapped during the d2d pipeline."""
    resources = project.codebaseresources.to_codebase().has_relation().no_status()
    return resources.update(status="mapped")

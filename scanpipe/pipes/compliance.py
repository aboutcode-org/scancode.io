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

from collections import defaultdict

from scanpipe.models import PACKAGE_URL_FIELDS
from scanpipe.models import ComplianceAlertMixin
from scanpipe.pipes import flag
from scanpipe.pipes import scancode

"""
A common compliance pattern for images is to store known licenses in a /licenses
directory and the corresponding source code archives, for packages that are
redistributable in source form, in a /sourcemirror directory; both at the root of
an image (VM or container image).

Usage example within a Pipeline:

def analyze_licenses_and_sources(self):
    util.flag_compliance_files(self.project)
    util.analyze_compliance_licenses(self.project)
"""


def flag_compliance_files(project):
    """Flag compliance files status for the provided `project`."""
    compliance_dirs = {
        "/licenses": flag.COMPLIANCE_LICENSES,
        "/sourcemirror": flag.COMPLIANCE_SOURCEMIRROR,
    }

    qs = project.codebaseresources.no_status()

    for path, status in compliance_dirs.items():
        qs.filter(rootfs_path__startswith=path).update(status=status)


def analyze_compliance_licenses(project):
    """Scan compliance licenses status for the provided `project`."""
    qs = project.codebaseresources.status(flag.COMPLIANCE_LICENSES)

    for codebase_resource in qs:
        scan_results, scan_errors = scancode.scan_file(codebase_resource.location)
        codebase_resource.set_scan_results(scan_results)


def group_compliance_alerts_by_severity(queryset):
    """
    Group compliance alerts by their severity for a given queryset.

    This function iterates through a queryset of instances, grouping each instance
    by its compliance alert severity level. It returns a dictionary where each key
    is a severity level (e.g., "error", "warning"), and the value is a list of
    string representations of the instances associated with that severity.
    """
    compliance_alerts = defaultdict(list)
    severity_levels = ComplianceAlertMixin.COMPLIANCE_SEVERITY_MAP

    for instance in queryset:
        compliance_alerts[instance.compliance_alert].append(str(instance))

    # Sort keys for consistent ordering (["error", "warning", "missing"])
    sorted_keys = sorted(
        compliance_alerts.keys(),
        key=lambda label: severity_levels.get(label, len(severity_levels)),
        reverse=True,
    )

    sorted_compliance_alerts = {
        label: compliance_alerts[label] for label in sorted_keys
    }
    return sorted_compliance_alerts


def get_project_compliance_alerts(project, fail_level="error"):
    """
    Retrieve compliance alerts for a given project at a specified severity level.

    This function checks for compliance alerts in the provided project, filtering them
    by the specified severity level (e.g., "error", "warning"). It gathers compliance
    alerts for both discovered packages and codebase resources, and returns them in
    a structured dictionary.
    """
    package_qs = (
        project.discoveredpackages.compliance_issues(severity=fail_level)
        .only(*PACKAGE_URL_FIELDS, "compliance_alert")
        .order_by(*PACKAGE_URL_FIELDS)
    )
    licenses_qs = (
        project.discoveredlicenses.compliance_issues(severity=fail_level)
        .only("identifier", "compliance_alert")
        .order_by("identifier")
    )
    resource_qs = (
        project.codebaseresources.compliance_issues(severity=fail_level)
        .only("path", "compliance_alert")
        .order_by("path")
    )

    queryset_mapping = {
        "packages": package_qs,
        "license_detections": licenses_qs,
        "resources": resource_qs,
    }

    project_compliance_alerts = {
        model_name: compliance_alerts
        for model_name, queryset in queryset_mapping.items()
        if (compliance_alerts := group_compliance_alerts_by_severity(queryset))
    }

    return project_compliance_alerts

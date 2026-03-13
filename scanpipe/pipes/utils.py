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

from license_expression import Licensing

from scanpipe.pipes import flag


def validate_package_license_integrity(project):
    """Validate the correctness of the package license."""
    # Patterns to ignore certain resources during license validation
    ignore_patterns = [
        "*test*",
        "*.sh",
    ]

    for package in project.discoveredpackages.all():
        package_lic = package.get_declared_license_expression()
        if package_lic:
            if package.type == "cargo":
                # A single cargo package only has one Cargo.toml file
                # meaning only one package is defined. Therefore, we don't
                # need to check for the package_uid
                package_uid = None
            else:
                package_uid = package.package_uid
            resources = project.codebaseresources.has_license_expression()
            detected_lic_list = collect_detected_licenses(
                resources, ignore_patterns, package_uid
            )

            if detected_lic_list:
                lic_exp = " AND ".join(detected_lic_list)
                detected_lic_exp = str(Licensing().dedup(lic_exp))
                # The package license is not in sync with detected license(s)
                if detected_lic_exp != package_lic:
                    package.update_extra_data(
                        {
                            "issue": "License Mismatch",
                            "declared_license": package_lic,
                            "detecte_codebase_license": detected_lic_exp,
                        }
                    )
                    for datafile_path in package.datafile_paths:
                        if not datafile_path.startswith("https://"):
                            data_path = project.codebaseresources.get(
                                path=datafile_path
                            )
                            data_path.update(status=flag.LICENSE_ISSUE)
                            data_path.update_extra_data(
                                {
                                    "declared_license": package_lic,
                                    "detecte_codebase_license": detected_lic_exp,
                                }
                            )


def contains_ignore_pattern(resource_path, ignore_patterns):
    """Check if the resource path matches any of the ignore patterns."""
    from fnmatch import fnmatch

    for pattern in ignore_patterns:
        if fnmatch(resource_path, pattern):
            return True
    return False


def collect_detected_licenses(resources, ignore_patterns, package_uid=None):
    """Collect detected licenses from resources, ignoring specified patterns."""
    detected_lic_list = []
    for resource in resources:
        if contains_ignore_pattern(resource.path, ignore_patterns):
            continue

        # If a package_uid is provided, only consider resources linked to it
        if package_uid and package_uid not in resource.for_packages:
            continue

        lic = resource.detected_license_expression
        if lic and lic != "unknown" and lic not in detected_lic_list:
            detected_lic_list.append(lic)
    return detected_lic_list

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

import sys

from attributecode.model import About
from packagedcode import APPLICATION_PACKAGE_DATAFILE_HANDLERS
from packageurl import PackageURL
from python_inspector.resolve_cli import resolver_api

from scanpipe.models import DiscoveredPackage

"""
Utilities to resolve packages from manifest, lockfile, and SBOM.
"""


def resolve_pypi_packages(input_location):
    """
    Resolve the PyPI packages from the `input_location` requirements file.
    """
    python_version = f"{sys.version_info.major}{sys.version_info.minor}"
    operating_system = "linux"

    inspector_output = resolver_api(
        requirement_files=[input_location],
        python_version=python_version,
        operating_system=operating_system,
        prefer_source=True,
    )

    return inspector_output.packages


def resolve_about_packages(input_location):
    """
    Resolve the packages from the `input_location` .ABOUT file.
    """
    about = About(location=input_location)
    about_data = about.as_dict()

    if package_url := about_data.get("package_url"):
        package_url_data = PackageURL.from_string(package_url).to_dict(encode=True)
        for field_name, value in package_url_data.items():
            if value:
                about_data[field_name] = value

    package_data = DiscoveredPackage.clean_data(about_data)
    return [package_data]


def get_default_package_type(input_location):
    """
    Return the package type associated with the provided `input_location`.
    This type is used to get the related handler that knows how process the input.
    """
    for handler in APPLICATION_PACKAGE_DATAFILE_HANDLERS:
        if handler.is_datafile(input_location):
            return handler.default_package_type


# Mapping between the `default_package_type` its related resolver function
resolver_registry = {
    "about": resolve_about_packages,
    "pypi": resolve_pypi_packages,
}

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

import logging

from license_expression import Licensing
from packagedcode import debian_copyright
from scanpipe.models import DiscoveredPackage
from scanpipe.pipelines import Pipeline

logger = logging.getLogger(__name__)


def re_qualify_debian_package_license(project):
    """
    Given a `project` Project, visit all the "deb" DiscoveredPackage; get the
    "copyright" files for the package; re-run license detection on the copyright
    file; if we have a primary license detected, update the package
    license_expression to separate the primary license from other licenses.
    """
    licensing = Licensing()

    packages = DiscoveredPackage.objects.filter(project=project, type="deb")
    for i, package in enumerate(packages):
        if (
            not package.license_expression
            or len(licensing.license_keys(package.license_expression)) == 1
        ):
            continue

        copyright_resources = package.codebase_resources.filter(name="copyright")
        for resource in copyright_resources:
            copyright_location = str(resource.location_path.absolute())

            try:
                dc = debian_copyright.parse_copyright_file(copyright_location)
                if dc:
                    primary_license = dc.primary_license
                    if primary_license:
                        license_expression = dc.get_license_expression(
                            skip_debian_packaging=True,
                            simplify_licenses=True,
                        )
                        if primary_license != license_expression:
                            full_expression = f"{primary_license} | {license_expression}"
                            package.license_expression = full_expression
                            package.save()

                            logger.info(f"Updating license for package #{i}: {package.purl}")

            except:
                logger.info(f"Failed to detect copyright license for package #{i}: {package.purl}")
                raise


class CollectDebianPrimaryLicense(Pipeline):
    """
    A pipeline to enhance a codebase that contains Debian systenm packages by
    reprocessing the detected license expression such that we have can discern
    primary from other licenses as in:

        "<primary expression> | <other expressions>".

    The "|" pipe is used as a separator.
    """

    @classmethod
    def steps(cls):
        return (
            cls.collect_debian_primary_license,
        )

    def collect_debian_primary_license(self):
        """
        Update debian packages license expressions.
        """
        re_qualify_debian_package_license(self.project)

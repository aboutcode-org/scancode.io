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
from pathlib import Path

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.pipelines import Pipeline

logger = logging.getLogger(__name__)


def add_pypi_packages_installed_files(project):
    """
    Given a `project` Project visit all the "pypi" DiscoveredPackage; collect
    the list of installed files from RECORD files and the corresponding
    CodebaseResource; and relate these CodebaseResource to its
    DiscoveredPackage.
    """
    packages = DiscoveredPackage.objects.filter(project=project, type="pypi")

    project_resources = CodebaseResource.objects.filter(project=project)

    from importlib_metadata import Distribution

    resources_by_path = {}

    for i, package in enumerate(packages):
        resources = package.codebase_resources.filter(name="METADATA")

        missing_resources = package.missing_resources[:]

        for resource in resources:
            # terrible hack where we keep a mapping of all the resources under a
            # site-packages directory keyed by absolute path
            if not resources_by_path:
                respath = Path(str(resource.path).strip("/"))
                site_packages_path = respath.parent.parent
                site_packages_res = project_resources.filter(path__startswith=site_packages_path)

                for sr in site_packages_res:
                    absloc = sr.location_path.resolve().absolute()
                    resources_by_path[absloc] = sr

            # location_path is a pathlib.Path
            reslocpath = resource.location_path
            dist_info_dir = reslocpath.parent
            installed_dist = Distribution.at(dist_info_dir)
            purl = package.purl
            logger.info(f"Adding resources for package #{i}: {purl}")

            for f, installed_file in enumerate(installed_dist.files, 1):
                installed_file_abspath = installed_file.locate().absolute()
                # installed_file = installed_file.hash
                # if not installed_file:
                #     continue
                installed_resource = resources_by_path.get(installed_file_abspath)
                if not installed_resource:
                    # TODO: the path is not right
                    missing_resources.append(installed_file_abspath)
                    logger.info(f"      PyPI installed file is missing: {installed_file_abspath}")
                else:
                    # update the model to relate this to it package AND update the status
                    if package not in installed_resource.discovered_packages.all():
                        installed_resource.discovered_packages.add(package)
                        installed_resource.status = "application-package"
                        logger.info(f"      added as application-package to: {purl}")
                        installed_resource.save()
                        package.save()

            logger.info(f"Added #{f} resources for package #{i}: {purl}")


class AddFilesToPackages(Pipeline):
    """
    A pipeline to enhance a codebase by relating packages to their files (and
    reciprocally). This is designed to work after an existing codebase scan.
    """

    @classmethod
    def steps(cls):
        return (cls.find_application_package_files,)

    def find_application_package_files(self):
        """
        Create the relationships between a package and its files.
        """
        file_adders = [add_pypi_packages_installed_files]
        for file_adder in file_adders:
            file_adder(self.project)

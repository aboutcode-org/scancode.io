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

from scanpipe.models import DiscoveredPackage
from scanpipe.pipelines import Pipeline
from pathlib import Path
from scanpipe.models import CodebaseResource

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
        resources = package.codebase_resources.all()
        if len(resources) != 1:
            continue

        resource = resources[0]

        if resource.name != "METADATA":
            continue

        if not resources_by_path:
            respath = Path(str(resource.path).strip("/"))
            site_packages_path = respath.parent.parent
            site_packages_res = project_resources.get(path=site_packages_path)

            for sr in site_packages_res.walk():
                absloc = sr.location_path.resolve().absolute()
                resources_by_path[absloc] = sr

        reslocpath = resource.location_path
        dist_info_dir = reslocpath.parent
        installed_dist = Distribution.at(dist_info_dir)
        purl = package.purl
        logger.info(f"Adding resources for package #{i}: {purl}")

        for f, installed_file in enumerate(installed_dist.files, 1):
            if_abspath = installed_file.locate().absolute()
            # if_hash = installed_file.hash
            # if not if_hash:
            #     continue
            installed_resource = resources_by_path.get(if_abspath)
            if not installed_resource:
                assert str(if_abspath).endswith(".pyc"), f"PyPI package is missing path: {if_abspath}"
            else:
                # update the model to relate this to it package AND update the status
                if package not in installed_resource.discovered_packages.all():
                    installed_resource.discovered_packages.add(package)
                    installed_resource.status = "application-package"
                    logger.info(f"      added as application-package to: {purl}")
                    installed_resource.save()
                    package.save()

                    # rootfs_path = pipes.normalize_path(install_file.path)
                    # logger.info(f"   installed file rootfs_path: {rootfs_path}")
                    #
                    # try:
                    #     codebase_resource = codebase_resources.get(
                    #         rootfs_path=rootfs_path,
                    #     )
                    # except ObjectDoesNotExist:
                    #     if rootfs_path not in missing_resources:
                    #         missing_resources.append(rootfs_path)
                    #     logger.info(f"      installed file is missing: {rootfs_path}")
                    #     continue
                    #
                    #
                    # if has_hash_diff(install_file, codebase_resource):
                    #     if install_file.path not in modified_resources:
                    #         modified_resources.append(install_file.path)
                    #
                    # package.missing_resources = missing_resources
                    # package.modified_resources = modified_resources
                    # package.save()

        logger.info(f"Added #{f} resources for package #{i}: {purl}")


class AddFilesToPackages(Pipeline):
    """
    A pipeline to enhance a codebase by relating packages to their files (and
    reciprocally). This is designed to work after an existing codebase scan.
    """

    @classmethod
    def steps(cls):
        return (
            cls.find_application_package_files,
        )

    def find_application_package_files(self):
        """
        Create the relationships between a package and its files.
        """
        file_adders = [add_pypi_packages_installed_files]
        for file_adder in file_adders:
            file_adder(self.project)

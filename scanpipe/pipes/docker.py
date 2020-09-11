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
import posixpath
from functools import partial
from pathlib import Path

from container_inspector.image import Image
from container_inspector.rootfs import get_whiteout_marker_type

from scanpipe import pipes
from scanpipe.models import CodebaseResource
from scanpipe.pipes import rootfs

logger = logging.getLogger(__name__)


def get_images_from_extracted_codebase(project):
    """
    Yield images collected from the project "codebase" directory. The
    image tarball should be extracted there first, with its manifest.json at the
    root.
    """
    codebase = project.codebase_path.absolute()
    for image in Image.get_images_from_dir(location=codebase):
        yield image


def get_and_extract_images_from_image_tarballs(project, force_extract=False):
    """
    Yield images collected from the project "codebase" directory.
    The process is to:
    1. collect all the tarballs from this directory.
    2. for each, extract that under a -extract directory and collect its images.

    If `force_extract` is False, do not extract if already extracted.
    """
    all_images = []

    for tarball in project.inputs(pattern="*.tar*"):
        tarball_location = str(tarball.absolute())
        if tarball_location.endswith("-extract"):
            continue
        extracted_location = tarball_location + "-extract"
        tarball_images = Image.get_images_from_tarball(
            location=tarball_location,
            target_dir=extracted_location,
            force_extract=force_extract,
        )

        for image in tarball_images:
            logger.info("Collected Docker image: {}".format(image.image_id))
            all_images.append(image)

    return all_images


def get_image_data(image):
    """
    Return a mapping of Image-related data given an `image`.
    """
    exclude = ["base_location", "extracted_to_location", "layers"]
    image_data = {
        key: value for key, value in image.to_dict().items() if key not in exclude
    }
    return image_data


def create_codebase_resources(project, image):
    """
    Create the CodebaseResource for an `image` in `project`.
    """
    for layer_resource in image.get_layers_resources():
        pipes.make_codebase_resource(
            project=project,
            location=layer_resource.location,
            rootfs_path=layer_resource.path,
        )


def scan_image_for_system_packages(project, image, detect_licenses=True):
    """
    Given a `project` and an `image`, scan the `image` layer by layer for
    installed system packages. Create a DiscoveredPackage for each.

    Then for each installed DiscoveredPackage installed file, check if it exists
    as a CodebaseResource and relate that CodebaseResource to its
    DiscoveredPackage or keep that as a missing file.
    """
    distro_id = image.distro.identifier

    if distro_id not in rootfs.PACKAGE_GETTER_BY_DISTRO:
        raise NotImplementedError(f'Distro "{distro_id}" is not supported.')

    package_getter = partial(
        rootfs.PACKAGE_GETTER_BY_DISTRO[distro_id],
        distro=distro_id,
        detect_licenses=detect_licenses,
    )

    installed_packages = image.get_installed_packages(package_getter)

    for i, (purl, package, layer) in enumerate(installed_packages):
        logger.info(f"Creating package #{i}: {purl}")
        created_package = pipes.update_or_create_package(project, package.to_dict())

        # We have no files for this installed package, we cannot go further.
        if not package.installed_files:
            logger.info(f"  No installed_files for: {purl}")
            continue

        missing_resources = created_package.missing_resources[:]
        modified_resources = created_package.modified_resources[:]

        codebase_resources = CodebaseResource.objects.project(project)

        for install_file in package.installed_files:
            install_file_path = pipes.normalize_path(install_file.path)
            layer_rootfs_path = posixpath.join(
                layer.layer_id,
                install_file_path.strip("/"),
            )
            logger.info(f"   installed file rootfs_path: {install_file_path}")
            logger.info(f"   layer rootfs_path: {layer_rootfs_path}")
            cbr_qs = codebase_resources.filter(
                path__endswith=layer_rootfs_path,
                rootfs_path=install_file_path,
            )
            found_res = False
            for codebase_resource in cbr_qs:
                found_res = True
                if created_package not in codebase_resource.discovered_packages.all():
                    codebase_resource.discovered_packages.add(created_package)
                    codebase_resource.status = "system-package"
                    logger.info(f"      added as system-package to: {purl}")
                    codebase_resource.save()

                if (
                    (
                        install_file.sha512
                        and codebase_resource.sha512
                        and codebase_resource.sha512 != install_file.sha512
                    )
                    or (
                        install_file.sha256
                        and codebase_resource.sha256
                        and codebase_resource.sha256 != install_file.sha256
                    )
                    or (
                        install_file.sha1
                        and codebase_resource.sha1
                        and codebase_resource.sha1 != install_file.sha1
                    )
                    or (
                        install_file.md5
                        and codebase_resource.md5
                        and codebase_resource.md5 != install_file.md5
                    )
                ):
                    # Alpine uses SHA1 while Debian uses MD5, we prefer te strongest
                    # hash that's present
                    if install_file.path not in modified_resources:
                        modified_resources.append(install_file.path)

            if not found_res and install_file_path not in missing_resources:
                missing_resources.append(install_file_path)
                logger.info(f"      installed file is missing: {install_file_path}")

        created_package.missing_resources = missing_resources
        created_package.modified_resources = modified_resources
        created_package.save()


def tag_whiteout_codebase_resources(project):
    """
    Mark overlayfs/AUFS whiteout special files CodebaseResource as "ignored".
    """
    qs = project.codebaseresources.no_status()

    for codebase_resource in qs:
        filename = Path(codebase_resource.path).name
        if get_whiteout_marker_type(filename):
            codebase_resource.status = "ignored-whiteout"
            codebase_resource.save()

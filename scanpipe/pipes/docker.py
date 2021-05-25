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

from scanpipe import pipes
from scanpipe.pipes import rootfs
from scanpipe.pipes import scancode
from scanpipe.pipes.rootfs import has_hash_diff

logger = logging.getLogger(__name__)


def extract_images_from_inputs(project):
    """
    Collects all the tarballs from the `project` input/ work directory, extracts each
    tarball to the tmp/ work directory and collects the images.
    Returns the `images` and `errors` that may have happen during the extraction.
    """
    target_path = project.tmp_path
    images = []
    errors = []

    for input_tarball in project.inputs(pattern="*.tar*"):
        extract_target = target_path / f"{input_tarball.name}-extract"
        extract_errors = scancode.extract(input_tarball, extract_target)
        images.extend(Image.get_images_from_dir(extract_target))
        errors.extend(extract_errors)

    return images, errors


def extract_layers_from_images(project, images):
    """
    Extracts all layers from the provided `images` into the `project` codebase/ work
    directory.
    Returns the `errors` that may happen during the extraction.
    """
    errors = []
    # FIXME: use container-inspector extract instead
    for image in images:
        image_dirname = Path(image.extracted_location).name
        target_path = project.codebase_path / image_dirname

        for layer in image.layers:
            extract_target = target_path / layer.layer_id
            extract_errors = scancode.extract(layer.archive_location, extract_target)
            errors.extend(extract_errors)
            layer.extracted_location = str(extract_target)


def get_image_data(image):
    """
    Returns a mapping of image-related data given an `image`.
    """
    exclude = ["extracted_location", "archive_location", "layers"]
    image_data = {
        key: value for key, value in image.to_dict().items() if key not in exclude
    }
    return image_data


def create_codebase_resources(project, image):
    """
    Creates the CodebaseResource for an `image` in a `project`.
    """
    for layer_resource in image.get_layers_resources():
        pipes.make_codebase_resource(
            project=project,
            location=layer_resource.location,
            rootfs_path=layer_resource.path,
        )


def scan_image_for_system_packages(project, image, detect_licenses=True):
    """
    Given a `project` and an `image` - this scans the `image` layer by layer for
    installed system packages and creates a DiscoveredPackage for each.

    Then for each installed DiscoveredPackage file, check if it exists
    as a CodebaseResource. If exists, relate that CodebaseResource to its
    DiscoveredPackage; otherwise, keep that as a missing file.
    """
    if not image.distro:
        raise rootfs.DistroNotFound(f"Distro not found.")

    distro_id = image.distro.identifier
    if distro_id not in rootfs.PACKAGE_GETTER_BY_DISTRO:
        raise rootfs.DistroNotSupported(f'Distro "{distro_id}" is not supported.')

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

        codebase_resources = project.codebaseresources.all()

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

                if has_hash_diff(install_file, codebase_resource):
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
    Marks overlayfs/AUFS whiteout special files CodebaseResource as "ignored-whiteout".
    See https://github.com/opencontainers/image-spec/blob/master/layer.md#whiteouts
    for details.
    """
    whiteout_prefix = ".wh."
    qs = project.codebaseresources.no_status()
    qs.filter(name__startswith=whiteout_prefix).update(status="ignored-whiteout")

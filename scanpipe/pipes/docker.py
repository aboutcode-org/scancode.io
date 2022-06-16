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
from pathlib import Path

from container_inspector.image import Image
from container_inspector.utils import extract_tar

from scanpipe import pipes
from scanpipe.pipes import rootfs

logger = logging.getLogger(__name__)


def extract_images_from_inputs(project):
    """
    Collects all the tarballs from the `project` input/ work directory, extracts
    each tarball to the tmp/ work directory and collects the images.

    Returns the `images` and an `errors` list of error messages that may have
    happen during the extraction.
    """
    target_path = project.tmp_path
    images = []
    errors = []

    for input_tarball in project.inputs(pattern="*.tar*"):
        extract_target = target_path / f"{input_tarball.name}-extract"
        imgs, errs = extract_image_from_tarball(input_tarball, extract_target)
        images.extend(imgs)
        errors.extend(errs)

    return images, errors


def extract_image_from_tarball(input_tarball, extract_target, verify=True):
    """
    Extract images from an ``input_tarball`` to an ``extract_target`` directory
    Path object and collects the extracted images.

    Returns the `images` and an `errors` list of error messages that may have
    happen during the extraction.
    """
    errors = extract_tar(location=input_tarball, target_dir=extract_target)
    images = Image.get_images_from_dir(
        extracted_location=str(extract_target),
        verify=verify,
    )
    return images, errors


def extract_layers_from_images(project, images):
    """
    Extracts all layers from the provided `images` into the `project` codebase
    work directory.

    Returns an `errors` list of error messages that may occur during the
    extraction.
    """
    return extract_layers_from_images_to_base_path(
        base_path=project.codebase_path,
        images=images,
    )


def extract_layers_from_images_to_base_path(base_path, images):
    """
    Extracts all layers from the provided `images` into the `base_path` work
    directory.

    Returns an `errors` list of error messages that may occur during the
    extraction.
    """
    errors = []
    base_path = Path(base_path)

    for image in images:
        image_dirname = Path(image.extracted_location).name
        target_path = base_path / image_dirname

        for layer in image.layers:
            extract_target = target_path / layer.layer_id
            extract_errors = extract_tar(
                location=layer.archive_location,
                target_dir=extract_target,
            )
            errors.extend(extract_errors)
            layer.extracted_location = str(extract_target)

    return errors


def get_image_data(image, layer_path_segments=2):
    """
    Returns a mapping of image-related data given an `image`.
    Keep only ``layer_path_segments`` trailing layer location segments (or keep
    the locations unmodified if ``layer_path_segments`` is 0).
    """
    exclude_from_img = ["extracted_location", "archive_location"]
    image_data = {
        key: value
        for key, value in image.to_dict(layer_path_segments=layer_path_segments).items()
        if key not in exclude_from_img
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
    if distro_id not in rootfs.SUPPORTED_DISTROS:
        raise rootfs.DistroNotSupported(f'Distro "{distro_id}" is not supported.')

    installed_packages = image.get_installed_packages(rootfs.package_getter)

    for i, (purl, package, layer) in enumerate(installed_packages):
        logger.info(f"Creating package #{i}: {purl}")
        created_package = pipes.update_or_create_package(project, package.to_dict())

        installed_files = []
        if hasattr(package, "resources"):
            installed_files = package.resources

        # We have no files for this installed package, we cannot go further.
        if not installed_files:
            logger.info(f"  No installed_files for: {purl}")
            continue

        missing_resources = created_package.missing_resources[:]
        modified_resources = created_package.modified_resources[:]

        codebase_resources = project.codebaseresources.all()

        for install_file in installed_files:
            install_file_path = install_file.get_path(strip_root=True)
            install_file_path = pipes.normalize_path(install_file_path)
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

                if rootfs.has_hash_diff(install_file, codebase_resource):
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

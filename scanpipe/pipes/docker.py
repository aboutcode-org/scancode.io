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

import logging
import posixpath
import re
import tarfile
import threading
from collections import namedtuple
from contextlib import contextmanager
from contextlib import nullcontext
from pathlib import Path

from commoncode.system import py314
from container_inspector.image import Image
from container_inspector.utils import extract_tar
from extractcode import EXTRACT_SUFFIX

from scanpipe import pipes
from scanpipe.pipes import flag
from scanpipe.pipes import rootfs

logger = logging.getLogger(__name__)

# A layer ID is the SHA256 of the layer archive, used as its extraction directory.
LAYER_ID_REGEX = re.compile(r"[0-9a-f]{64}")


def tar_filter_with_safe_hardlinks(member, dest_path):
    """
    Apply the ``tar`` extraction filter, and refuse a hard link to a file outside
    of the ``dest_path`` extraction directory: the ``tar`` filter does not check
    the hard link targets, so an image could link any file of the server.
    """
    member = tarfile.tar_filter(member, dest_path)
    if member.islnk():
        return tarfile.data_filter(member, dest_path)
    return member


# Serializes the changes of the ``TarFile.extraction_filter`` class attribute,
# shared by all the threads of the process.
extraction_filter_lock = threading.Lock()


@contextmanager
def default_extraction_filter(extraction_filter):
    """
    Set the ``extraction_filter`` as the ``tarfile`` default filter, used when
    ``extract()`` is called without filter, and restore the previous one on exit.
    """
    with extraction_filter_lock:
        previous_filter = vars(tarfile.TarFile)["extraction_filter"]
        tarfile.TarFile.extraction_filter = staticmethod(extraction_filter)
        try:
            yield
        finally:
            tarfile.TarFile.extraction_filter = previous_filter


def extract_tar_safely(location, target_dir):
    """
    Extract the tarball at ``location`` to ``target_dir`` with the
    ``tar_filter_with_safe_hardlinks`` filter, on all Python versions.

    container_inspector only passes its ``tar_filter`` on Python 3.14. On older
    versions, it extracts without filter and ``tarfile`` uses its default filter,
    "fully_trusted": a member could be written outside of ``target_dir`` through a
    symlink.
    """
    if py314:
        filter_context = nullcontext()
    else:
        filter_context = default_extraction_filter(tar_filter_with_safe_hardlinks)

    with filter_context:
        return extract_tar(
            location=location,
            target_dir=target_dir,
            skip_symlinks=False,
            as_events=False,
            tar_filter=tar_filter_with_safe_hardlinks,
        )


def get_tarballs_from_inputs(project):
    """
    Return the tarballs from the `project` input/ work directory.
    Supported file extensions: `.tar`, `.tar.gz`, `.tgz`.
    """
    return [
        tarball
        for pattern in ("*.tar*", "*.tgz")
        for tarball in project.inputs(pattern=pattern)
    ]


def extract_images_from_inputs(project):
    """
    Collect all the tarballs from the `project` input/ work directory, extracts
    each tarball to the tmp/ work directory and collects the images.

    Return the `images` and an `errors` list of error messages that may have
    happened during the extraction.
    """
    target_path = project.tmp_path
    images = []
    errors = []

    for tarball in get_tarballs_from_inputs(project):
        extract_target = target_path / f"{tarball.name}{EXTRACT_SUFFIX}"
        imgs, errs = extract_image_from_tarball(tarball, extract_target)
        images.extend(imgs)
        errors.extend(errs)

    return images, errors


def extract_image_from_tarball(input_tarball, extract_target, verify=False):
    """
    Extract images from an ``input_tarball`` to an ``extract_target`` directory
    Path object and collects the extracted images.

    Return the `images` and an `errors` list of error messages that may have
    happened during the extraction.
    """
    errors = extract_tar_safely(location=input_tarball, target_dir=extract_target)
    images = Image.get_images_from_dir(
        extracted_location=str(extract_target),
        verify=verify,
    )

    valid_images = []
    for image in images:
        if layer_errors := get_layer_errors(image, extract_target):
            errors.extend(layer_errors)
            continue
        valid_images.append(image)

    return valid_images, errors


def get_layer_errors(image, extract_target):
    """
    Return the error messages for the ``image`` layers with an ID that is not a
    SHA256, or with an archive outside of the ``extract_target`` directory. The
    layer IDs and archive paths come from the image config and manifest files: a
    forged image could extract a layer, or read a tarball, anywhere on the server.
    """
    extract_path = Path(extract_target).resolve()
    errors = []

    for layer in image.layers:
        layer_id = layer.layer_id or ""
        if not LAYER_ID_REGEX.fullmatch(layer_id):
            errors.append(f"Invalid layer ID: {layer_id}")

        archive_path = Path(layer.archive_location).resolve()
        if not archive_path.is_relative_to(extract_path):
            errors.append(f"Layer {layer_id} archive is outside of the image.")

    return errors


def extract_layers_from_images(project, images):
    """
    Extract all layers from the provided `images` into the `project` codebase
    work directory.

    Return an `errors` list of error messages that may occur during the
    extraction.
    """
    return extract_layers_from_images_to_base_path(
        base_path=project.codebase_path,
        images=images,
    )


def extract_layers_from_images_to_base_path(base_path, images):
    """
    Extract all layers from the provided `images` into the `base_path` work
    directory.

    Return an `errors` list of error messages that may occur during the
    extraction.
    """
    errors = []
    base_path = Path(base_path)
    resolved_base_path = base_path.resolve()

    for image in images:
        image_dirname = Path(image.extracted_location).name
        target_path = base_path / image_dirname

        for layer in image.layers:
            extract_target = target_path / layer.layer_id
            # The codebase can already contain a symlink in place of the image or
            # layer directory, for example from a cloned Git repository input.
            if not extract_target.resolve().is_relative_to(resolved_base_path):
                error_msg = f"Layer {layer.layer_id} target is outside of the codebase."
                raise ValueError(error_msg)

            extract_errors = extract_tar_safely(
                location=layer.archive_location, target_dir=extract_target
            )
            errors.extend(extract_errors)
            layer.extracted_location = str(extract_target)

    return errors


def get_image_data(image, layer_path_segments=2):
    """
    Return a mapping of image-related data given an `image`.
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


def get_layer_tag(image_id, layer_id, layer_index, id_length=6):
    """
    Return a "tag" crafted from the provided `image_id`, `layer_id`, and `layer_index`.
    The purpose of this tag is to be short, clear and sortable.

    For instance, given an image with an id:
        785df58b6b3e120f59bce6cd10169a0c58b8837b24f382e27593e2eea011a0d8

    and two layers from bottom to top as:
        0690c89adf3e8c306d4ced085fc16d1d104dcfddd6dc637e141fa78be242a707
        7a1d89d2653e8e4aa9011fd95034a4857109d6636f2ad32df470a196e5dd1585

    we would get these two tags:
        img-785df5-layer-01-0690c8
        img-785df5-layer-02-7a1d89
    """
    short_image_id = image_id[:id_length]
    short_layer_id = layer_id[:id_length]
    return f"img-{short_image_id}-layer-{layer_index:02}-{short_layer_id}"


def create_codebase_resources(project, image: Image) -> None:
    """
    Create codebase resources for the provided image and its layers.

    Creates a codebase resource for the extracted image root directory and each
    extracted layer directory, ensuring the structure is properly indexed for tree
    rendering.

    Args:
        project: The project instance.
        image: The image object with the extracted_location attribute.

    """
    pipes.make_codebase_resource(
        project=project,
        location=str(project.codebase_path / Path(image.extracted_location).name),
    )

    for layer_index, layer in enumerate(image.layers, start=1):
        layer_tag = get_layer_tag(image.image_id, layer.layer_id, layer_index)

        for resource in layer.get_resources(with_dir=True):
            pipes.make_codebase_resource(
                project=project,
                location=resource.location,
                rootfs_path=resource.path,
                tag=layer_tag,
            )

        layer_data = layer.to_dict()
        layer_data.pop("extracted_location", None)
        layer_data.pop("archive_location", None)
        pipes.make_codebase_resource(
            project=project,
            location=str(layer.extracted_location),
            tag=layer_tag,
            # Store the layer data in the extra_data for display in the UI
            extra_data={"layer": layer_data},
        )


def create_system_package(project, purl, package, layer, layer_tag):
    """Create system package and related resources."""
    package_data = package.to_dict()
    package_data["tag"] = layer_tag
    created_package = pipes.update_or_create_package(project, package_data)

    installed_files = []
    if hasattr(package, "resources"):
        installed_files = package.resources

    # We have no files for this installed package, we cannot go further.
    if not installed_files:
        logger.info(f"  No installed_files for: {purl}")
        return

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
        resource_qs = codebase_resources.filter(
            path__endswith=layer_rootfs_path,
            rootfs_path=install_file_path,
        )
        found_resource = False
        for resource in resource_qs:
            found_resource = True
            if created_package not in resource.discovered_packages.all():
                resource.discovered_packages.add(created_package)
                resource.update(status=flag.SYSTEM_PACKAGE)
                logger.info(f"      added as system-package to: {purl}")

            if rootfs.has_hash_diff(install_file, resource):
                if install_file.path not in modified_resources:
                    modified_resources.append(install_file.path)

        if not found_resource and install_file_path not in missing_resources:
            missing_resources.append(install_file_path)
            logger.info(f"      installed file is missing: {install_file_path}")

    created_package.update(
        missing_resources=missing_resources,
        modified_resources=modified_resources,
    )


def scan_image_for_system_packages(project, image):
    """
    Given a `project` and an `image` - this scans the `image` layer by layer for
    installed system packages and creates a DiscoveredPackage for each.

    Then for each installed DiscoveredPackage file, check if it exists
    as a CodebaseResource. If exists, relate that CodebaseResource to its
    DiscoveredPackage; otherwise, keep that as a missing file.
    """
    if not image.distro:
        raise rootfs.DistroNotFound("Distro not found.")

    distro_id = image.distro.identifier
    if distro_id not in rootfs.SUPPORTED_DISTROS:
        raise rootfs.DistroNotSupported(f'Distro "{distro_id}" is not supported.')

    layer_index_mapping = {
        layer.layer_id: index for index, layer in enumerate(image.layers, start=1)
    }

    installed_packages = image.get_installed_packages(rootfs.package_getter)
    for package_index, (purl, package, layer) in enumerate(installed_packages):
        logger.info(f"Creating package #{package_index}: {purl}")
        layer_index = layer_index_mapping.get(layer.layer_id)
        layer_tag = get_layer_tag(image.image_id, layer.layer_id, layer_index)
        create_system_package(project, purl, package, layer, layer_tag)


def flag_whiteout_codebase_resources(project):
    """
    Tag overlayfs/AUFS whiteout special files CodebaseResource as "ignored-whiteout".
    See https://github.com/opencontainers/image-spec/blob/master/layer.md#whiteouts
    for details.
    """
    whiteout_prefix = ".wh."
    qs = project.codebaseresources.no_status()
    qs.filter(name__startswith=whiteout_prefix).update(status=flag.IGNORED_WHITEOUT)


layer_fields = [
    "layer_tag",
    "created_by",
    "layer_id",
    "image_id",
    "created",
    "size",
    "author",
    "comment",
    "archive_location",
]
Layer = namedtuple("Layer", layer_fields)


def get_layers_data(project):
    """Get list of structured layers data from project extra_data field."""
    layers_data = []

    images = project.extra_data.get("images", [])
    if not isinstance(images, list):
        return []

    for image in images:
        image_id = image.get("image_id")

        for layer_index, layer in enumerate(image.get("layers", []), start=1):
            layer_id = layer.get("layer_id")
            layers_data.append(
                Layer(
                    layer_tag=get_layer_tag(image_id, layer_id, layer_index),
                    created_by=layer.get("created_by"),
                    layer_id=layer_id,
                    image_id=image_id,
                    created=layer.get("created"),
                    size=layer.get("size"),
                    author=layer.get("author"),
                    comment=layer.get("comment"),
                    archive_location=layer.get("archive_location"),
                )
            )

    return layers_data

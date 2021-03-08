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

from pathlib import Path

from container_inspector.image import Image

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import docker
from scanpipe.pipes import rootfs
from scanpipe.pipes import scancode


class Docker(Pipeline):
    """
    A pipeline to analyze a Docker image.
    """

    def extract_images(self):
        """
        Extract the images from tarballs.
        """
        target_path = self.project.tmp_path
        extract_errors = []
        all_images = []

        for input_tarball in self.project.inputs(pattern="*.tar*"):
            extract_target = target_path / f"{input_tarball.name}-extract"
            errors = scancode.extract(input_tarball, extract_target)
            extract_errors.extend(errors)
            all_images.extend(Image.get_images_from_dir(extract_target))

        if extract_errors:
            self.add_error("\n".join(extract_errors))

        self.images = all_images

    def extract_layers(self):
        """
        Extract layers from images.
        """
        extract_errors = []

        for image in self.images:
            image_dirname = Path(image.base_location).name
            target_path = self.project.codebase_path / image_dirname

            for layer in image.layers:
                extract_target = target_path / layer.layer_id
                errors = scancode.extract(layer.layer_location, extract_target)
                extract_errors.extend(errors)
                layer.extracted_to_location = str(extract_target)

        if extract_errors:
            self.add_error("\n".join(extract_errors))

    def find_images_linux_distro(self):
        """
        Find the linux distro of the images.
        """
        for image in self.images:
            image.get_and_set_distro()

    def collect_images_information(self):
        """
        Collect images information and store on project.
        """
        images_data = [docker.get_image_data(image) for image in self.images]
        self.project.extra_data.update({"images": images_data})
        self.project.save()

    def collect_and_create_codebase_resources(self):
        """
        Collect and create all image files as CodebaseResource.
        """
        for image in self.images:
            docker.create_codebase_resources(self.project, image)

    def collect_and_create_system_packages(self):
        """
        Collect installed system packages for each layer based on the distro.
        """
        with self.save_errors(rootfs.DistroNotFound, rootfs.DistroNotSupported):
            for image in self.images:
                docker.scan_image_for_system_packages(self.project, image)

    def tag_uninteresting_codebase_resources(self):
        """
        Flag remaining files not from a system package.
        """
        docker.tag_whiteout_codebase_resources(self.project)
        rootfs.tag_uninteresting_codebase_resources(self.project)

    def scan_for_application_packages(self):
        """
        Scan unknown resources for packages infos.
        """
        scancode.scan_for_application_packages(self.project)

    def scan_for_files(self):
        """
        Scan unknown resources for copyrights, licenses, emails, and urls.
        """
        scancode.scan_for_files(self.project)

    def analyze_scanned_files(self):
        """
        Analyze single file scan results for completeness.
        """
        pipes.analyze_scanned_files(self.project)

    def tag_not_analyzed_codebase_resources(self):
        """
        Check for leftover files for sanity. We should have none.
        """
        pipes.tag_not_analyzed_codebase_resources(self.project)

    steps = (
        extract_images,
        extract_layers,
        find_images_linux_distro,
        collect_images_information,
        collect_and_create_codebase_resources,
        collect_and_create_system_packages,
        tag_uninteresting_codebase_resources,
        scan_for_application_packages,
        scan_for_files,
        analyze_scanned_files,
        tag_not_analyzed_codebase_resources,
    )

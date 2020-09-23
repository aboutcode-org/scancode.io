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

# isort:skip_file

import os

import django

django.setup()

from scanpipe import pipes
from scanpipe.pipelines import Pipeline
from scanpipe.pipelines import step
from scanpipe.pipes import docker as docker_pipes
from scanpipe.pipes import rootfs as rootfs_pipes


class DockerPipeline(Pipeline):
    """
    A pipeline to analyze a Docker image.
    """

    @step
    def start(self):
        """
        Load the Project instance.
        """
        self.project = self.get_project(self.project_name)
        self.next(self.extract_images)

    @step
    def extract_images(self):
        """
        Extract the images from tarballs.
        """
        self.images = docker_pipes.get_and_extract_images_from_image_tarballs(
            self.project
        )
        self.next(self.extract_layers)

    @step
    def extract_layers(self):
        """
        Extract layers from images.
        """
        for image in self.images:
            image_dirname = os.path.basename(image.base_location)
            target_dir = str(self.project.codebase_path / image_dirname)
            image.extract_layers(target_dir=target_dir)
        self.next(self.find_images_linux_distro)

    @step
    def find_images_linux_distro(self):
        """
        Find the linux distro of the images.
        """
        for image in self.images:
            image.get_and_set_distro()
        self.next(self.collect_images_information)

    @step
    def collect_images_information(self):
        """
        Collect images information and store on project.
        """
        images_data = [docker_pipes.get_image_data(image) for image in self.images]
        self.project.extra_data.update({"images": images_data})
        self.project.save()
        self.next(self.collect_and_create_codebase_resources)

    @step
    def collect_and_create_codebase_resources(self):
        """
        Collect and create all image files as CodebaseResource.
        """
        for image in self.images:
            docker_pipes.create_codebase_resources(self.project, image)
        self.next(self.collect_and_create_system_packages)

    @step
    def collect_and_create_system_packages(self):
        """
        Collect installed system packages for each layer based on the distro.
        """
        for image in self.images:
            docker_pipes.scan_image_for_system_packages(self.project, image)
        self.next(self.tag_uninteresting_codebase_resources)

    @step
    def tag_uninteresting_codebase_resources(self):
        """
        Flag remaining files not from a system package.
        """
        docker_pipes.tag_whiteout_codebase_resources(self.project)
        rootfs_pipes.tag_uninteresting_codebase_resources(self.project)
        self.next(self.scan_for_application_packages)

    @step
    def scan_for_application_packages(self):
        """
        Scan unknown resources for packages infos.
        """
        pipes.scan_for_application_packages(self.project)
        self.next(self.scan_for_files)

    @step
    def scan_for_files(self):
        """
        Scan unknown resources for copyrights, licenses, emails, and urls.
        """
        pipes.scan_for_files(self.project)
        self.next(self.analyze_scanned_files)

    @step
    def analyze_scanned_files(self):
        """
        Analyze single file scan results for completeness.
        """
        pipes.analyze_scanned_files(self.project)
        self.next(self.tag_not_analyzed_codebase_resources)

    @step
    def tag_not_analyzed_codebase_resources(self):
        """
        Check for leftover files for sanity. We should have none.
        """
        pipes.tag_not_analyzed_codebase_resources(self.project)
        self.next(self.end)

    @step
    def end(self):
        """
        Analysis completed.
        """


if __name__ == "__main__":
    DockerPipeline()

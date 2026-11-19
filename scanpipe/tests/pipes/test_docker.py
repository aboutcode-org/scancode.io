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

import io
import json
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.apps import apps
from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import Project
from scanpipe.pipes import docker
from scanpipe.pipes.input import copy_inputs
from scanpipe.tests import FIXTURES_REGEN

scanpipe_app = apps.get_app_config("scanpipe")


class ScanPipeDockerPipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"
    maxDiff = None

    def assertResultsEqual(self, expected_file, results, regen=FIXTURES_REGEN):
        """Set `regen` to True to regenerate the expected results."""
        if regen:
            expected_file.write_text(results)

        expected_data = expected_file.read_text()
        self.assertEqual(expected_data, results)

    def test_pipes_docker_get_image_data_contains_layers_with_relative_paths(self):
        extract_target = str(Path(tempfile.mkdtemp()) / "tempdir")
        input_tarball = str(self.data / "docker" / "docker-images.tar.gz")

        # Extract the image first
        images, errors = docker.extract_image_from_tarball(
            input_tarball,
            extract_target,
            verify=False,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = (
            self.data / "docker" / "docker-images.tar.gz-expected-data-1.json"
        )
        self.assertResultsEqual(expected_location, results)

        # Extract the layers second
        errors = docker.extract_layers_from_images_to_base_path(
            base_path=extract_target,
            images=images,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = (
            self.data / "docker" / "docker-images.tar.gz-expected-data-2.json"
        )
        self.assertResultsEqual(expected_location, results)

    @staticmethod
    def make_tar_member(name, member_type=tarfile.REGTYPE, linkname=""):
        member = tarfile.TarInfo(name)
        member.type = member_type
        member.linkname = linkname
        return member

    def test_scanpipe_pipes_docker_tar_filter_with_safe_hardlinks(self):
        dest_path = str(Path(tempfile.mkdtemp()).resolve())
        safe_members = [
            self.make_tar_member("file.txt"),
            self.make_tar_member("hardlink", tarfile.LNKTYPE, "file.txt"),
            self.make_tar_member("etc_link", tarfile.SYMTYPE, "/etc"),
        ]
        for member in safe_members:
            filtered = docker.tar_filter_with_safe_hardlinks(member, dest_path)
            self.assertEqual(member.linkname, filtered.linkname)

        for linkname in ("../outside.txt", "/etc/passwd"):
            member = self.make_tar_member("hardlink", tarfile.LNKTYPE, linkname)
            with self.assertRaises(tarfile.FilterError):
                docker.tar_filter_with_safe_hardlinks(member, dest_path)

    def test_scanpipe_pipes_docker_extract_layers_refuses_outside_hardlinks(self):
        work_path = Path(tempfile.mkdtemp())
        outside_file = work_path / "outside.txt"
        outside_file.write_text("outside")

        layer_location = work_path / "layer.tar"
        with tarfile.open(layer_location, "w") as layer_tarball:
            file_member = self.make_tar_member("file.txt")
            file_member.size = len(b"inside")
            layer_tarball.addfile(file_member, io.BytesIO(b"inside"))
            layer_tarball.addfile(
                self.make_tar_member("hardlink", tarfile.LNKTYPE, "file.txt")
            )
            layer_tarball.addfile(
                self.make_tar_member(
                    "outside_hardlink", tarfile.LNKTYPE, str(outside_file)
                )
            )

        layer = SimpleNamespace(archive_location=str(layer_location), layer_id="layer1")
        image = SimpleNamespace(
            extracted_location=str(work_path / "image"), layers=[layer]
        )
        errors = docker.extract_layers_from_images_to_base_path(
            base_path=work_path / "codebase", images=[image]
        )

        layer_path = Path(layer.extracted_location)
        self.assertEqual("inside", (layer_path / "hardlink").read_text())
        self.assertFalse((layer_path / "outside_hardlink").exists())
        self.assertEqual(1, len(errors))
        self.assertIn("outside_hardlink", errors[0])

    def test_scanpipe_pipes_docker_extract_tar_safely_refuses_writes_through_symlinks(
        self,
    ):
        work_path = Path(tempfile.mkdtemp())
        outside_path = work_path / "outside"
        outside_path.mkdir()

        tarball_location = work_path / "layer.tar"
        with tarfile.open(tarball_location, "w") as tarball:
            tarball.addfile(
                self.make_tar_member("link", tarfile.SYMTYPE, str(outside_path))
            )
            file_member = self.make_tar_member("link/written.txt")
            file_member.size = len(b"content")
            tarball.addfile(file_member, io.BytesIO(b"content"))

        default_filter = vars(tarfile.TarFile)["extraction_filter"]
        errors = docker.extract_tar_safely(
            location=tarball_location, target_dir=work_path / "target"
        )

        self.assertFalse((outside_path / "written.txt").exists())
        self.assertEqual(1, len(errors))
        self.assertIn("link/written.txt", errors[0])
        self.assertIs(default_filter, vars(tarfile.TarFile)["extraction_filter"])

    def test_scanpipe_pipes_docker_get_layer_errors(self):
        extract_target = Path(tempfile.mkdtemp())
        layer_sha256 = "a" * 64
        valid_layer = SimpleNamespace(
            layer_id=layer_sha256,
            archive_location=str(extract_target / layer_sha256 / "layer.tar"),
        )
        image = SimpleNamespace(layers=[valid_layer])
        self.assertEqual([], docker.get_layer_errors(image, extract_target))

        invalid_layer_ids = [
            "../../escape",
            "/var/escape",
            "..",
            "",
            "A" * 64,
            "layer1",
        ]
        for layer_id in invalid_layer_ids:
            layer = SimpleNamespace(
                layer_id=layer_id, archive_location=valid_layer.archive_location
            )
            image = SimpleNamespace(layers=[layer])
            errors = docker.get_layer_errors(image, extract_target)
            self.assertEqual([f"Invalid layer ID: {layer_id}"], errors)

        outside_layer = SimpleNamespace(
            layer_id=layer_sha256,
            archive_location=str(extract_target / ".." / "outside.tar"),
        )
        image = SimpleNamespace(layers=[outside_layer])
        expected = [f"Layer {layer_sha256} archive is outside of the image."]
        self.assertEqual(expected, docker.get_layer_errors(image, extract_target))

    def test_scanpipe_pipes_docker_extract_layers_refuses_symlinked_target(self):
        work_path = Path(tempfile.mkdtemp())
        outside_path = work_path / "outside"
        outside_path.mkdir()
        base_path = work_path / "codebase"
        base_path.mkdir()
        (base_path / "image").symlink_to(outside_path)

        layer = SimpleNamespace(
            layer_id="a" * 64, archive_location=str(work_path / "layer.tar")
        )
        image = SimpleNamespace(extracted_location="image", layers=[layer])
        with self.assertRaises(ValueError) as cm:
            docker.extract_layers_from_images_to_base_path(base_path, [image])

        expected = f"Layer {layer.layer_id} target is outside of the codebase."
        self.assertEqual(expected, str(cm.exception))
        self.assertEqual([], list(outside_path.iterdir()))

    @mock.patch("scanpipe.pipes.docker.Image.get_images_from_dir")
    @mock.patch("scanpipe.pipes.docker.extract_tar_safely")
    def test_scanpipe_pipes_docker_extract_image_from_tarball_forged_layer_id(
        self, mock_extract_tar_safely, mock_get_images_from_dir
    ):
        extract_target = Path(tempfile.mkdtemp())
        archive_location = str(extract_target / "layer.tar")
        valid_layer = SimpleNamespace(
            layer_id="a" * 64, archive_location=archive_location
        )
        forged_layer = SimpleNamespace(
            layer_id="../../escape", archive_location=archive_location
        )
        valid_image = SimpleNamespace(layers=[valid_layer])
        forged_image = SimpleNamespace(layers=[forged_layer])
        mock_extract_tar_safely.return_value = []
        mock_get_images_from_dir.return_value = [valid_image, forged_image]

        images, errors = docker.extract_image_from_tarball("image.tar", extract_target)
        self.assertEqual([valid_image], images)
        self.assertEqual(["Invalid layer ID: ../../escape"], errors)

    def test_scanpipe_pipes_docker_default_extraction_filter(self):
        previous_filter = vars(tarfile.TarFile)["extraction_filter"]
        with docker.default_extraction_filter(docker.tar_filter_with_safe_hardlinks):
            self.assertIs(
                docker.tar_filter_with_safe_hardlinks,
                tarfile.TarFile.extraction_filter,
            )
            self.assertTrue(docker.extraction_filter_lock.locked())

        self.assertIs(previous_filter, vars(tarfile.TarFile)["extraction_filter"])
        self.assertFalse(docker.extraction_filter_lock.locked())

    @mock.patch("scanpipe.pipes.docker.extract_tar")
    def test_scanpipe_pipes_docker_extract_tar_safely_default_filter(
        self, mock_extract_tar
    ):
        default_filters = []

        def record_default_filter(**kwargs):
            default_filters.append(tarfile.TarFile.extraction_filter)
            return []

        mock_extract_tar.side_effect = record_default_filter
        with mock.patch("scanpipe.pipes.docker.py314", False):
            docker.extract_tar_safely(location="layer.tar", target_dir="target")
        with mock.patch("scanpipe.pipes.docker.py314", True):
            docker.extract_tar_safely(location="layer.tar", target_dir="target")

        expected = [docker.tar_filter_with_safe_hardlinks, None]
        self.assertEqual(expected, default_filters)

    def test_pipes_docker_flag_whiteout_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(project=p1, name=".wh.filename2")

        docker.flag_whiteout_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("ignored-whiteout", resource2.status)

    def test_pipes_docker_extract_image_from_tarball_with_broken_symlinks(
        self,
    ):
        extract_target = str(Path(tempfile.mkdtemp()) / "tempdir")
        input_tarball = str(self.data / "image-with-symlinks" / "minitag.tar")

        # Extract the image first
        images, errors = docker.extract_image_from_tarball(
            input_tarball,
            extract_target,
            verify=False,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = (
            self.data / "image-with-symlinks" / "minitag.tar-expected-data-1.json"
        )
        self.assertResultsEqual(expected_location, results)

        # Extract the layers second
        errors = docker.extract_layers_from_images_to_base_path(
            base_path=extract_target,
            images=images,
        )
        self.assertEqual([], errors)

        images_data = [docker.get_image_data(i) for i in images]
        results = json.dumps(images_data, indent=2)
        expected_location = (
            self.data / "image-with-symlinks" / "minitag.tar-expected-data-2.json"
        )
        self.assertResultsEqual(expected_location, results)

    def test_pipes_docker_get_tarballs_from_inputs(self):
        p1 = Project.objects.create(name="Analysis")
        _, tar = tempfile.mkstemp(suffix=".tar")
        _, tar_gz = tempfile.mkstemp(suffix=".tar.gz")
        _, tgz = tempfile.mkstemp(suffix=".tgz")
        _, zip = tempfile.mkstemp(suffix=".zip")
        _, rar = tempfile.mkstemp(suffix=".rar")
        copy_inputs([tar, tar_gz, tgz, zip, rar], p1.input_path)

        expected_extensions = ("tar", "tar.gz", "tgz")
        tarballs = docker.get_tarballs_from_inputs(project=p1)
        self.assertEqual(3, len(tarballs))
        for path in tarballs:
            self.assertTrue(path.name.endswith(expected_extensions))

    def test_pipes_docker_get_layers_data(self):
        p1 = Project.objects.create(name="Analysis")
        self.assertEqual([], docker.get_layers_data(p1))

        layers = [
            {
                "size": 5855232,
                "author": "Author",
                "comment": "Comment",
                "created": "2022-04-05T00:19:59.790636867Z",
                "layer_id": "4fc242d58285699eca05db3cc7c7122a2b8e014d9481",
                "created_by": "/bin/sh -c #(nop) ADD file:3efb3fd9ff852b5b56e4 in / ",
                "archive_location": "4fc242d58285699eca05db3cc7c712/layer.tar",
            },
            {
                "size": 2876928,
                "author": None,
                "comment": None,
                "created": "2022-04-05T07:50:46.219557029Z",
                "layer_id": "fbd7d5451c694bccb661c80cb52dd44824a8d0947b",
                "created_by": "/bin/sh -c set -eux;",
                "archive_location": "fbd7d5451c694bccb661c80/layer.tar",
            },
        ]
        p1.update_extra_data(
            {
                "images": [
                    {
                        "image_id": "06a4df09d5a34628e72a77999e5daee6cd3",
                        "layers": layers,
                    }
                ]
            }
        )

        layers_data = docker.get_layers_data(p1)
        self.assertEqual(2, len(layers_data))
        self.assertEqual("img-06a4df-layer-01-4fc242", layers_data[0].layer_tag)
        self.assertEqual(5855232, layers_data[0].size)
        self.assertEqual("Author", layers_data[0].author)
        self.assertEqual("Comment", layers_data[0].comment)
        self.assertEqual(layers[0]["archive_location"], layers_data[0].archive_location)

        self.assertEqual("img-06a4df-layer-02-fbd7d5", layers_data[1].layer_tag)
        self.assertEqual(layers[1]["archive_location"], layers_data[1].archive_location)

        from_old_rootfs = {
            "images": {"name": "packageurl-python-main.zip-extract", "distro": {}}
        }
        p1.update_extra_data(from_old_rootfs)
        self.assertEqual([], docker.get_layers_data(p1))

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

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import expectedFailure
from unittest import mock
from unittest import skipIf

from django.apps import apps
from django.test import TestCase
from django.test import override_settings

from commoncode.archive import extract_tar
from scancode.interrupt import TimeoutError as InterruptTimeoutError

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import output
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_input
from scanpipe.tests import license_policies_index

scanpipe_app = apps.get_app_config("scanpipe")
from_docker_image = os.environ.get("FROM_DOCKER_IMAGE")


class ScanPipeScancodePipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_scancode_extract_archive(self):
        target = tempfile.mkdtemp()
        input_location = str(self.data_location / "archive.zip")

        errors = scancode.extract_archive(input_location, target)
        self.assertEqual([], errors)

        results = [path.name for path in list(Path(target).glob("**/*"))]
        expected = [
            "a",
            "c",
            "b",
            "a.txt",
        ]
        self.assertEqual(7, len(results))
        for path in expected:
            self.assertIn(path, results)

    def test_scanpipe_pipes_scancode_extract_archives(self):
        tempdir = Path(tempfile.mkdtemp())
        input_location = str(self.data_location / "archive.zip")
        copy_input(input_location, tempdir)

        errors = scancode.extract_archives(tempdir)
        self.assertEqual([], errors)

        results = [path.name for path in list(tempdir.glob("**/*"))]
        self.assertEqual(9, len(results))
        expected = [
            "archive.zip-extract",
            "archive.zip",
            "a",
            "b",
            "c",
            "a.txt",
        ]
        for path in expected:
            self.assertIn(path, results)

    @skipIf(sys.platform != "linux", "QCOW2 extraction is not available on macOS.")
    def test_scanpipe_pipes_scancode_extract_archive_vmimage_qcow2(self):
        target = tempfile.mkdtemp()
        compressed_input_location = str(self.data_location / "foobar.qcow2.tar.gz")
        extract_tar(compressed_input_location, target_dir=target)
        input_location = Path(target) / "foobar.qcow2"

        errors = scancode.extract_archive(input_location, target)

        # The VM image extraction features are available in the Docker image context.
        if from_docker_image:
            self.assertEqual([], errors)
            results = [path.name for path in list(Path(target).glob("**/*"))]
            expected = [
                "bin",
                "busybox",
                "dot",
                "foobar.qcow2",
                "log",
                "lost+found",
                "tmp",
            ]
            self.assertEqual(sorted(expected), sorted(results))

        else:
            error = errors[0]
            self.assertTrue(
                any(
                    [
                        "Unable to read kernel" in error,
                        "VM Image extraction only supported on Linux." in error,
                    ]
                )
            )

    def test_scanpipe_pipes_scancode_get_resource_info(self):
        input_location = str(self.data_location / "notice.NOTICE")
        sha256 = "b323607418a36b5bd700fcf52ae9ca49f82ec6359bc4b89b1b2d73cf75321757"
        expected = {
            "type": CodebaseResource.Type.FILE,
            "name": "notice.NOTICE",
            "extension": ".NOTICE",
            "is_text": True,
            "size": 1178,
            "sha1": "4bd631df28995c332bf69d9d4f0f74d7ee089598",
            "md5": "90cd416fd24df31f608249b77bae80f1",
            "sha256": sha256,
            "mime_type": "text/plain",
            "file_type": "ASCII text",
        }
        resource_info = scancode.get_resource_info(input_location)
        self.assertEqual(expected, resource_info)

    def test_scanpipe_pipes_scancode_scan_file(self):
        input_location = str(self.data_location / "notice.NOTICE")
        scan_results, scan_errors = scancode.scan_file(input_location)
        expected = [
            "copyrights",
            "holders",
            "authors",
            "licenses",
            "license_expressions",
            "spdx_license_expressions",
            "percentage_of_license_text",
            "emails",
            "urls",
        ]
        self.assertEqual(sorted(expected), sorted(scan_results.keys()))
        self.assertEqual([], scan_errors)

    def test_scanpipe_pipes_scancode_scan_file_timeout(self):
        input_location = str(self.data_location / "notice.NOTICE")

        with mock.patch("scancode.api.get_copyrights") as get_copyrights:
            get_copyrights.side_effect = InterruptTimeoutError
            scan_results, scan_errors = scancode.scan_file(input_location)

        expected_errors = [
            "ERROR: for scanner: copyrights:\n"
            "ERROR: Processing interrupted: timeout after 120 seconds."
        ]
        self.assertEqual(expected_errors, scan_errors)

        expected = [
            "licenses",
            "license_expressions",
            "spdx_license_expressions",
            "percentage_of_license_text",
            "emails",
            "urls",
        ]
        self.assertEqual(sorted(expected), sorted(scan_results.keys()))

    def test_scanpipe_pipes_scancode_scan_file_and_save_results(self):
        project1 = Project.objects.create(name="Analysis")
        codebase_resource1 = CodebaseResource.objects.create(
            project=project1, path="not available"
        )

        self.assertEqual(0, project1.projecterrors.count())
        scan_results, scan_errors = scancode.scan_file(codebase_resource1.location)
        scancode.save_scan_file_results(codebase_resource1, scan_results, scan_errors)

        codebase_resource1.refresh_from_db()
        self.assertEqual("scanned-with-error", codebase_resource1.status)
        self.assertEqual(4, project1.projecterrors.count())

        copy_input(self.data_location / "notice.NOTICE", project1.codebase_path)
        codebase_resource2 = CodebaseResource.objects.create(
            project=project1, path="notice.NOTICE"
        )
        scan_results, scan_errors = scancode.scan_file(codebase_resource2.location)
        scancode.save_scan_file_results(codebase_resource2, scan_results, scan_errors)
        codebase_resource2.refresh_from_db()
        self.assertEqual("scanned", codebase_resource2.status)
        expected = [
            "apache-2.0",
            "apache-2.0",
            "warranty-disclaimer",
        ]
        self.assertEqual(expected, codebase_resource2.license_expressions)

    def test_scanpipe_pipes_scancode_scan_file_and_save_results_timeout_error(self):
        project1 = Project.objects.create(name="Analysis")
        copy_input(self.data_location / "notice.NOTICE", project1.codebase_path)
        codebase_resource = CodebaseResource.objects.create(
            project=project1, path="notice.NOTICE"
        )

        with mock.patch("scancode.api.get_copyrights") as get_copyrights:
            get_copyrights.side_effect = InterruptTimeoutError
            results, errors = scancode.scan_file(codebase_resource.location)
            scancode.save_scan_file_results(codebase_resource, results, errors)

        codebase_resource.refresh_from_db()
        self.assertEqual("scanned-with-error", codebase_resource.status)
        self.assertEqual(1, project1.projecterrors.count())
        error = project1.projecterrors.latest("created_date")
        self.assertEqual("CodebaseResource", error.model)
        self.assertEqual("", error.traceback)
        expected_message = (
            "ERROR: for scanner: copyrights:\n"
            "ERROR: Processing interrupted: timeout after 120 seconds."
        )
        self.assertEqual(expected_message, error.message)

    @mock.patch("scanpipe.pipes.scancode._scan_resource")
    def test_scanpipe_pipes_scancode_scan_for_files(self, mock_scan_resource):
        scan_results = {"license_expressions": ["mit"]}
        scan_errors = []
        mock_scan_resource.return_value = scan_results, scan_errors

        project1 = Project.objects.create(name="Analysis")
        sha1 = "51d28a27d919ce8690a40f4f335b9d591ceb16e9"
        resource1 = CodebaseResource.objects.create(
            project=project1,
            path="dir1/file.ext",
            sha1=sha1,
        )
        resource2 = CodebaseResource.objects.create(
            project=project1,
            path="dir2/file.ext",
            sha1=sha1,
        )

        scancode.scan_for_files(project1)

        resource1.refresh_from_db()
        self.assertEqual("scanned", resource1.status)
        self.assertEqual(["mit"], resource1.license_expressions)
        resource2.refresh_from_db()
        self.assertEqual("scanned", resource2.status)
        self.assertEqual(["mit"], resource2.license_expressions)

        resource3 = CodebaseResource.objects.create(
            project=project1,
            path="dir3/file.ext",
            sha1=sha1,
        )
        scan_results = {"copyrights": ["copy"]}
        scan_errors = ["ERROR"]
        mock_scan_resource.return_value = scan_results, scan_errors
        scancode.scan_for_files(project1)
        resource3.refresh_from_db()
        self.assertEqual("scanned-with-error", resource3.status)
        self.assertEqual([], resource3.license_expressions)
        self.assertEqual(["copy"], resource3.copyrights)

    def test_scanpipe_pipes_scancode_scan_for_package_data_timeout(self):
        input_location = str(self.data_location / "notice.NOTICE")

        with mock.patch("scancode.api.get_package_data") as get_package_data:
            get_package_data.side_effect = InterruptTimeoutError
            scan_results, scan_errors = scancode.scan_for_package_data(input_location)

        expected_errors = [
            "ERROR: for scanner: package_data:\n"
            "ERROR: Processing interrupted: timeout after 120 seconds."
        ]
        self.assertEqual(expected_errors, scan_errors)

    def test_scanpipe_pipes_scancode_scan_package_and_save_results_timeout_error(self):
        project1 = Project.objects.create(name="Analysis")
        copy_input(self.data_location / "notice.NOTICE", project1.codebase_path)
        codebase_resource = CodebaseResource.objects.create(
            project=project1, path="notice.NOTICE"
        )

        with mock.patch("scancode.api.get_package_data") as get_package_data:
            get_package_data.side_effect = InterruptTimeoutError
            results, errors = scancode.scan_for_package_data(codebase_resource.location)
            scancode.save_scan_package_results(codebase_resource, results, errors)

        codebase_resource.refresh_from_db()
        self.assertEqual("scanned-with-error", codebase_resource.status)
        self.assertEqual(1, project1.projecterrors.count())
        error = project1.projecterrors.latest("created_date")
        self.assertEqual("CodebaseResource", error.model)
        self.assertEqual("", error.traceback)
        expected_message = (
            "ERROR: for scanner: package_data:\n"
            "ERROR: Processing interrupted: timeout after 120 seconds."
        )
        self.assertEqual(expected_message, error.message)

    def test_scanpipe_pipes_scancode_scan_and_save_multiprocessing_with_threading(self):
        def noop(*args, **kwargs):
            pass

        project1 = Project.objects.create(name="Analysis")
        CodebaseResource.objects.create(project=project1, path="notice.NOTICE")
        resource_qs = project1.codebaseresources.all()

        scan_func = mock.Mock(return_value=(None, None))
        scan_func.__name__ = ""

        with override_settings(SCANCODEIO_PROCESSES=-1):
            scancode._scan_and_save(resource_qs, scan_func, noop)
        with_threading = scan_func.call_args[0][-1]
        self.assertFalse(with_threading)

        with override_settings(SCANCODEIO_PROCESSES=0):
            scancode._scan_and_save(resource_qs, scan_func, noop)
        with_threading = scan_func.call_args[0][-1]
        self.assertTrue(with_threading)

    @expectedFailure
    def test_scanpipe_pipes_scancode_virtual_codebase(self):
        project = Project.objects.create(name="asgiref")
        input_location = self.data_location / "asgiref-3.3.0_scanpipe_output.json"
        virtual_codebase = scancode.get_virtual_codebase(project, input_location)
        self.assertEqual(19, len(virtual_codebase.resources.keys()))

        scancode.create_discovered_packages(project, virtual_codebase)
        scancode.create_codebase_resources(project, virtual_codebase)
        scancode.create_discovered_dependencies(project, virtual_codebase)

        self.assertEqual(18, CodebaseResource.objects.count())
        self.assertEqual(1, DiscoveredPackage.objects.count())
        self.assertEqual(1, DiscoveredDependency.objects.count())
        # Make sure the root is not created as a CodebaseResource, walk(skip_root=True)
        self.assertFalse(CodebaseResource.objects.filter(path="codebase").exists())

        # Make sure the root is properly stripped, see `.get_path(strip_root=True)`
        self.assertFalse(
            CodebaseResource.objects.filter(path__startswith="codebase").exists()
        )

        # Make sure the detected package is properly assigned to its codebase resource
        package = DiscoveredPackage.objects.get()
        expected = "asgiref-3.3.0-py3-none-any.whl"
        self.assertEqual(expected, package.codebase_resources.get().path)

        # The functions can be called again and existing objects are skipped
        scancode.create_discovered_packages(project, virtual_codebase)
        scancode.create_codebase_resources(project, virtual_codebase)
        scancode.create_discovered_dependencies(project, virtual_codebase)
        self.assertEqual(18, CodebaseResource.objects.count())
        self.assertEqual(1, DiscoveredPackage.objects.count())
        self.assertEqual(1, DiscoveredDependency.objects.count())

    def test_scanpipe_pipes_scancode_create_codebase_resources_inject_policy(self):
        project = Project.objects.create(name="asgiref")
        # We are using `asgiref-3.3.0_toolkit_scan.json` instead of
        # `asgiref-3.3.0_scanpipe_output.json` because it is not exactly the same
        # format as a scancode-toolkit scan
        input_location = self.data_location / "asgiref-3.3.0_toolkit_scan.json"
        virtual_codebase = scancode.get_virtual_codebase(project, input_location)

        scanpipe_app.license_policies_index = license_policies_index
        scancode.create_discovered_packages(project, virtual_codebase)
        scancode.create_codebase_resources(project, virtual_codebase)
        scancode.create_discovered_dependencies(
            project, virtual_codebase, strip_datafile_path_root=True
        )
        resources = project.codebaseresources

        resource1 = resources.get(path__endswith="asgiref-3.3.0.dist-info/LICENSE")
        self.assertEqual("bsd-new", resource1.licenses[0]["key"])
        self.assertNotIn("bsd-new", license_policies_index)
        self.assertIsNone(resource1.licenses[0]["policy"])

        resource2 = resources.get(path__endswith="asgiref/timeout.py")
        self.assertEqual("apache-2.0", resource2.licenses[0]["key"])
        expected = {
            "label": "Approved License",
            "color_code": "#008000",
            "license_key": "apache-2.0",
            "compliance_alert": "",
        }
        self.assertEqual(expected, resource2.licenses[0]["policy"])

    def test_scanpipe_pipes_scancode_run_scancode(self):
        project = Project.objects.create(name="name with space")
        exitcode, output = scancode.run_scancode(
            location=str(project.codebase_path),
            output_file=str(project.get_output_file_path("scancode", "json")),
            options=["--info"],
        )
        self.assertEqual(0, exitcode)
        self.assertEqual("", output)

    @mock.patch("scanpipe.pipes.run_command")
    def test_scanpipe_pipes_scancode_run_scancode_cli_options(self, mock_run_command):
        mock_run_command.return_value = 0, ""

        with override_settings(SCANCODE_TOOLKIT_CLI_OPTIONS=["--timeout 60"]):
            scancode.run_scancode(location=None, output_file=None, options=[])
            self.assertIn("--timeout 60", mock_run_command.call_args[0][0])

        with override_settings(SCANCODEIO_PROCESSES=10):
            scancode.run_scancode(location=None, output_file=None, options=[])
            self.assertIn("--processes 10", mock_run_command.call_args[0][0])

    def test_scanpipe_pipes_scancode_make_results_summary(self):
        project = Project.objects.create(name="Analysis")
        scan_results_location = self.data_location / "is-npm-1.0.0_scan_package.json"
        summary = scancode.make_results_summary(project, scan_results_location)
        self.assertEqual(10, len(summary.keys()))

        scan_results_location = (
            self.data_location / "multiple-is-npm-1.0.0_scan_package.json"
        )
        summary = scancode.make_results_summary(project, scan_results_location)
        self.assertEqual(10, len(summary.keys()))

    def test_scanpipe_pipes_scancode_load_inventory_from_toolkit_scan(self):
        project = Project.objects.create(name="Analysis")
        input_location = self.data_location / "asgiref-3.3.0_toolkit_scan.json"
        scancode.load_inventory_from_toolkit_scan(project, input_location)
        self.assertEqual(18, project.codebaseresources.count())
        self.assertEqual(2, project.discoveredpackages.count())
        self.assertEqual(4, project.discovereddependencies.count())

    def test_scanpipe_pipes_scancode_load_inventory_from_scanpipe(self):
        project = Project.objects.create(name="1")
        input_location = self.data_location / "asgiref-3.3.0_scanpipe_output.json"
        scan_data = json.loads(input_location.read_text())
        scancode.load_inventory_from_scanpipe(project, scan_data)
        self.assertEqual(18, project.codebaseresources.count())
        self.assertEqual(2, project.discoveredpackages.count())
        self.assertEqual(4, project.discovereddependencies.count())

        # Using the JSON output of project1 to load into project2
        project2 = Project.objects.create(name="2")
        output_file = output.to_json(project=project)
        scan_data = json.loads(output_file.read_text())
        scancode.load_inventory_from_scanpipe(project2, scan_data)
        self.assertEqual(18, project2.codebaseresources.count())
        self.assertEqual(2, project2.discoveredpackages.count())
        self.assertEqual(4, project2.discovereddependencies.count())

    def test_scanpipe_pipes_scancode_assemble_packages(self):
        project = Project.objects.create(name="Analysis")
        project_scan_location = self.data_location / "package_assembly_codebase.json"
        scancode.load_inventory_from_toolkit_scan(project, project_scan_location)

        self.assertEqual(0, project.discoveredpackages.count())
        scancode.assemble_packages(project)
        self.assertEqual(1, project.discoveredpackages.count())

        package = project.discoveredpackages.all()[0]
        self.assertEqual("pkg:npm/test@0.1.0", package.package_url)

        associated_resources = [r.path for r in package.codebase_resources.all()]
        expected_resources = [
            "get_package_resources/package.json",
            "get_package_resources/this-should-be-returned",
        ]
        self.assertEqual(sorted(expected_resources), sorted(associated_resources))

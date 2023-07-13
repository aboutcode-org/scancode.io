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
from scanpipe.pipes import input
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_input
from scanpipe.tests import FIXTURES_REGEN

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
            "authors",
            "copyrights",
            "detected_license_expression",
            "detected_license_expression_spdx",
            "emails",
            "holders",
            "license_clues",
            "license_detections",
            "percentage_of_license_text",
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
            "detected_license_expression",
            "detected_license_expression_spdx",
            "emails",
            "license_clues",
            "license_detections",
            "percentage_of_license_text",
            "urls",
        ]
        self.assertEqual(sorted(expected), sorted(scan_results.keys()))

    def test_scanpipe_pipes_scancode_scan_file_min_license_score(self):
        input_location = str(self.data_location / "notice.NOTICE")

        scan_results, _ = scancode.scan_file(input_location)
        license_detections = scan_results.get("license_detections")
        self.assertEqual(1, len(license_detections))
        self.assertEqual(3, len(license_detections[0].get("matches")))

        scan_results, _ = scancode.scan_file(input_location, min_license_score=99)
        license_detections = scan_results.get("license_detections")
        self.assertEqual(1, len(license_detections))
        self.assertEqual(1, len(license_detections[0].get("matches")))

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
        expected = "apache-2.0 AND warranty-disclaimer"
        self.assertEqual(expected, codebase_resource2.detected_license_expression)

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
        scan_results = {"detected_license_expression": "mit"}
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
        self.assertEqual("mit", resource1.detected_license_expression)
        resource2.refresh_from_db()
        self.assertEqual("scanned", resource2.status)
        self.assertEqual("mit", resource2.detected_license_expression)

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
        self.assertEqual("", resource3.detected_license_expression)
        self.assertEqual(["copy"], resource3.copyrights)

    @mock.patch("scanpipe.pipes.scancode._scan_and_save")
    def test_scanpipe_pipes_scancode_scan_for_files_scancode_license_score(
        self, mock_scan_and_save
    ):
        project1 = Project.objects.create(
            name="Analysis",
            settings={"scancode_license_score": 99},
        )

        scancode.scan_for_files(project1)
        expected = {"min_license_score": 99}
        self.assertEqual(expected, mock_scan_and_save.call_args_list[-1].args[-1])

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

    def test_scanpipe_pipes_scancode_make_results_summary(self, regen=FIXTURES_REGEN):
        # Ensure the policies index is empty to avoid any side effect on results
        scanpipe_app.license_policies_index = None
        # Run the scan_package pipeline to have a proper DB and local files setup
        pipeline_name = "scan_package"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data_location / "is-npm-1.0.0.tgz"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()
        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        # Forcing package_uid for proper assertion with expected results
        package = project1.discoveredpackages.get()
        uuid = "ba110d49-b6f2-4c86-8d89-a6fd34838ca8"
        package.update(package_uid=f"pkg:npm/is-npm@1.0.0?uuid={uuid}")

        # Patching the ``file_type`` values as those OS dependant.
        # Note that we cannot use proper ``mock`` as the ``scan_package`` pipeline
        # uses a subprocess call to run the ``scancode`` command.
        project1.codebaseresources.all().update(file_type="")

        scan_output_location = self.data_location / "is-npm-1.0.0_scan_package.json"
        summary = scancode.make_results_summary(project1, scan_output_location)
        expected_location = self.data_location / "scancode/is-npm-1.0.0_summary.json"
        if regen:
            expected_location.write_text(json.dumps(summary, indent=2))

        self.assertJSONEqual(expected_location.read_text(), summary)

    def test_scanpipe_pipes_scancode_assemble_packages(self):
        project = Project.objects.create(name="Analysis")
        filename = "package_assembly_codebase.json"
        project_scan_location = self.data_location / "scancode" / filename
        input.load_inventory_from_toolkit_scan(project, project_scan_location)

        project.discoveredpackages.all().delete()
        self.assertEqual(0, project.discoveredpackages.count())

        scancode.assemble_packages(project)
        self.assertEqual(1, project.discoveredpackages.count())

        package = project.discoveredpackages.all()[0]
        self.assertEqual("pkg:npm/test@0.1.0", package.package_url)

        associated_resources = [r.path for r in package.codebase_resources.all()]
        expected_resources = [
            "test/get_package_resources/package.json",
            "test/get_package_resources/this-should-be-returned",
        ]
        self.assertEqual(sorted(expected_resources), sorted(associated_resources))

    def test_scanpipe_pipes_scancode_get_detection_data(self):
        detection_entry = {
            "matches": [
                {
                    "score": 99.0,
                    "matcher": "2-aho",
                    "end_line": 76,
                    "start_line": 76,
                    "matched_text": "licensed under CC-BY-NC,",
                    "match_coverage": 100.0,
                    "matched_length": 5,
                    "rule_relevance": 99,
                    "rule_identifier": "cc-by-nc-4.0_16.RULE",
                    "license_expression": "cc-by-nc-4.0",
                },
                {
                    "score": 99.0,
                    "matcher": "2-aho",
                    "end_line": 76,
                    "start_line": 76,
                    "matched_text": "licensed under CC-BY-",
                    "match_coverage": 100.0,
                    "matched_length": 4,
                    "rule_relevance": 99,
                    "rule_identifier": "cc-by-4.0_84.RULE",
                    "license_expression": "cc-by-4.0",
                },
            ],
            "identifier": "cc_by_nc_4_0_and_cc_by_4_0-3e419bd6-97a4-a144-35ab",
            "license_expression": "cc-by-nc-4.0 AND cc-by-4.0",
        }

        expected = {
            "license_expression": "cc-by-nc-4.0 AND cc-by-4.0",
            "identifier": "cc_by_nc_4_0_and_cc_by_4_0-3e419bd6-97a4-a144-35ab",
            "matches": [
                {
                    "license_expression": "cc-by-nc-4.0",
                    "matched_text": "licensed under CC-BY-NC,",
                },
                {
                    "license_expression": "cc-by-4.0",
                    "matched_text": "licensed under CC-BY-",
                },
            ],
        }

        results = scancode.get_detection_data(detection_entry)
        self.assertEqual(expected, results)

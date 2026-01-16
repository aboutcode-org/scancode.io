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
import multiprocessing
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
from scanpipe.pipes import collect_and_create_codebase_resources
from scanpipe.pipes import flag
from scanpipe.pipes import input
from scanpipe.pipes import scancode
from scanpipe.pipes.input import copy_input
from scanpipe.tests import FIXTURES_REGEN

scanpipe_app = apps.get_app_config("scanpipe")
from_docker_image = os.environ.get("FROM_DOCKER_IMAGE")


class ScanPipeScancodePipesTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_scancode_extract_archive(self):
        target = tempfile.mkdtemp()
        input_location = str(self.data / "scancode" / "archive.zip")

        errors = scancode.extract_archive(input_location, target)
        self.assertEqual({}, errors)

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

    def test_scanpipe_pipes_scancode_extract_archive_errors(self):
        target = tempfile.mkdtemp()
        input_location = str(self.data / "scancode" / "corrupted.tar.gz")
        errors = scancode.extract_archive(input_location, target)

        error_message = "gzip decompression failed"
        self.assertIn(error_message, errors[str(input_location)][0])

    def test_scanpipe_pipes_scancode_extract_archives(self):
        tempdir = Path(tempfile.mkdtemp())
        input_location = str(self.data / "scancode" / "archive.zip")
        copy_input(input_location, tempdir)

        errors = scancode.extract_archives(tempdir)
        self.assertEqual({}, errors)

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

    def test_scanpipe_pipes_scancode_extract_archives_errors(self):
        tempdir = Path(tempfile.mkdtemp())
        input_location = str(self.data / "scancode" / "corrupted.tar.gz")
        target = copy_input(input_location, tempdir)
        errors = scancode.extract_archives(tempdir)

        error_message = "gzip decompression failed"
        self.assertIn(error_message, errors[str(target)][0])

    @skipIf(sys.platform != "linux", "QCOW2 extraction is not available on macOS.")
    def test_scanpipe_pipes_scancode_extract_archive_vmimage_qcow2(self):
        target = tempfile.mkdtemp()
        compressed_input_location = str(self.data / "scancode" / "foobar.qcow2.tar.gz")
        extract_tar(compressed_input_location, target_dir=target)
        input_location = Path(target) / "foobar.qcow2"

        errors = scancode.extract_archive(input_location, target)

        # The VM image extraction features are available in the Docker image context.
        if from_docker_image:
            self.assertEqual({}, errors)
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
            expected = "libguestfs requires the kernel executable to be readable"
            self.assertIn(expected, errors[str(input_location)][0])

    def test_scanpipe_pipes_scancode_get_resource_info(self):
        input_location = str(self.data / "aboutcode" / "notice.NOTICE")
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
            "sha1_git": "1f72cf031889492f93c055fd29c4a3083025c6cf",
            "mime_type": "text/plain",
            "file_type": "ASCII text",
        }
        resource_info = scancode.get_resource_info(input_location)
        self.assertEqual(expected, resource_info)

    def test_scanpipe_pipes_scancode_scan_file(self):
        input_location = str(self.data / "aboutcode" / "notice.NOTICE")
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
        input_location = str(self.data / "aboutcode" / "notice.NOTICE")

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
        input_location = str(self.data / "aboutcode" / "notice.NOTICE")

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

        self.assertEqual(0, project1.projectmessages.count())
        scan_results, scan_errors = scancode.scan_file(codebase_resource1.location)
        scancode.save_scan_file_results(codebase_resource1, scan_results, scan_errors)

        codebase_resource1.refresh_from_db()
        self.assertEqual("scanned-with-error", codebase_resource1.status)
        self.assertEqual(4, project1.projectmessages.count())

        copy_input(self.data / "aboutcode" / "notice.NOTICE", project1.codebase_path)
        codebase_resource2 = CodebaseResource.objects.create(
            project=project1, path="notice.NOTICE"
        )
        scan_results, scan_errors = scancode.scan_file(codebase_resource2.location)
        scancode.save_scan_file_results(codebase_resource2, scan_results, scan_errors)
        codebase_resource2.refresh_from_db()
        self.assertEqual("scanned", codebase_resource2.status)
        expected = (
            "apache-2.0 AND (apache-2.0 AND scancode-acknowledgment)"
            " AND warranty-disclaimer"
        )
        self.assertEqual(expected, codebase_resource2.detected_license_expression)

    def test_scanpipe_pipes_scancode_scan_file_and_save_results_timeout_error(self):
        project1 = Project.objects.create(name="Analysis")
        copy_input(self.data / "aboutcode" / "notice.NOTICE", project1.codebase_path)
        codebase_resource = CodebaseResource.objects.create(
            project=project1, path="notice.NOTICE"
        )

        with mock.patch("scancode.api.get_copyrights") as get_copyrights:
            get_copyrights.side_effect = InterruptTimeoutError
            results, errors = scancode.scan_file(codebase_resource.location)
            scancode.save_scan_file_results(codebase_resource, results, errors)

        codebase_resource.refresh_from_db()
        self.assertEqual("scanned-with-error", codebase_resource.status)
        self.assertEqual(1, project1.projectmessages.count())
        message = project1.projectmessages.latest("created_date")
        self.assertEqual("CodebaseResource", message.model)
        self.assertEqual("", message.traceback)
        expected_description = (
            "ERROR: for scanner: copyrights:\n"
            "ERROR: Processing interrupted: timeout after 120 seconds."
        )
        self.assertEqual(expected_description, message.description)

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

    def test_scanpipe_pipes_scancode_scan_for_package_data_timeout(self):
        input_location = str(self.data / "aboutcode" / "notice.NOTICE")

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
        copy_input(self.data / "aboutcode" / "notice.NOTICE", project1.codebase_path)
        codebase_resource = CodebaseResource.objects.create(
            project=project1, path="notice.NOTICE"
        )

        with mock.patch("scancode.api.get_package_data") as get_package_data:
            get_package_data.side_effect = InterruptTimeoutError
            results, errors = scancode.scan_for_package_data(codebase_resource.location)
            scancode.save_scan_package_results(codebase_resource, results, errors)

        codebase_resource.refresh_from_db()
        self.assertEqual("scanned-with-error", codebase_resource.status)
        self.assertEqual(1, project1.projectmessages.count())
        message = project1.projectmessages.latest("created_date")
        self.assertEqual("CodebaseResource", message.model)
        self.assertEqual("", message.traceback)
        expected_description = (
            "ERROR: for scanner: package_data:\n"
            "ERROR: Processing interrupted: timeout after 120 seconds."
        )
        self.assertEqual(expected_description, message.description)

    def test_scanpipe_pipes_scancode_scan_resources_multiprocessing_threading(self):
        def noop(*args, **kwargs):
            pass

        project1 = Project.objects.create(name="Analysis")
        CodebaseResource.objects.create(project=project1, path="notice.NOTICE")
        resource_qs = project1.codebaseresources.all()

        scan_func = mock.Mock(return_value=(None, None))
        scan_func.__name__ = ""

        with override_settings(SCANCODEIO_PROCESSES=-1):
            scancode.scan_resources(resource_qs, scan_func, noop)
        with_threading = scan_func.call_args[0][-1]
        self.assertFalse(with_threading)

        with override_settings(SCANCODEIO_PROCESSES=0):
            scancode.scan_resources(resource_qs, scan_func, noop)
        with_threading = scan_func.call_args[0][-1]
        self.assertTrue(with_threading)

    @expectedFailure
    def test_scanpipe_pipes_scancode_virtual_codebase(self):
        project = Project.objects.create(name="asgiref")
        input_location = self.data / "asgiref" / "asgiref-3.3.0_scanpipe_output.json"
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

    def test_scanpipe_pipes_scancode_get_packages_with_purl_from_resources(self):
        project = Project.objects.create(name="Analysis")
        filename = "package_assembly_codebase.json"
        project_scan_location = self.data / "scancode" / filename
        input.load_inventory_from_toolkit_scan(project, project_scan_location)

        project.discoveredpackages.all().delete()
        self.assertEqual(0, project.discoveredpackages.count())

        packages = list(scancode.get_packages_with_purl_from_resources(project))

        package_purl_exists = [True for package in packages if package.purl]
        package_purls = [package.purl for package in packages]
        self.assertTrue(package_purl_exists)
        self.assertEqual(len(package_purl_exists), 1)
        self.assertTrue("pkg:npm/test@0.1.0" in package_purls)

    def test_scanpipe_pipes_scancode_run_scan(self):
        project = Project.objects.create(name="name with space")
        scanning_errors = scancode.run_scan(
            location=str(project.codebase_path),
            output_file=str(project.get_output_file_path("scancode", "json")),
            run_scan_args={"info": True},
        )
        self.assertEqual({}, scanning_errors)

    @mock.patch("scanpipe.pipes.scancode.scancode_run_scan")
    def test_scanpipe_pipes_scancode_run_scan_args(self, mock_run_scan):
        mock_run_scan.return_value = True, {}
        output_file = tempfile.mkstemp()[1]

        with override_settings(SCANCODEIO_SCAN_FILE_TIMEOUT=10):
            scancode.run_scan(location=None, output_file=output_file, run_scan_args={})
            run_scan_kwargs = mock_run_scan.call_args.kwargs
            self.assertEqual(10, run_scan_kwargs.get("timeout"))

        expected_processes = -1 if multiprocessing.get_start_method() != "fork" else 2
        with override_settings(SCANCODEIO_PROCESSES=2):
            scancode.run_scan(location=None, output_file=output_file, run_scan_args={})
            run_scan_kwargs = mock_run_scan.call_args.kwargs
            self.assertEqual(expected_processes, run_scan_kwargs.get("processes"))

    def test_scanpipe_max_file_size_works(self):
        with override_settings(SCANCODEIO_SCAN_MAX_FILE_SIZE=10000):
            project1 = Project.objects.create(name="Analysis")
            input_location = self.data / "d2d-rust" / "to-trustier-binary-linux.tar.gz"
            project1.copy_input_from(input_location)

            run = project1.add_pipeline("scan_codebase")
            pipeline = run.make_pipeline_instance()

            exitcode, out = pipeline.execute()
            self.assertEqual(0, exitcode, msg=out)
            resource1 = project1.codebaseresources.get(
                path="to-trustier-binary-linux.tar.gz-extract/trustier"
            )
            self.assertEqual(resource1.status, flag.IGNORED_BY_MAX_FILE_SIZE)

    def test_scanpipe_pipes_scancode_make_results_summary(self, regen=FIXTURES_REGEN):
        # Ensure the policies are empty to avoid any side effect on results
        scanpipe_app.policies = None
        # Run the scan_single_package pipeline to have a proper DB and local files setup
        pipeline_name = "scan_single_package"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data / "scancode" / "is-npm-1.0.0.tgz"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()
        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        # Forcing package_uid for proper assertion with expected results
        package = project1.discoveredpackages.get()
        uuid = "ba110d49-b6f2-4c86-8d89-a6fd34838ca8"
        package.update(package_uid=f"pkg:npm/is-npm@1.0.0?uuid={uuid}")

        # Patching the ``file_type`` and ``mime_typea` values as those are OS dependant.
        # Note that we cannot use proper ``mock`` as the ``scan_package`` pipeline
        # uses a subprocess call to run the ``scancode`` command.
        project1.codebaseresources.all().update(file_type="", mime_type="text/plain")

        scan_output_location = self.data / "scancode" / "is-npm-1.0.0_scan_package.json"
        summary = scancode.make_results_summary(project1, scan_output_location)
        expected_location = self.data / "scancode" / "is-npm-1.0.0_summary.json"
        if regen:
            expected_location.write_text(json.dumps(summary, indent=2))

        self.assertJSONEqual(expected_location.read_text(), summary)

    def test_scanpipe_pipes_scancode_assemble_package_function(self):
        project = Project.objects.create(name="Analysis")
        filename = "package_assembly_codebase.json"
        project_scan_location = self.data / "scancode" / filename
        input.load_inventory_from_toolkit_scan(project, project_scan_location)
        project.discoveredpackages.all().delete()

        processed_paths = set()
        resource = project.codebaseresources.get(name="package.json")

        # This assembly should not trigger that many queries.
        with self.assertNumQueries(16):
            scancode.assemble_package(resource, project, processed_paths)

        self.assertEqual(1, project.discoveredpackages.count())
        package = project.discoveredpackages.get()
        self.assertEqual("pkg:npm/test@0.1.0", package.package_url)
        associated_resources = [r.path for r in package.codebase_resources.all()]
        expected_resources = [
            "test/get_package_resources/package.json",
            "test/get_package_resources/this-should-be-returned",
        ]
        self.assertEqual(sorted(expected_resources), sorted(associated_resources))

    def test_scanpipe_pipes_scancode_assemble_packages(self):
        project = Project.objects.create(name="Analysis")
        filename = "package_assembly_codebase.json"
        project_scan_location = self.data / "scancode" / filename
        input.load_inventory_from_toolkit_scan(project, project_scan_location)

        project.discoveredpackages.all().delete()
        self.assertEqual(0, project.discoveredpackages.count())

        scancode.assemble_packages(project, progress_logger=lambda: None)
        self.assertEqual(1, project.discoveredpackages.count())

        package = project.discoveredpackages.get()
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

    def test_scanpipe_scancode_process_package_data(self):
        project1 = Project.objects.create(name="Utility: PurlDB")
        package_json_location = self.data / "manifests" / "package.json"
        copy_input(package_json_location, project1.codebase_path)
        collect_and_create_codebase_resources(project1)
        scancode.scan_for_application_packages(project1, assemble=False)
        scancode.process_package_data(project1)

        self.assertEqual(1, project1.discoveredpackages.count())
        self.assertEqual(6, project1.discovereddependencies.count())

    def test_scanpipe_scancode_create_packages_and_dependencies_from_mapping(self):
        pipeline_name = "inspect_packages"
        project1 = Project.objects.create(name="Analysis")

        input_location = self.data / "dependencies" / "resolved_dependencies_npm.zip"
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(
            pipeline_name=pipeline_name,
            selected_groups=[],
        )
        pipeline = run.make_pipeline_instance()
        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(1, project1.discoveredpackages.count())
        self.assertEqual(7, project1.discovereddependencies.count())

        yarn_resource = project1.codebaseresources.get(
            path="resolved_dependencies_npm.zip-extract/yarn.lock"
        )
        lockfile_package_data = yarn_resource.package_data[0]
        scancode.create_packages_and_dependencies_from_mapping(
            project=project1,
            resource=yarn_resource,
            package_mapping=lockfile_package_data,
            find_package=False,
            process_resolved=True,
        )

        self.assertEqual(7, project1.discoveredpackages.count())
        self.assertEqual(12, project1.discovereddependencies.count())

    def test_scanpipe_scancode_resolve_dependencies(self):
        project1 = Project.objects.create(name="Analysis")
        pkg_1 = DiscoveredPackage.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            version="3.7.2",
        )
        DiscoveredDependency.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            extracted_requirement="^3.5.1",
            is_direct=False,
            resolved_to_package=pkg_1,
        )
        dep_2 = DiscoveredDependency.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            extracted_requirement="^3.5.1",
            is_direct=True,
        )
        scancode.match_and_resolve_dependencies(project1)

        self.assertEqual(1, project1.discoveredpackages.count())
        self.assertEqual(1, project1.discovereddependencies.count())
        resolved_dep = project1.discovereddependencies.get(name="bluebird")
        self.assertEqual(resolved_dep, dep_2)
        self.assertEqual(resolved_dep.resolved_to_package, pkg_1)

    def test_scanpipe_scancode_resolve_dependencies_complex_requirements(self):
        project1 = Project.objects.create(name="Analysis")
        pkg_1 = DiscoveredPackage.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            version="3.7.2",
        )
        DiscoveredDependency.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            extracted_requirement="^3.5.1",
            is_direct=False,
            resolved_to_package=pkg_1,
        )
        dep_2 = DiscoveredDependency.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            extracted_requirement="^3.5.1 || ^3.5.0",
            is_direct=True,
        )
        scancode.match_and_resolve_dependencies(project1)

        self.assertEqual(1, project1.discoveredpackages.count())
        self.assertEqual(1, project1.discovereddependencies.count())
        resolved_dep = project1.discovereddependencies.get(name="bluebird")
        self.assertEqual(resolved_dep, dep_2)
        self.assertEqual(resolved_dep.resolved_to_package, pkg_1)

    def test_scanpipe_scancode_resolve_dependencies_no_requirements(self):
        project1 = Project.objects.create(name="Analysis")
        pkg_1 = DiscoveredPackage.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            version="3.7.2",
        )
        DiscoveredDependency.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            extracted_requirement="^3.5.1",
            is_direct=False,
            resolved_to_package=pkg_1,
        )
        dep_2 = DiscoveredDependency.objects.create(
            project=project1,
            type="npm",
            name="bluebird",
            extracted_requirement="",
            is_direct=True,
        )
        scancode.match_and_resolve_dependencies(project1)

        self.assertEqual(1, project1.discoveredpackages.count())
        self.assertEqual(1, project1.discovereddependencies.count())
        resolved_dep = project1.discovereddependencies.get(name="bluebird")
        self.assertEqual(resolved_dep, dep_2)
        self.assertEqual(resolved_dep.resolved_to_package, pkg_1)

    def test_scanpipe_pipes_scancode_scan_single_package_correct_parent_path(self):
        project1 = Project.objects.create(name="Analysis")
        input_location = self.data / "scancode" / "is-npm-1.0.0.tgz"
        project1.copy_input_from(input_location)
        run = project1.add_pipeline("scan_single_package")
        pipeline = run.make_pipeline_instance()
        exitcode, out = pipeline.execute()

        self.assertEqual(0, exitcode, msg=out)
        self.assertEqual(4, project1.codebaseresources.count())

        root = project1.codebaseresources.get(path="package")
        self.assertEqual("", root.parent_path)
        self.assertNotEqual("codebase", root.parent_path)

        file1 = project1.codebaseresources.get(path="package/index.js")
        self.assertEqual("package", file1.parent_path)

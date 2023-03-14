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

import datetime
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import expectedFailure
from unittest import mock
from unittest import skipIf

from django.apps import apps
from django.core.management import call_command
from django.test import TestCase
from django.test import TransactionTestCase
from django.test import override_settings

from commoncode.archive import extract_tar
from scancode.interrupt import TimeoutError as InterruptTimeoutError

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import codebase
from scanpipe.pipes import fetch
from scanpipe.pipes import filename_now
from scanpipe.pipes import input
from scanpipe.pipes import make_codebase_resource
from scanpipe.pipes import output
from scanpipe.pipes import resolve
from scanpipe.pipes import rootfs
from scanpipe.pipes import scancode
from scanpipe.pipes import strip_root
from scanpipe.pipes import tag_not_analyzed_codebase_resources
from scanpipe.pipes import update_or_create_dependency
from scanpipe.pipes import update_or_create_package
from scanpipe.pipes import update_or_create_resource
from scanpipe.pipes import windows
from scanpipe.pipes.input import copy_input
from scanpipe.tests import dependency_data1
from scanpipe.tests import license_policies_index
from scanpipe.tests import mocked_now
from scanpipe.tests import package_data1
from scanpipe.tests import resource_data1

scanpipe_app = apps.get_app_config("scanpipe")
from_docker_image = os.environ.get("FROM_DOCKER_IMAGE")


class ScanPipePipesTest(TestCase):
    data_location = Path(__file__).parent / "data"

    def test_scanpipe_pipes_strip_root(self):
        input_paths = [
            "/root/dir/file",
            "/root/dir/file/",
            "//root/dir/file",
            "//root/dir/file/",
            "root/dir/file",
            "root/dir/file/",
        ]
        expected = "dir/file"

        for path in input_paths:
            self.assertEqual(expected, strip_root(path))
            self.assertEqual(expected, strip_root(Path(path)))

    def test_scanpipe_pipes_tag_not_analyzed_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="filename1.ext",
            status="scanned",
        )

        tag_not_analyzed_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("not-analyzed", resource1.status)
        self.assertEqual("scanned", resource2.status)

    @mock.patch("scanpipe.pipes.datetime", mocked_now)
    def test_scanpipe_pipes_filename_now(self):
        self.assertEqual("2010-10-10-10-10-10", filename_now())

    def test_scanpipe_pipes_input_get_tool_name_from_scan_headers(self):
        tool_name = input.get_tool_name_from_scan_headers(scan_data={})
        self.assertIsNone(tool_name)

        tool_name = input.get_tool_name_from_scan_headers(scan_data={"headers": []})
        self.assertIsNone(tool_name)

        input_location = self.data_location / "asgiref-3.3.0_scanpipe_output.json"
        tool_name = input.get_tool_name_from_scan_headers(
            scan_data=json.loads(input_location.read_text())
        )
        self.assertEqual("scanpipe", tool_name)

        input_location = self.data_location / "asgiref-3.3.0_toolkit_scan.json"
        tool_name = input.get_tool_name_from_scan_headers(
            scan_data=json.loads(input_location.read_text())
        )
        self.assertEqual("scancode-toolkit", tool_name)

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
        self.assertEquals(sorted(expected_resources), sorted(associated_resources))

    def test_scanpipe_pipes_codebase_get_codebase_tree(self):
        def _replace_path(virtual_tree_children):
            """
            Given a list `virtual_tree_children` of mappings, remove instances
            of "virtual_root/" from the paths of mappings and their children,
            recursively.
            """
            for res in virtual_tree_children:
                path = res["path"]
                path = path.replace("virtual_root/", "")
                res["path"] = path
                _replace_path(res.get("children", []))

        fixtures = self.data_location / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        scan_results = self.data_location / "asgiref-3.3.0_scanpipe_output.json"
        virtual_codebase = scancode.get_virtual_codebase(project, scan_results)
        project_codebase = codebase.ProjectCodebase(project)

        fields = ["name", "path"]

        virtual_tree = codebase.get_codebase_tree(virtual_codebase, fields)
        project_tree = codebase.get_codebase_tree(project_codebase, fields)

        with open(self.data_location / "asgiref-3.3.0_tree.json") as f:
            expected = json.loads(f.read())

        self.assertEqual(expected, project_tree)

        virtual_tree_children = virtual_tree["children"][0]["children"]
        _replace_path(virtual_tree_children)

        self.assertEqual(expected["children"], virtual_tree_children)

    def test_scanpipe_pipes_codebase_project_codebase_class_no_resources(self):
        project = Project.objects.create(name="project")
        project_codebase = codebase.ProjectCodebase(project)

        self.assertEqual([], list(project_codebase.root_resources))
        self.assertEqual([], list(project_codebase.resources))
        self.assertEqual([], list(project_codebase.walk()))
        self.assertEqual(dict(children=[]), project_codebase.get_tree())

    def test_scanpipe_pipes_codebase_project_codebase_class_with_resources(self):
        fixtures = self.data_location / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})

        project = Project.objects.get(name="asgiref")
        project_codebase = codebase.ProjectCodebase(project)

        expected_root_resources = project.codebaseresources.exclude(path__contains="/")
        expected_root_resources = list(expected_root_resources)
        self.assertEqual(expected_root_resources, list(project_codebase.root_resources))

        self.assertEqual(18, len(project_codebase.resources))

        walk_gen = project_codebase.walk()
        self.assertEqual(next(iter(expected_root_resources)), next(walk_gen))
        expected = "asgiref-3.3.0-py3-none-any.whl-extract"
        self.assertEqual(expected, next(walk_gen).path)

        tree = project_codebase.get_tree()
        with open(self.data_location / "asgiref-3.3.0_tree.json") as f:
            expected = json.loads(f.read())

        self.assertEqual(expected, tree)

    @skipIf(sys.platform != "linux", "Ordering differs on macOS.")
    def test_scanpipe_pipes_codebase_project_codebase_class_walk(self):
        fixtures = self.data_location / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})

        project = Project.objects.get(name="asgiref")
        project_codebase = codebase.ProjectCodebase(project)

        topdown_paths = list(r.path for r in project_codebase.walk(topdown=True))
        expected_topdown_paths = [
            "asgiref-3.3.0-py3-none-any.whl",
            "asgiref-3.3.0-py3-none-any.whl-extract",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/current_thread_executor.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/local.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/server.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/wsgi.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/LICENSE",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/METADATA",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/RECORD",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/"
            "top_level.txt",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/WHEEL",
        ]
        self.assertEqual(expected_topdown_paths, topdown_paths)

        bottom_up_paths = list(r.path for r in project_codebase.walk(topdown=False))
        expected_bottom_up_paths = [
            "asgiref-3.3.0-py3-none-any.whl",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/compatibility.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/current_thread_executor.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/__init__.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/local.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/server.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/sync.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/testing.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/timeout.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref/wsgi.py",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/LICENSE",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/METADATA",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/RECORD",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/"
            "top_level.txt",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info/WHEEL",
            "asgiref-3.3.0-py3-none-any.whl-extract/asgiref-3.3.0.dist-info",
            "asgiref-3.3.0-py3-none-any.whl-extract",
        ]
        self.assertEqual(expected_bottom_up_paths, bottom_up_paths)

    @mock.patch("requests.get")
    def test_scanpipe_pipes_fetch_http(self, mock_get):
        url = "https://example.com/filename.zip"

        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=url
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "filename.zip").exists())

        redirect_url = "https://example.com/redirect.zip"
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url=redirect_url
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "redirect.zip").exists())

        headers = {
            "content-disposition": 'attachment; filename="another_name.zip"',
        }
        mock_get.return_value = mock.Mock(
            content=b"\x00", headers=headers, status_code=200, url=url
        )
        downloaded_file = fetch.fetch_http(url)
        self.assertTrue(Path(downloaded_file.directory, "another_name.zip").exists())

    @mock.patch("scanpipe.pipes.fetch.get_docker_image_platform")
    @mock.patch("scanpipe.pipes.fetch._get_skopeo_location")
    @mock.patch("scanpipe.pipes.run_command")
    def test_scanpipe_pipes_fetch_docker_image(
        self, mock_run_command, mock_skopeo, mock_platform
    ):
        url = "docker://debian:10.9"

        mock_platform.return_value = "linux", "amd64", ""
        mock_skopeo.return_value = "skopeo"
        mock_run_command.return_value = 1, "error"

        with self.assertRaises(fetch.FetchDockerImageError):
            fetch.fetch_docker_image(url)

        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        self.assertTrue(cmd.startswith("skopeo copy --insecure-policy"))
        self.assertIn("docker://debian:10.9 docker-archive:/", cmd)
        self.assertIn("--override-os=linux --override-arch=amd64", cmd)
        self.assertTrue(cmd.endswith("debian_10_9.tar"))

    @mock.patch("requests.get")
    def test_scanpipe_pipes_fetch_fetch_urls(self, mock_get):
        urls = [
            "https://example.com/filename.zip",
            "https://example.com/archive.tar.gz",
        ]

        mock_get.return_value = mock.Mock(
            content=b"\x00", headers={}, status_code=200, url="mocked_url"
        )
        downloads, errors = fetch.fetch_urls(urls)
        self.assertEqual(2, len(downloads))
        self.assertEqual(urls[0], downloads[0].uri)
        self.assertEqual(urls[1], downloads[1].uri)
        self.assertEqual(0, len(errors))

        mock_get.side_effect = Exception
        downloads, errors = fetch.fetch_urls(urls)
        self.assertEqual(0, len(downloads))
        self.assertEqual(2, len(errors))
        self.assertEqual(urls, errors)

    def test_scanpipe_pipes_rootfs_from_project_codebase_class_method(self):
        p1 = Project.objects.create(name="Analysis")
        root_filesystems = list(rootfs.RootFs.from_project_codebase(p1))
        self.assertEqual([], root_filesystems)

        input_location = str(self.data_location / "windows-container-rootfs.tar")
        extract_tar(input_location, target_dir=p1.codebase_path)
        root_filesystems = list(rootfs.RootFs.from_project_codebase(p1))
        self.assertEqual(1, len(root_filesystems))
        distro = root_filesystems[0].distro
        self.assertEqual("windows", distro.os)
        self.assertEqual("windows", distro.identifier)

    def test_scanpipe_pipes_rootfs_tag_empty_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="dir/")
        resource2 = CodebaseResource.objects.create(
            project=p1, path="filename.ext", type=CodebaseResource.Type.FILE
        )

        rootfs.tag_empty_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("ignored-empty-file", resource2.status)

    def test_scanpipe_pipes_rootfs_tag_uninteresting_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        resource2 = CodebaseResource.objects.create(project=p1, rootfs_path="/tmp/file")

        rootfs.tag_uninteresting_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("ignored-not-interesting", resource2.status)

    def test_scanpipe_pipes_rootfs_has_hash_diff(self):
        install_file = mock.Mock(sha256="else", md5="md5")
        codebase_resource = CodebaseResource(sha256="sha256", md5="md5")
        self.assertTrue(rootfs.has_hash_diff(install_file, codebase_resource))

        install_file = mock.Mock(sha512="sha512", md5="md5")
        codebase_resource = CodebaseResource(sha512="sha512", md5="else")
        self.assertTrue(rootfs.has_hash_diff(install_file, codebase_resource))

        install_file = mock.Mock(sha256="sha256", md5="md5")
        codebase_resource = CodebaseResource(sha256="sha256", md5="md5")
        self.assertFalse(rootfs.has_hash_diff(install_file, codebase_resource))

    def test_scanpipe_pipes_resolve_set_license_expression(self):
        declared_license = {"license": "MIT"}
        data = resolve.set_license_expression({"declared_license": declared_license})
        self.assertEqual("mit", data.get("license_expression"))

        declared_license = {
            "classifiers": [
                "License :: OSI Approved :: Python Software Foundation License"
            ]
        }
        data = resolve.set_license_expression({"declared_license": declared_license})
        self.assertEqual("python", data.get("license_expression"))

        declared_license = "GPL 2.0"
        data = resolve.set_license_expression({"declared_license": declared_license})
        self.assertEqual("gpl-2.0", data.get("license_expression"))

    def test_scanpipe_pipes_windows_tag_uninteresting_windows_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/example.lnk",
            rootfs_path="/Files/example.lnk",
            extension=".lnk",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/Hives/Software_Delta",
            rootfs_path="/Hives/Software_Delta",
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/example.dat",
            rootfs_path="/Files/example.dat",
            extension=".dat",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/should-not-be-ignored.txt",
            rootfs_path="/Files/should-not-be-ignored.txt",
            extension=".txt",
        )

        windows.tag_uninteresting_windows_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        self.assertEqual("ignored-not-interesting", resource1.status)
        self.assertEqual("ignored-not-interesting", resource2.status)
        self.assertEqual("ignored-not-interesting", resource3.status)
        self.assertEqual("", resource4.status)

    def test_scanpipe_pipes_windows_tag_known_software(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python/py.exe",
            rootfs_path="/Files/Python/py.exe",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python27/python2.exe",
            rootfs_path="/Files/Python27/python2.exe",
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python3/python3.exe",
            rootfs_path="/Files/Python3/python3.exe",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python39/python3.9",
            rootfs_path="/Files/Python39/python3.9.exe",
        )
        resource5 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
            rootfs_path="/Files/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
        )
        resource6 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/jdk-11.0.1/readme.txt",
            rootfs_path="/Files/jdk-11.0.1/readme.txt",
        )
        resource7 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/openjdk-11.0.1/readme.txt",
            rootfs_path="/Files/openjdk-11.0.1/readme.txt",
        )
        resource8 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/jdk/readme.txt",
            rootfs_path="/Files/jdk/readme.txt",
        )
        resource9 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/openjdk/readme.txt",
            rootfs_path="/Files/openjdk/readme.txt",
        )
        resource10 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/something-else/jdk/readme.txt",
            rootfs_path="/Files/Program Files/something-else/jdk/readme.txt",
        )
        resource11 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python/py.exe",
            rootfs_path="/Python/py.exe",
        )
        resource12 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python27/python2.exe",
            rootfs_path="/Python27/python2.exe",
        )
        resource13 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python3/python3.exe",
            rootfs_path="/Python3/python3.exe",
        )
        resource14 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python39/python3.9",
            rootfs_path="/Python39/python3.9.exe",
        )
        resource15 = CodebaseResource.objects.create(
            project=p1,
            path="root/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
            rootfs_path="/Python39/Lib/site-packages/pip-21.1.3.dist-info/WHEEL",
        )
        resource16 = CodebaseResource.objects.create(
            project=p1,
            path="root/jdk-11.0.1/readme.txt",
            rootfs_path="/jdk-11.0.1/readme.txt",
        )
        resource17 = CodebaseResource.objects.create(
            project=p1,
            path="root/openjdk-11.0.1/readme.txt",
            rootfs_path="/openjdk-11.0.1/readme.txt",
        )
        resource18 = CodebaseResource.objects.create(
            project=p1,
            path="root/jdk/readme.txt",
            rootfs_path="/jdk/readme.txt",
        )
        resource19 = CodebaseResource.objects.create(
            project=p1,
            path="root/openjdk/readme.txt",
            rootfs_path="/openjdk/readme.txt",
        )
        resource20 = CodebaseResource.objects.create(
            project=p1,
            path="root/Program Files/something-else/jdk/readme.txt",
            rootfs_path="/Program Files/something-else/jdk/readme.txt",
        )

        windows.tag_known_software(p1)
        resource11.refresh_from_db()
        resource12.refresh_from_db()
        resource13.refresh_from_db()
        resource14.refresh_from_db()
        resource15.refresh_from_db()
        resource16.refresh_from_db()
        resource17.refresh_from_db()
        resource18.refresh_from_db()
        resource19.refresh_from_db()
        resource20.refresh_from_db()
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        resource5.refresh_from_db()
        resource6.refresh_from_db()
        resource7.refresh_from_db()
        resource8.refresh_from_db()
        resource9.refresh_from_db()
        resource10.refresh_from_db()

        self.assertEqual("installed-package", resource1.status)
        self.assertEqual("installed-package", resource2.status)
        self.assertEqual("installed-package", resource3.status)
        self.assertEqual("installed-package", resource4.status)
        self.assertEqual("", resource5.status)
        self.assertEqual("installed-package", resource6.status)
        self.assertEqual("installed-package", resource7.status)
        self.assertEqual("installed-package", resource8.status)
        self.assertEqual("installed-package", resource9.status)
        self.assertEqual("", resource10.status)
        self.assertEqual("installed-package", resource11.status)
        self.assertEqual("installed-package", resource12.status)
        self.assertEqual("installed-package", resource13.status)
        self.assertEqual("installed-package", resource14.status)
        self.assertEqual("", resource15.status)
        self.assertEqual("installed-package", resource16.status)
        self.assertEqual("installed-package", resource17.status)
        self.assertEqual("installed-package", resource18.status)
        self.assertEqual("installed-package", resource19.status)
        self.assertEqual("", resource20.status)

    def test_scanpipe_pipes_windows_tag_program_files(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files (x86)/Microsoft/example.exe",
            rootfs_path="/Files/Program Files (x86)/Microsoft/example.exe",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/Microsoft/example.exe",
            rootfs_path="/Files/Program Files/Microsoft/example.exe",
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files (x86)/7Zip/7z.exe",
            rootfs_path="/Files/Program Files (x86)/7Zip/7z.exe",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/7Zip/7z.exe",
            rootfs_path="/Files/Program Files/7Zip/7z.exe",
        )
        resource5 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files (x86)/common files/sample.dat",
            rootfs_path="/Files/Program Files (x86)/common files/sample.dat",
        )
        resource6 = CodebaseResource.objects.create(
            project=p1,
            path="root/Files/Program Files/common files/sample.dat",
            rootfs_path="/Files/Program Files/common files/sample.dat",
        )
        windows.tag_program_files(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        resource5.refresh_from_db()
        resource6.refresh_from_db()
        self.assertEqual("", resource1.status)
        self.assertEqual("", resource2.status)
        self.assertEqual("installed-package", resource3.status)
        self.assertEqual("installed-package", resource4.status)
        self.assertEqual("", resource5.status)
        self.assertEqual("", resource6.status)

    def test_scanpipe_pipes_rootfs_tag_ignorable_codebase_resources(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/cmake_install.cmake",
            rootfs_path="/user/cmake_install.cmake",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1, path="root/user/example.pot", rootfs_path="/user/example.pot"
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/__pycache__/foo.pyc",
            rootfs_path="/user/__pycache__/foo.pyc",
        )
        resource4 = CodebaseResource.objects.create(
            project=p1, path="root/user/foo.css.map", rootfs_path="/user/foo.css.map"
        )
        resource5 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/should-not-be-ignored.txt",
            rootfs_path="/user/should-not-be-ignored.txt",
        )
        rootfs.tag_ignorable_codebase_resources(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        resource4.refresh_from_db()
        resource5.refresh_from_db()
        self.assertEqual("ignored-default-ignores", resource1.status)
        self.assertEqual("ignored-default-ignores", resource2.status)
        self.assertEqual("ignored-default-ignores", resource3.status)
        self.assertEqual("ignored-default-ignores", resource4.status)
        self.assertEqual("", resource5.status)

    def test_scanpipe_pipes_rootfs_tag_data_files_with_no_clues(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/foo.data",
            rootfs_path="/user/foo.data",
            file_type="data",
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/bar.data",
            rootfs_path="/user/bar.data",
            file_type="data",
            license_expressions=["apache-2.0"],
        )
        rootfs.tag_data_files_with_no_clues(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        self.assertEqual("ignored-data-file-no-clues", resource1.status)
        self.assertEqual("", resource2.status)

    def test_scanpipe_pipes_rootfs_tag_media_files_as_uninteresting(self):
        p1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/foo.png",
            rootfs_path="/user/foo.png",
            mime_type="image/png",
            file_type="image/png",
            is_media=True,
        )
        resource2 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/bar.jpg",
            rootfs_path="/user/bar.jpg",
            mime_type="image/jpeg",
            file_type="JPEG image data",
            is_media=True,
        )
        resource3 = CodebaseResource.objects.create(
            project=p1,
            path="root/user/baz.txt",
            rootfs_path="/user/baz.txt",
            is_media=False,
        )
        rootfs.tag_media_files_as_uninteresting(p1)
        resource1.refresh_from_db()
        resource2.refresh_from_db()
        resource3.refresh_from_db()
        self.assertEqual("ignored-media-file", resource1.status)
        self.assertEqual("ignored-media-file", resource2.status)
        self.assertEqual("", resource3.status)

    def test_scanpipe_pipes_update_or_create_resource(self):
        p1 = Project.objects.create(name="Analysis")
        resource = update_or_create_resource(p1, resource_data1)
        for field_name, value in resource_data1.items():
            self.assertEqual(value, getattr(resource, field_name), msg=field_name)

    def test_scanpipe_pipes_update_or_create_package(self):
        p1 = Project.objects.create(name="Analysis")
        package = update_or_create_package(p1, package_data1)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", package.purl)
        self.assertEqual("", package.primary_language)
        self.assertEqual(datetime.date(1999, 10, 10), package.release_date)

        updated_data = dict(package_data1)
        updated_data["primary_language"] = "Python"
        updated_package = update_or_create_package(p1, updated_data)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", updated_package.purl)
        self.assertEqual("Python", updated_package.primary_language)
        self.assertEqual(package.pk, updated_package.pk)

        resource1 = CodebaseResource.objects.create(project=p1, path="filename.ext")
        package_data2 = dict(package_data1)
        package_data2["name"] = "new name"
        package_data2["package_uid"] = ""
        package_data2["release_date"] = "2020-11-01T01:40:20"
        package2 = update_or_create_package(p1, package_data2, resource1)
        self.assertNotEqual(package.pk, package2.pk)
        self.assertIn(resource1, package2.codebase_resources.all())
        self.assertEqual(datetime.date(2020, 11, 1), package2.release_date)

    def test_scanpipe_pipes_update_or_create_dependency(self):
        p1 = Project.objects.create(name="Analysis")
        CodebaseResource.objects.create(
            project=p1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        update_or_create_package(p1, package_data1)

        dependency_data = dict(dependency_data1)
        dependency_data["scope"] = ""
        dependency = update_or_create_dependency(p1, dependency_data)
        for field_name, value in dependency_data.items():
            self.assertEqual(value, getattr(dependency, field_name), msg=field_name)

        dependency_data["scope"] = "install"
        dependency = update_or_create_dependency(p1, dependency_data)
        self.assertEqual(dependency.scope, "install")


class ScanPipePipesTransactionTest(TransactionTestCase):
    """
    Since we are testing some Database errors, we need to use a
    TransactionTestCase to avoid any TransactionManagementError while running
    the tests.
    """

    data_location = Path(__file__).parent / "data"

    def test_scanpipe_pipes_make_codebase_resource(self):
        p1 = Project.objects.create(name="Analysis")
        resource_location = str(self.data_location / "notice.NOTICE")

        with self.assertRaises(ValueError) as cm:
            make_codebase_resource(p1, resource_location)

        self.assertIn("not", str(cm.exception))
        self.assertIn(resource_location, str(cm.exception))
        self.assertIn("/codebase", str(cm.exception))

        copy_input(resource_location, p1.codebase_path)
        resource_location = str(p1.codebase_path / "notice.NOTICE")
        make_codebase_resource(p1, resource_location)

        resource = p1.codebaseresources.get()
        self.assertEqual(1178, resource.size)
        self.assertEqual("4bd631df28995c332bf69d9d4f0f74d7ee089598", resource.sha1)
        self.assertEqual("90cd416fd24df31f608249b77bae80f1", resource.md5)
        self.assertEqual("text/plain", resource.mime_type)
        self.assertEqual("ASCII text", resource.file_type)
        self.assertEqual("", resource.status)
        self.assertEqual(CodebaseResource.Type.FILE, resource.type)

        # Duplicated path: skip the creation and no project error added
        make_codebase_resource(p1, resource_location)
        self.assertEqual(1, p1.codebaseresources.count())
        self.assertEqual(0, p1.projecterrors.count())

    def test_scanpipe_add_resource_to_package(self):
        project1 = Project.objects.create(name="Analysis")
        resource1 = CodebaseResource.objects.create(
            project=project1,
            path="filename.ext",
        )
        package1 = update_or_create_package(project1, package_data1)
        self.assertFalse(resource1.for_packages)

        self.assertIsNone(scancode.add_resource_to_package(None, resource1, project1))
        self.assertFalse(resource1.for_packages)

        scancode.add_resource_to_package("not_available", resource1, project1)
        self.assertFalse(resource1.for_packages)
        self.assertEqual(1, project1.projecterrors.count())
        error = project1.projecterrors.get()
        self.assertEqual("assemble_package", error.model)
        expected = {"resource": "filename.ext", "package_uid": "not_available"}
        self.assertEqual(expected, error.details)

        scancode.add_resource_to_package(package1.package_uid, resource1, project1)
        self.assertEqual(len(resource1.for_packages), 1)
        self.assertIn(package1.package_uid, resource1.for_packages)

        # Package will not be added twice since it is already associated with the
        # resource.
        scancode.add_resource_to_package(package1.package_uid, resource1, project1)
        self.assertEqual(len(resource1.for_packages), 1)

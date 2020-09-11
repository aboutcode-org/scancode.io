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

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import TransactionTestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.pipelines import get_pipeline_doc
from scanpipe.tests import package_data1

scanpipe_app_config = apps.get_app_config("scanpipe")


class ScanPipeModelsTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_project_model_extra_data(self):
        self.assertEqual({}, self.project1.extra_data)
        project1_from_db = Project.objects.get(name=self.project1.name)
        self.assertEqual({}, project1_from_db.extra_data)

    def test_scanpipe_project_model_work_directories(self):
        expected_work_directory = (
            f"projects/{self.project1.name}-{self.project1.short_uuid}"
        )
        self.assertTrue(self.project1.work_directory.endswith(expected_work_directory))
        self.assertTrue(self.project1.work_path.exists())
        self.assertTrue(self.project1.input_path.exists())
        self.assertTrue(self.project1.output_path.exists())
        self.assertTrue(self.project1.codebase_path.exists())
        self.assertTrue(self.project1.tmp_path.exists())

    def test_scanpipe_project_model_clear_tmp_directory(self):
        new_file_path = self.project1.tmp_path / "file.ext"
        new_file_path.touch()
        self.assertEqual([new_file_path], list(self.project1.tmp_path.glob("*")))

        self.project1.clear_tmp_directory()
        self.assertTrue(self.project1.tmp_path.exists())
        self.assertEqual([], list(self.project1.tmp_path.glob("*")))

    def test_scanpipe_project_model_inputs_and_input_files_and_input_root(self):
        self.assertEqual([], list(self.project1.inputs()))
        self.assertEqual([], self.project1.input_files)
        self.assertEqual([], self.project1.input_root)

        new_file_path1 = self.project1.input_path / "file.ext"
        new_file_path1.touch()

        new_dir1 = self.project1.input_path / "dir1"
        new_dir1.mkdir(parents=True, exist_ok=True)
        new_file_path2 = new_dir1 / "file2.ext"
        new_file_path2.touch()

        inputs = list(self.project1.inputs())
        expected = [new_dir1, new_file_path1, new_file_path2]
        self.assertEqual(sorted(expected), sorted(inputs))

        expected = ["file.ext", "dir1/file2.ext"]
        self.assertEqual(sorted(expected), sorted(self.project1.input_files))

        expected = ["dir1", "file.ext"]
        self.assertEqual(sorted(expected), sorted(self.project1.input_root))

    def test_scanpipe_project_model_add_input_file(self):
        self.assertEqual([], self.project1.input_files)

        uploaded_file = SimpleUploadedFile("file.ext", content=b"content")
        self.project1.add_input_file(uploaded_file)

        self.assertEqual(["file.ext"], self.project1.input_files)

    def test_scanpipe_project_model_add_pipeline(self):
        self.assertEqual(0, self.project1.runs.count())

        pipeline, _name = scanpipe_app_config.pipelines[0]
        self.project1.add_pipeline(pipeline)

        self.assertEqual(1, self.project1.runs.count())
        run = self.project1.runs.get()
        self.assertEqual(pipeline, run.pipeline)
        self.assertEqual(get_pipeline_doc(pipeline), run.description)

    def test_scanpipe_project_model_get_next_run(self):
        self.assertEqual(None, self.project1.get_next_run())

        run1 = Run.objects.create(project=self.project1, pipeline="pipeline1")
        run2 = Run.objects.create(project=self.project1, pipeline="pipeline2")

        self.assertEqual(run1, self.project1.get_next_run())
        run1.task_id = 1
        run1.save()

        self.assertEqual(run2, self.project1.get_next_run())
        run2.task_id = 2
        run2.save()

        self.assertEqual(None, self.project1.get_next_run())

    def test_scanpipe_run_model_methods(self):
        run1 = Run.objects.create(project=self.project1, pipeline="pipeline")

        self.assertFalse(run1.task_succeeded)
        run1.task_exitcode = 0
        run1.save()
        self.assertTrue(run1.task_succeeded)

        self.assertIsNone(run1.get_run_id())
        run1.task_output = "Workflow starting (run-id 1593181041039832):"
        run1.save()
        self.assertEqual("1593181041039832", run1.get_run_id())

    def test_scanpipe_codebase_resource_model_methods(self):
        resource = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )

        self.assertEqual(
            f"{self.project1.codebase_path}/{resource.path}", resource.location
        )

        with open(resource.location, "w") as f:
            f.write("content")
        self.assertEqual("content", resource.file_content)

        package = DiscoveredPackage.objects.create(project=self.project1)
        resource.discovered_packages.add(package)
        self.assertEqual([str(package.uuid)], resource.for_packages)

        scan_results = {
            "name": "name",
            "extension": "ext",
            "non_resource_field": "value",
        }
        resource.set_scan_results(scan_results, save=True)
        self.assertEqual(scan_results["name"], resource.name)
        self.assertEqual(scan_results["extension"], resource.extension)

    def test_scanpipe_discovered_package_model_create_from_data(self):
        package = DiscoveredPackage.create_from_data(self.project1, package_data1)
        self.assertEqual(self.project1, package.project)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", str(package))
        self.assertEqual("deb", package.type)
        self.assertEqual("debian", package.namespace)
        self.assertEqual("adduser", package.name)
        self.assertEqual("3.118", package.version)
        self.assertEqual("arch=all", package.qualifiers)
        self.assertEqual("add and remove users and groups", package.description)
        self.assertEqual("849", package.size)
        self.assertEqual(
            "gpl-2.0 AND gpl-2.0-plus AND unknown", package.license_expression
        )

    def test_scanpipe_discovered_package_model_create_for_resource(self):
        codebase_resource = CodebaseResource.objects.create(
            project=self.project1, path="filename.ext"
        )
        package = DiscoveredPackage.create_for_resource(
            package_data1, codebase_resource
        )
        self.assertEqual(self.project1, package.project)
        self.assertEqual("pkg:deb/debian/adduser@3.118?arch=all", str(package))
        self.assertEqual(1, codebase_resource.discovered_packages.count())
        self.assertEqual(package, codebase_resource.discovered_packages.get())


class ScanPipeErrorModelsTest(TransactionTestCase):
    """
    Since we are testing some Database errors, we need to use a
    TransactionTestCase to avoid any TransactionManagementError while running
    the tests.
    """

    def test_scanpipe_project_error_model_save_non_valid_related_object(self):
        project1 = Project.objects.create(name="Analysis")
        long_value = "value" * 1000

        package = DiscoveredPackage.objects.create(
            project=project1, filename=long_value
        )
        # The DiscoveredPackage was not created
        self.assertIsNone(package.id)
        self.assertEqual(0, DiscoveredPackage.objects.count())
        # A ProjectError was saved instead
        self.assertEqual(1, project1.projecterrors.count())

        error = project1.projecterrors.get()
        self.assertEqual("DiscoveredPackage", error.model)
        self.assertEqual(long_value, error.details["filename"])
        self.assertEqual(
            "value too long for type character varying(255)\n", error.message
        )

        codebase_resource = CodebaseResource.objects.create(
            project=project1, type=long_value
        )
        self.assertIsNone(codebase_resource.id)
        self.assertEqual(0, CodebaseResource.objects.count())
        self.assertEqual(2, project1.projecterrors.count())

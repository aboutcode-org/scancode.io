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

import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError
from django.core.management import call_command
from django.test import TestCase

from scanpipe.management.commands.graph import graphviz_installed
from scanpipe.models import Project


class ScanPipeManagementCommandTest(TestCase):
    pipeline_location = "scanpipe/pipelines/docker.py"

    def test_scanpipe_management_command_graph(self):
        out = StringIO()
        temp_dir = tempfile.mkdtemp()

        if not graphviz_installed():
            expected = "Graphviz is not installed."
            with self.assertRaisesMessage(CommandError, expected):
                call_command("graph", self.pipeline_location)
            return

        call_command("graph", self.pipeline_location, "--output", temp_dir, stdout=out)
        out_value = out.getvalue()
        self.assertIn("Graph(s) generated:", out_value)
        self.assertIn("DockerPipeline.png", out_value)
        self.assertTrue(Path(f"/{temp_dir}/DockerPipeline.png").exists())

    def test_scanpipe_management_command_create_project_base(self):
        out = StringIO()

        expected = "Error: the following arguments are required: name"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("create-project")

        call_command("create-project", "my_project", stdout=out)
        self.assertIn("Project my_project created", out.getvalue())
        self.assertTrue(Project.objects.get(name="my_project"))

        expected = "Project with this Name already exists."
        with self.assertRaisesMessage(CommandError, expected):
            call_command("create-project", "my_project")

    def test_scanpipe_management_command_create_project_pipelines(self):
        out = StringIO()

        options = ["--pipeline", "non-existing.py"]
        expected = "non-existing.py is not a valid pipeline"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("create-project", "my_project", *options)

        options = [
            "--pipeline",
            "scanpipe/pipelines/docker.py",
            "--pipeline",
            "scanpipe/pipelines/root_filesystems.py",
        ]
        call_command("create-project", "my_project", *options, stdout=out)
        self.assertIn("Project my_project created", out.getvalue())
        project = Project.objects.get(name="my_project")
        expected = [
            "scanpipe/pipelines/docker.py",
            "scanpipe/pipelines/root_filesystems.py",
        ]
        self.assertEqual(expected, [run.pipeline for run in project.runs.all()])

    def test_scanpipe_management_command_create_project_inputs(self):
        out = StringIO()

        options = ["--input", "non-existing.py"]
        expected = "non-existing.py not found or not a file"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("create-project", "my_project", *options)

        parent_path = Path(__file__).parent
        options = [
            "--input",
            str(parent_path / "test_commands.py"),
            "--input",
            str(parent_path / "test_models.py"),
        ]
        call_command("create-project", "my_project", *options, stdout=out)
        self.assertIn("Project my_project created", out.getvalue())
        project = Project.objects.get(name="my_project")
        expected = sorted(["test_commands.py", "test_models.py"])
        self.assertEqual(expected, sorted(project.input_files))

    def test_scanpipe_management_command_add_input(self):
        out = StringIO()

        project = Project.objects.create(name="my_project")
        parent_path = Path(__file__).parent
        options = [
            str(parent_path / "test_commands.py"),
            str(parent_path / "test_models.py"),
        ]

        expected = "the following arguments are required: --project"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("add-input", *options, stdout=out)

        options.extend(["--project", project.name])
        call_command("add-input", *options, stdout=out)
        self.assertIn("File(s) copied to the project inputs directory", out.getvalue())
        expected = sorted(["test_commands.py", "test_models.py"])
        self.assertEqual(expected, sorted(project.input_files))

        options = ["--project", project.name, "non-existing.py"]
        expected = "non-existing.py not found or not a file"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("add-input", *options, stdout=out)

    def test_scanpipe_management_command_add_pipeline(self):
        out = StringIO()

        project = Project.objects.create(name="my_project")

        pipelines = [
            "scanpipe/pipelines/docker.py",
            "scanpipe/pipelines/root_filesystems.py",
        ]

        options = pipelines[:]
        expected = "the following arguments are required: --project"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("add-pipeline", *options, stdout=out)

        options.extend(["--project", project.name])
        call_command("add-pipeline", *options, stdout=out)
        self.assertIn("Pipeline(s) added to the project", out.getvalue())
        self.assertEqual(pipelines, [run.pipeline for run in project.runs.all()])

        options = ["--project", project.name, "non-existing.py"]
        expected = "non-existing.py is not a valid pipeline"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("add-pipeline", *options, stdout=out)

    def test_scanpipe_management_command_show_pipeline(self):
        pipelines = [
            "scanpipe/pipelines/docker.py",
            "scanpipe/pipelines/root_filesystems.py",
        ]

        project = Project.objects.create(name="my_project")
        for pipeline_location in pipelines:
            project.add_pipeline(pipeline_location)

        options = ["--project", project.name, "--no-color"]
        out = StringIO()
        call_command("show-pipeline", *options, stdout=out)
        expected = (
            " [ ] scanpipe/pipelines/docker.py\n"
            " [ ] scanpipe/pipelines/root_filesystems.py\n"
        )
        self.assertEqual(expected, out.getvalue())

        project.runs.filter(pipeline=pipelines[0]).update(task_exitcode=0)
        project.runs.filter(pipeline=pipelines[1]).update(task_exitcode=1)

        out = StringIO()
        call_command("show-pipeline", *options, stdout=out)
        expected = (
            " [S] scanpipe/pipelines/docker.py\n"
            " [F] scanpipe/pipelines/root_filesystems.py\n"
        )
        self.assertEqual(expected, out.getvalue())

    def test_scanpipe_management_command_run(self):
        out = StringIO()

        project = Project.objects.create(name="my_project")
        options = ["--project", project.name]

        expected = "No pipelines to run on Project my_project"
        with self.assertRaisesMessage(CommandError, expected):
            call_command("run", *options, stdout=out)

        pipeline = "scanpipe/pipelines/docker.py"
        project.add_pipeline(pipeline)
        call_command("run", *options, stdout=out)

        expected = "Pipeline scanpipe/pipelines/docker.py run in progress..."
        self.assertIn(expected, out.getvalue())

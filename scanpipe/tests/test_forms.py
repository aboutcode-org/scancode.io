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

import uuid
from unittest import mock

from django.test import TestCase

import requests
import saneyaml

from scanpipe.forms import EditInputSourceTagForm
from scanpipe.forms import InputsBaseForm
from scanpipe.forms import PipelineRunStepSelectionForm
from scanpipe.forms import ProjectForm
from scanpipe.forms import ProjectSettingsForm
from scanpipe.models import Project
from scanpipe.models import Run
from scanpipe.tests import global_policies
from scanpipe.tests import license_policies_index
from scanpipe.tests.pipelines.do_nothing import DoNothing


class ScanPipeFormsTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    @mock.patch("requests.sessions.Session.head")
    def test_scanpipe_forms_inputs_base_form_input_urls(self, mock_head):
        data = {
            "input_urls": "Docker://debian",
        }
        form = InputsBaseForm(data=data)
        self.assertFalse(form.is_valid())
        error_msg = "URL scheme 'Docker' is not supported. Did you mean: 'docker'?"
        self.assertEqual({"input_urls": [error_msg]}, form.errors)

        data = {
            "input_urls": "https://example.com/archive.zip",
        }
        mock_head.side_effect = requests.exceptions.RequestException
        form = InputsBaseForm(data=data)
        self.assertFalse(form.is_valid())
        expected = {"input_urls": ["Could not fetch:\nhttps://example.com/archive.zip"]}
        self.assertEqual(expected, form.errors)

        mock_head.side_effect = None
        mock_head.return_value = mock.Mock(headers={}, status_code=200)
        form = InputsBaseForm(data=data)
        self.assertTrue(form.is_valid())
        form.handle_inputs(project=self.project1)

        inputs_with_source = self.project1.get_inputs_with_source()
        expected = [
            {
                "uuid": str(self.project1.inputsources.get().uuid),
                "filename": "",
                "download_url": "https://example.com/archive.zip",
                "is_uploaded": False,
                "tag": "",
                "size": None,
                "is_file": True,
                "exists": False,
            }
        ]
        self.assertEqual(expected, inputs_with_source)

    def test_scanpipe_forms_project_form_name(self):
        data = {
            "name": "  Test   Name   ",
            "pipeline": "scan_codebase",
        }
        form = ProjectForm(data=data)
        self.assertTrue(form.is_valid())
        obj = form.save()
        self.assertEqual("Test Name", obj.name)

    def test_scanpipe_forms_project_form_pipeline_choices(self):
        blank_entry = ("", "---------")
        main_pipeline = ("scan_codebase", "scan_codebase")
        addon_pipeline = ("find_vulnerabilities", "find_vulnerabilities")

        choices = ProjectForm().fields["pipeline"].choices
        self.assertIn(blank_entry, choices)
        self.assertIn(main_pipeline, choices)
        self.assertNotIn(addon_pipeline, choices)

    def test_scanpipe_forms_project_settings_form_update_name_and_notes(self):
        data = {
            "name": "new name",
            "notes": "some notes",
        }
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertTrue(form.is_valid())
        project = form.save()
        self.assertEqual(data["name"], project.name)
        self.assertEqual(data["notes"], project.notes)

    def test_scanpipe_forms_project_settings_form_set_initial_from_settings_field(self):
        form = ProjectSettingsForm()
        self.assertIsNone(form.fields["product_name"].initial)

        self.assertEqual({}, self.project1.settings)
        form = ProjectSettingsForm(instance=self.project1)
        self.assertIsNone(form.fields["product_name"].initial)

        self.project1.settings = {"product_name": "Product"}
        self.project1.save()
        form = ProjectSettingsForm(instance=self.project1)
        self.assertEqual("Product", form.fields["product_name"].initial)

    def test_scanpipe_forms_project_settings_form_update_project_settings(self):
        data = {
            "name": self.project1.name,
            "ignored_patterns": "*.ext\ndir/*",
        }
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertTrue(form.is_valid())
        project = form.save()

        expected = {
            "ignored_patterns": ["*.ext", "dir/*"],
            "ignored_vulnerabilities": None,
            "policies": "",
            "ignored_dependency_scopes": None,
            "scan_max_file_size": None,
            "product_name": "",
            "product_version": "",
            "attribution_template": "",
        }
        self.assertEqual(expected, project.settings)
        expected = {
            "ignored_patterns": ["*.ext", "dir/*"],
        }
        self.assertEqual(expected, project.get_env())

    def test_scanpipe_forms_project_settings_form_ignored_dependency_scopes(self):
        data = {
            "name": self.project1.name,
            "ignored_dependency_scopes": "",
        }
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertTrue(form.is_valid())

        data["ignored_dependency_scopes"] = "bad"
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertFalse(form.is_valid())
        expected = {
            "ignored_dependency_scopes": [
                "Invalid input line: 'bad'. Each line must contain exactly one ':' "
                "character."
            ]
        }
        self.assertEqual(expected, form.errors)

        data["ignored_dependency_scopes"] = "npm:"
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertFalse(form.is_valid())

        expected = {
            "ignored_dependency_scopes": [
                "Invalid input line: 'npm:'. Both key and value must be non-empty."
            ]
        }
        self.assertEqual(expected, form.errors)

        data["ignored_dependency_scopes"] = "npm:devDependencies\npypi:tests"
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertTrue(form.is_valid())

        project = form.save()
        expected = {
            "ignored_patterns": None,
            "ignored_vulnerabilities": None,
            "ignored_dependency_scopes": [
                {"package_type": "npm", "scope": "devDependencies"},
                {"package_type": "pypi", "scope": "tests"},
            ],
            "scan_max_file_size": None,
            "attribution_template": "",
            "policies": "",
            "product_name": "",
            "product_version": "",
        }
        self.assertEqual(expected, project.settings)
        expected = {
            "ignored_dependency_scopes": [
                {"package_type": "npm", "scope": "devDependencies"},
                {"package_type": "pypi", "scope": "tests"},
            ]
        }
        self.assertEqual(expected, project.get_env())

    def test_scanpipe_forms_project_settings_form_policies(self):
        data = {
            "name": self.project1.name,
            "policies": "{not valid}",
        }
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertFalse(form.is_valid())
        expected = {
            "policies": [
                "At least one of the following policy types must be present: "
                "license_clarity_thresholds, license_policies, "
                "scorecard_score_thresholds"
            ]
        }
        self.assertEqual(expected, form.errors)

        policies_as_yaml = saneyaml.dump(global_policies)
        data["policies"] = policies_as_yaml
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertTrue(form.is_valid())
        project = form.save()
        self.assertEqual(policies_as_yaml.strip(), project.settings["policies"])
        self.assertEqual(license_policies_index, project.get_license_policy_index())

    def test_scanpipe_forms_project_settings_form_purl(self):
        data_invalid_purl = {
            "name": "proj name",
            "purl": "pkg/npm/lodash@4.17.21",
        }
        data_valid_purl = {
            "name": "proj name",
            "purl": "pkg:npm/lodash@4.17.21",
        }

        form1 = ProjectSettingsForm(data=data_invalid_purl)
        self.assertFalse(form1.is_valid())

        form2 = ProjectSettingsForm(data=data_valid_purl)
        self.assertTrue(form2.is_valid())
        obj = form2.save()
        self.assertEqual("pkg:npm/lodash@4.17.21", obj.purl)

    def test_scanpipe_forms_edit_input_source_tag_form(self):
        data = {}
        form = EditInputSourceTagForm(data=data)
        self.assertFalse(form.is_valid())

        data = {
            "input_source_uuid": uuid.uuid4(),
            "tag": "value",
        }
        form = EditInputSourceTagForm(data=data)
        self.assertTrue(form.is_valid())
        obj = form.save(project=self.project1)
        self.assertIsNone(obj)

        input_source = self.project1.add_input_source(
            filename="filename.zip",
            is_uploaded=True,
            tag="base value",
        )
        data = {
            "input_source_uuid": input_source.uuid,
            "tag": "new value",
        }
        form = EditInputSourceTagForm(data=data)
        self.assertTrue(form.is_valid())
        obj = form.save(project=self.project1)
        self.assertEqual(obj, input_source)
        self.assertEqual(data["tag"], obj.tag)

    def test_scanpipe_forms_pipeline_run_step_selection_form_choices(self):
        with self.assertRaises(ValueError):
            PipelineRunStepSelectionForm()

        run = Run.objects.create(project=self.project1, pipeline_name="do_nothing")
        form = PipelineRunStepSelectionForm(instance=run)
        choices = form.fields["selected_steps"].choices

        expected = [("step1", "step1"), ("step2", "step2")]
        self.assertEqual(expected, choices)
        choices = PipelineRunStepSelectionForm.get_step_choices(DoNothing)
        self.assertEqual(expected, choices)
        self.assertEqual({"selected_steps": ["step1", "step2"]}, form.initial)

    def test_scanpipe_forms_pipeline_run_step_selection_form_save(self):
        run = Run.objects.create(project=self.project1, pipeline_name="do_nothing")
        data = {"selected_steps": "invalid"}
        form = PipelineRunStepSelectionForm(data=data, instance=run)
        self.assertFalse(form.is_valid())

        data = {"selected_steps": ["step1"]}
        form = PipelineRunStepSelectionForm(data=data, instance=run)
        self.assertTrue(form.is_valid())
        form.save()
        run.refresh_from_db()
        self.assertEqual(["step1"], run.selected_steps)

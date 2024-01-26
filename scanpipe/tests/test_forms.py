#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from unittest import mock

from django.test import TestCase

import requests

from scanpipe.forms import InputsBaseForm
from scanpipe.forms import ProjectForm
from scanpipe.forms import ProjectSettingsForm
from scanpipe.models import Project


class ScanPipeFormsTest(TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    @mock.patch("requests.head")
    def test_scanpipe_forms_inputs_base_form_input_urls(self, mock_head):
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
        main_pipline = ("scan_codebase", "scan_codebase")
        addon_pipline = ("find_vulnerabilities", "find_vulnerabilities")

        choices = ProjectForm().fields["pipeline"].choices
        self.assertIn(blank_entry, choices)
        self.assertIn(main_pipline, choices)
        self.assertNotIn(addon_pipline, choices)

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
        self.assertTrue(form.fields["extract_recursively"].initial)

        self.assertEqual({}, self.project1.settings)
        form = ProjectSettingsForm(instance=self.project1)
        self.assertTrue(form.fields["extract_recursively"].initial)

        self.project1.settings = {"extract_recursively": False}
        self.project1.save()
        form = ProjectSettingsForm(instance=self.project1)
        self.assertFalse(form.fields["extract_recursively"].initial)

    def test_scanpipe_forms_project_settings_form_update_project_settings(self):
        data = {
            "name": self.project1.name,
            "extract_recursively": False,
            "ignored_patterns": "*.ext\ndir/*",
            "scancode_license_score": 10,
        }
        form = ProjectSettingsForm(data=data, instance=self.project1)
        self.assertTrue(form.is_valid())
        project = form.save()

        expected = {
            "extract_recursively": False,
            "ignored_patterns": ["*.ext", "dir/*"],
            "attribution_template": "",
            "scancode_license_score": 10,
        }
        self.assertEqual(expected, project.settings)
        expected = {
            "extract_recursively": False,
            "ignored_patterns": ["*.ext", "dir/*"],
            "scancode_license_score": 10,
        }
        self.assertEqual(expected, project.get_env())

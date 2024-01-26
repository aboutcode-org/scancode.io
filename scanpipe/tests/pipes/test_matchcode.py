#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from scanpipe.models import Project
from scanpipe.pipes import matchcode


class MatchCodePipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_matchcode_fingerprint_codebase_directories(self):
        fixtures = self.data_location / "asgiref-3.3.0_fixtures.json"
        call_command("loaddata", fixtures, **{"verbosity": 0})
        project = Project.objects.get(name="asgiref")

        matchcode.fingerprint_codebase_directories(project)
        directory = project.codebaseresources.get(
            path="asgiref-3.3.0-py3-none-any.whl-extract"
        )
        expected_directory_fingerprints = {
            "directory_content": "0000000ef11d2819221282031466c11a367bba72",
            "directory_structure": "0000000e0e30a50b5eb8c495f880c087325e6062",
        }
        self.assertEqual(expected_directory_fingerprints, directory.extra_data)

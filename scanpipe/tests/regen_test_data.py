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
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.test import override_settings

import requests
from scorecode.ossf_scorecard import fetch_scorecard

from scanpipe.models import Project
from scanpipe.pipes import codebase
from scanpipe.pipes import input
from scanpipe.pipes import output
from scanpipe.pipes import scancode


class RegenTestData(TestCase):
    """
    Regen the scan and fixtures test files following a toolkit upgrade.

    Since this module name is not following the default "test_*" pattern,
    it is ignored during the tests' discovery.

    It can be run by providing the `--pattern` argument to the `test` command.

    Usages:

    - Docker:
    $ docker compose run --rm --volume "$(pwd)/scanpipe/":/opt/scancodeio/scanpipe/ \
        web ./manage.py test --pattern "regen*.py"

    Warning: Once the test data is updated, run the whole test suite with the
    `SCANCODEIO_TEST_FIXTURES_REGEN` setting enabled to regen the expected files.

    - Local:
    $ SCANCODEIO_TEST_FIXTURES_REGEN=True ./manage.py test

    - Docker:
    $ docker compose run --rm --volume "$(pwd)/scanpipe/":/opt/scancodeio/scanpipe/ \
        -e SCANCODEIO_TEST_FIXTURES_REGEN=True web ./manage.py test
    """

    data = Path(__file__).parent / "data"

    def test_regen_asgiref_test_files(self):
        pipeline_name = "scan_codebase"
        project1 = Project.objects.create(name="asgiref")

        filename = "asgiref-3.3.0-py3-none-any.whl"
        input_location = self.data / "asgiref" / filename
        project1.copy_input_from(input_location)
        project1.add_input_source(filename=filename, is_uploaded=True)
        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        with override_settings(SCANCODEIO_PROCESSES=-1):
            exitcode, _ = pipeline.execute()
        self.assertEqual(0, exitcode)

        # ScanCode-toolkit scan result
        scancode.run_scan(
            location=str(project1.codebase_path),
            output_file=str(self.data / "asgiref" / "asgiref-3.3.0_toolkit_scan.json"),
            run_scan_args={
                "copyright": True,
                "info": True,
                "license": True,
                "package": True,
            },
            processes=1,
        )

        # ScanCode.io results
        test_file_location = (
            self.data / "asgiref" / "asgiref-3.3.0_scanpipe_output.json"
        )
        result_file = output.to_json(project1)
        result_json = json.loads(Path(result_file).read_text())
        test_file_location.write_text(json.dumps(result_json, indent=2))

        # Model fixtures
        fixtures_test_file_location = (
            self.data / "asgiref" / "asgiref-3.3.0_fixtures.json"
        )
        models = [
            "scanpipe.project",
            "scanpipe.run",
            "scanpipe.codebaseresource",
            "scanpipe.discoveredpackage",
            "scanpipe.discovereddependency",
        ]
        call_command("dumpdata", models, indent=2, output=fixtures_test_file_location)

        # Walk test fixtures
        test_file_location = (
            self.data / "asgiref" / "asgiref-3.3.0_walk_test_fixtures.json"
        )
        with open(fixtures_test_file_location) as f:
            fixtures = json.load(f)
        for fixture in fixtures:
            fixture_path = fixture.get("fields", {}).get("path")
            if fixture_path:
                # Truncate "asgiref-3.3.0-py3-none-any.whl" to "asgiref-3.3.0.whl"
                # This is done to avoid having too long of paths for test
                # expectations
                fixture_path = fixture_path.replace("-py3-none-any", "")
                fixture["fields"]["path"] = fixture_path
        test_file_location.write_text(json.dumps(fixtures, indent=2))

        # Codebase tree
        test_file_location = self.data / "asgiref" / "asgiref-3.3.0_tree.json"
        pc = codebase.ProjectCodebase(project1)
        project_tree = codebase.get_codebase_tree(codebase=pc, fields=["name", "path"])
        test_file_location.write_text(json.dumps(project_tree, indent=2))

        # Load inventory expected file
        project2 = Project.objects.create(name="package_assembly")
        filename = "package_assembly_codebase.tar.gz"
        input_file = self.data / "scancode" / filename
        project2.copy_input_from(input_location)
        input.copy_input(input_file, project2.codebase_path)
        scancode.extract_archives(location=project2.codebase_path)
        scan_location = str(
            project2.codebase_path / "package_assembly_codebase.tar.gz-extract/"
        )
        json_filename = "package_assembly_codebase.json"
        scancode.run_scan(
            location=scan_location,
            output_file=str(self.data / "scancode" / json_filename),
            run_scan_args={
                "info": True,
                "package": True,
            },
            processes=1,
        )

    def test_regenerate_scorecard_data(self):
        """Regenerate and save scorecard data by calling the OSSF Scorecard API."""
        scorecard_data_file = self.data / "scorecode" / "scorecard_response.json"
        platform, org, repo = "github.com", "nexB", "scancode-toolkit"

        try:
            scorecard_data = fetch_scorecard(platform, org, repo)
        except requests.exceptions.Timeout:
            raise RuntimeError("The request to the OSSF Scorecard API timed out.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error fetching scorecard data: {e}")

        scorecard_data_file.parent.mkdir(parents=True, exist_ok=True)
        scorecard_data_file.write_text(json.dumps(scorecard_data.to_dict(), indent=2))

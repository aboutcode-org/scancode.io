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

from pathlib import Path

from django.test import TestCase

from scanpipe.tests import make_project


class ScanPipeSCAIntegrationsTest(TestCase):
    data = Path(__file__).parent / "data"

    def test_scanpipe_scan_integrations_load_sbom_trivy(self):
        # Input file generated with:
        # $ trivy image --scanners vuln,license --format cyclonedx \
        #     --output trivy-alpine-3.17-sbom.json alpine:3.17.0
        input_location = self.data / "sca-integrations" / "trivy-alpine-3.17-sbom.json"

        pipeline_name = "load_sbom"
        project1 = make_project()
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(1, project1.codebaseresources.count())
        self.assertEqual(16, project1.discoveredpackages.count())
        self.assertEqual(7, project1.discoveredpackages.vulnerable().count())
        self.assertEqual(25, project1.discovereddependencies.count())

    def test_scanpipe_scan_integrations_load_sbom_anchore(self):
        # Input file generated with:
        # $ grype -v -o cyclonedx-json \
        #     --file anchore-alpine-3.17-sbom.json alpine:3.17.0
        input_location = (
            self.data / "sca-integrations" / "anchore-alpine-3.17-sbom.json"
        )

        pipeline_name = "load_sbom"
        project1 = make_project()
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(1, project1.codebaseresources.count())
        self.assertEqual(94, project1.discoveredpackages.count())
        self.assertEqual(7, project1.discoveredpackages.vulnerable().count())
        self.assertEqual(20, project1.discovereddependencies.count())

    def test_scanpipe_scan_integrations_load_sbom_cdxgen(self):
        # Input file generated with:
        # $ cdxgen alpine:3.17.0 --type docker --spec-version 1.6 --json-pretty \
        #     --output cdxgen-alpine-3.17-sbom.json
        input_location = self.data / "sca-integrations" / "cdxgen-alpine-3.17-sbom.json"

        pipeline_name = "load_sbom"
        project1 = make_project()
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(1, project1.codebaseresources.count())
        self.assertEqual(14, project1.discoveredpackages.count())
        self.assertEqual(0, project1.discoveredpackages.vulnerable().count())
        self.assertEqual(0, project1.discovereddependencies.count())

    def test_scanpipe_scan_integrations_load_sbom_depscan(self):
        # Input file generated with:
        # $ depscan --src alpine:3.17.0 --type docker
        input_location = (
            self.data / "sca-integrations" / "depscan-alpine-3.17-sbom.json"
        )

        pipeline_name = "load_sbom"
        project1 = make_project()
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(1, project1.codebaseresources.count())
        self.assertEqual(33, project1.discoveredpackages.count())
        self.assertEqual(3, project1.discoveredpackages.vulnerable().count())
        self.assertEqual(20, project1.discovereddependencies.count())

    def test_scanpipe_scan_integrations_load_sbom_sbomtool(self):
        # Input file generated with:
        # $ sbom-tool generate -di alpine:3.17.0 \
        #   -pn DockerImage -pv 1.0.0 -ps Company -nsb https://sbom.company.com
        input_location = (
            self.data / "sca-integrations" / "sbom-tool-alpine-3.17-sbom.spdx.json"
        )

        pipeline_name = "load_sbom"
        project1 = make_project()
        project1.copy_input_from(input_location)

        run = project1.add_pipeline(pipeline_name)
        pipeline = run.make_pipeline_instance()

        exitcode, out = pipeline.execute()
        self.assertEqual(0, exitcode, msg=out)

        self.assertEqual(1, project1.codebaseresources.count())
        self.assertEqual(16, project1.discoveredpackages.count())
        self.assertEqual(0, project1.discoveredpackages.vulnerable().count())
        self.assertEqual(16, project1.discovereddependencies.count())

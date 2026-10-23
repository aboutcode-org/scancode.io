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

from django.test import TestCase

import yaml

from scancodeio import ROOT_DIR
from scancodeio import extract_short_commit


class ScanCodeIOTest(TestCase):
    def test_scancodeio_extract_short_commit(self):
        self.assertEqual(extract_short_commit(""), "")
        self.assertEqual(extract_short_commit("v32.6.0-44-ga8980bd"), "a8980bd")
        self.assertEqual(extract_short_commit("v1.0.0-1-g123456"), "123456")
        self.assertEqual(extract_short_commit("v2.0.0-5-abcdefg"), "abcdefg")
        self.assertEqual(extract_short_commit("v1.5.0-2-ghijkl"), "hijkl")

    def test_scancodeio_docker_compose_web_service_has_healthcheck(self):
        # Without a healthcheck, `docker compose up --wait` only waits for the
        # "web" container to be running, not for its migrate/collectstatic
        # steps to complete. This lets a `docker compose run web scanpipe ...`
        # command race ahead of the database migrations.
        # See https://github.com/aboutcode-org/scancode.io/issues/1842
        compose_file = ROOT_DIR.joinpath("docker-compose.yml")
        compose_data = yaml.safe_load(compose_file.read_text())
        self.assertIn("healthcheck", compose_data["services"]["web"])

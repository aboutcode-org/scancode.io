# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from unittest import mock

from django.test import TestCase

from scorecode.models import PackageScore

from scanpipe.pipes import scorecard
from scanpipe.tests import make_package
from scanpipe.tests import make_project


class ScanPipeScorecardPipesTest(TestCase):
    def test_scanpipe_pipes_scorecard_is_scorecard_repository_url(self):
        scored_urls = [
            "https://github.com/ossf/scorecard",
            "git+https://github.com/ossf/scorecard.git",
            "https://www.github.com/ossf/scorecard",
            "https://gitlab.com/gitlab-org/gitlab",
            "https://www.gitlab.com/gitlab-org/gitlab",
        ]
        for vcs_url in scored_urls:
            self.assertTrue(scorecard.is_scorecard_repository_url(vcs_url), vcs_url)

        not_scored_urls = [
            "",
            "https://github.com.example.org/ossf/scorecard",
            "https://example-github.com/ossf/scorecard",
            "https://gist.github.com/ossf/scorecard",
            "https://gitlab.com.example.org/gitlab-org/gitlab",
            "https://example.org/github.com/ossf/scorecard",
        ]
        for vcs_url in not_scored_urls:
            self.assertFalse(scorecard.is_scorecard_repository_url(vcs_url), vcs_url)

    @mock.patch("scorecode.ossf_scorecard.fetch_scorecard_info")
    def test_scanpipe_pipes_scorecard_fetch_packages_scores(self, mock_fetch):
        project = make_project()
        scored_package = make_package(
            project, "pkg:npm/scored@1.0", vcs_url="https://github.com/ossf/scorecard"
        )
        lookalike_package = make_package(
            project,
            "pkg:npm/lookalike@1.0",
            vcs_url="https://github.com.example.org/ossf/scorecard",
        )
        mock_fetch.return_value = PackageScore(
            scoring_tool="ossf_scorecard",
            scoring_tool_version="v5.2.1",
            score="8.3",
            scoring_tool_documentation_url="https://github.com/ossf/scorecard",
            score_date="2025-07-24T18:50:16Z",
        )

        scorecard.fetch_packages_scores(project)

        mock_fetch.assert_called_once_with(package=scored_package)
        self.assertEqual(
            ["8.3"], [score.score for score in scored_package.scores.all()]
        )
        self.assertFalse(lookalike_package.scores.exists())

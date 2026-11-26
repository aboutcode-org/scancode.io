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

from urllib.parse import urlsplit

from scorecode import ossf_scorecard

from scanpipe.models import DiscoveredPackageScore

# The repository hosts scored by the OpenSSF Scorecard API.
SCORECARD_REPOSITORY_HOSTS = (
    "github.com",
    "www.github.com",
    "gitlab.com",
    "www.gitlab.com",
)


def is_scorecard_repository_url(vcs_url):
    """Return True if the host of the ``vcs_url`` is a scored repository host."""
    # ScoreCode maps any host containing a scored host, such as
    # "github.com.example.org", to the scores of the same repository path on the
    # scored host: only the exact hosts are looked up.
    return urlsplit(vcs_url).hostname in SCORECARD_REPOSITORY_HOSTS


def fetch_packages_scores(project):
    """Fetch and store the OpenSSF Scorecard scores of the ``project`` packages."""
    for package in project.discoveredpackages.all():
        if not is_scorecard_repository_url(package.vcs_url):
            continue

        if scorecard_data := ossf_scorecard.fetch_scorecard_info(package=package):
            DiscoveredPackageScore.create_from_package_and_scorecard(
                scorecard_data=scorecard_data,
                package=package,
            )

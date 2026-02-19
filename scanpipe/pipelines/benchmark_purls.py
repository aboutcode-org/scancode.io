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

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import benchmark


class BenchmarkPurls(Pipeline):
    """
    Validate discovered project packages against a reference list of expected PURLs.

    The expected PURLs must be provided as a .txt file with one PURL per line.
    Input files are recognized if:

    - They are tagged with "purls", or
    - Their filename ends with "purls.txt" (e.g., "expected_purls.txt").

    """

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (
            cls.get_expected_purls,
            cls.compare_purls,
        )

    def get_expected_purls(self):
        """Load the expected PURLs defined in the project inputs."""
        self.expected_purls = benchmark.get_expected_purls(self.project)

    def compare_purls(self):
        """Run the PURLs diff and write the results to a project output file."""
        diff_results = benchmark.compare_purls(self.project, self.expected_purls)
        output_file = self.project.get_output_file_path("benchmark_purls", "txt")
        output_file.write_text("\n".join(diff_results))

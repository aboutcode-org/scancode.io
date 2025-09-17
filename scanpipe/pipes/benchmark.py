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

import difflib


def get_expected_purls(project):
    """
    Load the expected Package URLs (PURLs) from the project's input files.

    A file is considered an expected PURLs source if:
    - Its filename ends with ``*purls.txt``, or
    - Its download URL includes the "#purls" tag.

    Each line in the file should contain one PURL. Returns a sorted,
    deduplicated list of PURLs. Raises an exception if no input is found.
    """
    purls_files = list(project.inputs("*purls.txt"))
    purls_files.extend(
        [input.path for input in project.inputsources.filter(tag="purls")]
    )

    expected_purls = []
    for file_path in purls_files:
        expected_purls.extend(file_path.read_text().splitlines())

    if not expected_purls:
        raise Exception("Expected PURLs not provided.")

    return sorted(set(expected_purls))


def get_unique_project_purls(project):
    """
    Return the sorted list of unique Package URLs (PURLs) discovered in the project.

    Extracts the ``purl`` field from all discovered packages, removes duplicates,
    and sorts the result to provide a deterministic list of project PURLs.
    """
    project_packages = project.discoveredpackages.only_package_url_fields()
    sorted_unique_purls = sorted({package.purl for package in project_packages})
    return sorted_unique_purls


def compare_purls(project, expected_purls):
    """
    Compare discovered project PURLs against the expected PURLs.

    Returns only the differences:
    - Lines starting with '-' are missing from the project.
    - Lines starting with '+' are unexpected in the project.
    """
    sorted_project_purls = get_unique_project_purls(project)
    diff_result = difflib.ndiff(sorted_project_purls, expected_purls)

    # Keep only lines that are diffs (- or +)
    filtered_diff = [line for line in diff_result if line.startswith(("-", "+"))]

    return filtered_diff

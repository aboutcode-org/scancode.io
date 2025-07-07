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

from collections import Counter

STRING_MATCHING_RATIO_JAVASCRIPT = 0.7
SMALL_FILE_STRING_THRESHOLD_JAVASCRIPT = 10
STRING_MATCHING_RATIO_JAVASCRIPT_SMALL_FILE = 0.5


def match_source_strings_to_deployed(source_strings, deployed_strings):
    """
    Compute the similarity between source and deployed string literals and
    return whether they match based on matching threshold.
    """
    common_strings_ratio = 0
    is_match = False
    deployed_strings_set = set(deployed_strings)
    source_strings_set = set(source_strings)
    source_strings_count = len(source_strings)
    deployed_strings_count = len(deployed_strings)
    total_strings_count = source_strings_count + deployed_strings_count
    source_strings_counter = Counter(source_strings)
    deployed_strings_counter = Counter(deployed_strings)

    common_strings = source_strings_set.intersection(deployed_strings_set)
    total_common_strings_count = sum(
        [
            source_strings_counter.get(string, 0)
            + deployed_strings_counter.get(string, 0)
            for string in common_strings
        ]
    )

    if total_common_strings_count:
        common_strings_ratio = total_common_strings_count / total_strings_count

    if common_strings_ratio > STRING_MATCHING_RATIO_JAVASCRIPT:
        is_match = True
    elif (
        source_strings_count > SMALL_FILE_STRING_THRESHOLD_JAVASCRIPT
        and common_strings_ratio > STRING_MATCHING_RATIO_JAVASCRIPT_SMALL_FILE
    ):
        is_match = True

    return is_match, common_strings_ratio

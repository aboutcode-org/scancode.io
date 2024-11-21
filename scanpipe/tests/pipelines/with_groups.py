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

from aboutcode.pipeline import optional_step
from scanpipe.pipelines import Pipeline


class WithGroups(Pipeline):
    """Include "grouped" steps."""

    download_inputs = False

    @classmethod
    def steps(cls):
        return (
            cls.grouped_with_foo_and_bar,
            cls.grouped_with_bar,
            cls.grouped_with_excluded,
            cls.no_groups,
        )

    @optional_step("foo", "bar")
    def grouped_with_foo_and_bar(self):
        """Step1 doc."""
        pass

    @optional_step("bar")
    def grouped_with_bar(self):
        """Step2 doc."""
        pass

    @optional_step("excluded")
    def grouped_with_excluded(self):
        """Step2 doc."""
        pass

    def no_groups(self):
        """Step2 doc."""
        pass

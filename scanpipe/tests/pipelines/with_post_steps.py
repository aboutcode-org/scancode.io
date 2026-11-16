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

from aboutcode.pipeline import optional_step
from scanpipe.pipelines import Pipeline


class WithPostSteps(Pipeline):
    """Run the post steps at the end, even after a failure."""

    download_inputs = False

    @classmethod
    def steps(cls):
        return (
            cls.step1,
            cls.step2,
        )

    @classmethod
    def get_post_steps(cls):
        return (
            cls.post_step1,
            cls.post_step2,
            cls.optional_post_step,
        )

    def step1(self):
        raise ValueError("Error in step1")

    def step2(self):
        pass

    def post_step1(self):
        raise ValueError("Error in post_step1")

    def post_step2(self):
        pass

    @optional_step("cleanup")
    def optional_post_step(self):
        pass

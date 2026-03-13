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

import subprocess

from scanpipe.pipes import run_command_safely


def build_crates(cargo_toml_path, build_dir):
    """
    Build the Rust crate using Cargo to ensure that the source code compiles correctly.

    This step is crucial for validating the integrity of the source code and ensuring
    that it can be successfully built. It also helps to identify any discrepancies
    between the source code and the compiled binary, which can be further analyzed
    in subsequent steps of the pipeline.
    """
    cmd = [
        "cargo",
        "build",
        "--locked",
        "--manifest-path",
        str(cargo_toml_path),
        "--target-dir",
        str(build_dir),
    ]

    try:
        run_command_safely(cmd)
    except subprocess.SubprocessError as error:
        raise RuntimeError(f"Failed to build the Rust crate: {error}")

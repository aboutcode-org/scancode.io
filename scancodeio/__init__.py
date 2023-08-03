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

import os
import subprocess
import sys
import warnings
from pathlib import Path

VERSION = "32.5.0"

PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parent
SCAN_NOTICE = PROJECT_DIR.joinpath("scan.NOTICE").read_text()


def get_version(version):
    """Return the version including the git describe tag when available."""
    # The codebase is a git clone
    if git_describe := get_git_describe_from_command():
        return git_describe

    # The codebase is an extracted git archive
    if git_describe := get_git_describe_from_version_file():
        return git_describe

    return version


def get_git_describe_from_command():
    """
    Return the git describe tag from executing the ``git describe --tags`` command.
    This will only provide a result when the codebase is a git clone.
    """
    git_describe = subprocess.run(
        "git describe --tags",
        capture_output=True,
        shell=True,
        text=True,
    )
    return git_describe.stdout.strip()


def get_git_describe_from_version_file(version_file_location=ROOT_DIR / ".VERSION"):
    """
    Return the git describe tag from the ".VERSION" file.
    This will only provide a result when the codebase is an extracted git archive
    """
    try:
        version = version_file_location.read_text().strip()
    except (FileNotFoundError, UnicodeDecodeError):
        return

    if version and version.startswith("v"):
        return version


__version__ = get_version(VERSION)


# Turn off the warnings for the following modules.
warnings.filterwarnings("ignore", module="extractcode")
warnings.filterwarnings("ignore", module="typecode")


def command_line():
    """Command line entry point."""
    from django.core.management import execute_from_command_line

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scancodeio.settings")
    execute_from_command_line(sys.argv)

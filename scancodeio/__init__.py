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

import os
import sys
import warnings
from contextlib import suppress
from pathlib import Path

import git

VERSION = "36.1.0"

PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parent
SCAN_NOTICE = PROJECT_DIR.joinpath("scan.NOTICE").read_text()
GITHUB_URL = "https://github.com/aboutcode-org/scancode.io"


def get_version(version):
    """Return the version including the git describe tag when available."""
    # The codebase is a git clone
    if git_describe := get_git_describe_from_local_checkout():
        return git_describe

    # The codebase is an extracted git archive
    if git_describe := get_git_describe_from_version_file():
        return git_describe

    return version


def get_git_describe_from_local_checkout():
    """
    Return the git describe tag from the local checkout.
    This will only provide a result when the codebase is a git clone.
    """
    with suppress(git.GitError):
        return git.Repo(".").git.describe(tags=True, always=True)


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


def extract_short_commit(git_describe):
    """
    Extract the short commit hash from a Git describe string while removing
    any leading "g" character if present.
    """
    short_commit = git_describe.split("-")[-1]
    return short_commit.lstrip("g")


__version__ = get_version(VERSION)


# Turn off the warnings for the following modules.
warnings.filterwarnings("ignore", module="extractcode")
warnings.filterwarnings("ignore", module="typecode")
warnings.filterwarnings("ignore", module="clamd")


def command_line():
    """Command line entry point."""
    from django.core.management import execute_from_command_line

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scancodeio.settings")
    execute_from_command_line(sys.argv)


def combined_run():
    """
    Command line entry point for executing pipeline as a single command.

    This function sets up a pre-configured settings context, requiring no additional
    configuration.
    It combines the creation, execution, and result retrieval of the project into a
    single process.

    Set SCANCODEIO_NO_AUTO_DB=1 to use the database configuration from the settings
    instead of SQLite.
    """
    from django.core.checks.security.base import SECRET_KEY_INSECURE_PREFIX
    from django.core.management import execute_from_command_line
    from django.core.management.utils import get_random_secret_key

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scancodeio.settings")
    secret_key = SECRET_KEY_INSECURE_PREFIX + get_random_secret_key()
    os.environ.setdefault("SECRET_KEY", secret_key)

    # Default to SQLite unless SCANCODEIO_NO_AUTO_DB is provided
    if not os.getenv("SCANCODEIO_NO_AUTO_DB"):
        os.environ.setdefault("SCANCODEIO_DB_ENGINE", "django.db.backends.sqlite3")
        os.environ.setdefault("SCANCODEIO_DB_NAME", "scancodeio.sqlite3")
        os.environ.setdefault("SCANCODEIO_PROCESSES", "0")  # Disable multiprocessing

    sys.argv.insert(1, "run")
    execute_from_command_line(sys.argv)

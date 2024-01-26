#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import os
import sys
import warnings
from contextlib import suppress
from pathlib import Path

import git

VERSION = "33.0.0"

PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parent
SCAN_NOTICE = PROJECT_DIR.joinpath("scan.NOTICE").read_text()
GITHUB_URL = "https://github.com/nexB/scancode.io"


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


def command_line():
    """Command line entry point."""
    from django.core.management import execute_from_command_line

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scancodeio.settings")
    execute_from_command_line(sys.argv)

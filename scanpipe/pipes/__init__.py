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

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from time import sleep

from django.db.models import Count

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.pipes import scancode

logger = logging.getLogger("scanpipe.pipes")


def make_codebase_resource(project, location, **extra_fields):
    """
    Creates a CodebaseResource instance in the database for the given `project`.

    The provided `location` is the absolute path of this resource.
    It must be rooted in `project.codebase_path` as only the relative path within the
    project codebase/ directory is stored in the database.

    Extra fields can be provided as keywords arguments to this function call:

    >>> make_codebase_resource(
    >>>     project=project,
    >>>     location=resource.location,
    >>>     rootfs_path=resource.path,
    >>>     tag=layer_tag,
    >>> )

    In this example, `rootfs_path` is an optional path relative to a rootfs root
    within an Image/VM filesystem context. e.g.: "/var/log/file.log"

    All paths use the POSIX separators.

    If a CodebaseResource already exists in the `project` with the same path,
    the error raised on save() is not stored in the database and the creation is
    skipped.
    """
    relative_path = Path(location).relative_to(project.codebase_path)
    resource_data = scancode.get_resource_info(location=location)

    if extra_fields:
        resource_data.update(**extra_fields)

    codebase_resource = CodebaseResource(
        project=project,
        path=relative_path,
        **resource_data,
    )
    codebase_resource.save(save_error=False)


def update_or_create_package(project, package_data, codebase_resource=None):
    """
    Gets, updates or creates a DiscoveredPackage then returns it.
    Uses the `project` and `package_data` mapping to lookup and creates the
    DiscoveredPackage using its Package URL and package_uid as a unique key.
    """
    purl_data = DiscoveredPackage.extract_purl_data(package_data)

    try:
        package = DiscoveredPackage.objects.get(
            project=project,
            package_uid=package_data.get("package_uid"),
            **purl_data,
        )
    except DiscoveredPackage.DoesNotExist:
        package = None

    if package:
        package.update_from_data(package_data)
    else:
        if codebase_resource:
            package = codebase_resource.create_and_add_package(package_data)
        else:
            package = DiscoveredPackage.create_from_data(project, package_data)

    return package


def update_or_create_dependencies(project, dependency_data, datafile_resource=None):
    """
    Gets, updates or creates a DiscoveredDependency then returns it.
    Uses the `project` and `dependency_data` mapping to lookup and creates the
    DiscoveredDependency using its dependency_uid and for_package_uid as a unique key.
    """
    try:
        dependency = project.discovereddependencys.get(
            dependency_uid=dependency_data.get("dependency_uid")
        )
    except DiscoveredDependency.DoesNotExist:
        dependency = None

    if dependency:
        dependency.update_from_data(dependency_data)
    else:
        dependency = DiscoveredDependency.create_from_data(
            project,
            dependency_data,
            datafile_resource=datafile_resource,
        )

    return dependency


def analyze_scanned_files(project):
    """
    Sets the status for CodebaseResource to unknown or no license.
    """
    scanned_files = project.codebaseresources.files().status("scanned")

    scanned_files.has_no_licenses().update(status="no-licenses")
    scanned_files.unknown_license().update(status="unknown-license")


def tag_not_analyzed_codebase_resources(project):
    """
    Flags any of the `project`'s '`CodebaseResource` without a status as "not-analyzed".
    """
    project.codebaseresources.no_status().update(status="not-analyzed")


def normalize_path(path):
    """
    Returns a normalized path from a `path` string.
    """
    return "/" + path.strip("/")


def strip_root(location):
    """
    Returns the provided `location` without the root directory.
    """
    return "/".join(str(location).strip("/").split("/")[1:])


def filename_now(sep="-"):
    """
    Returns the current date and time in iso format suitable for filename.
    """
    now = datetime.now().isoformat(sep=sep, timespec="seconds")
    return now.replace(":", sep)


def count_group_by(queryset, field_name):
    """
    Returns a summary of all existing values for the provided `field_name` on the
    `queryset`, including the count of each entry, as a dictionary.
    """
    counts = (
        queryset.values(field_name)
        .annotate(count=Count(field_name))
        .order_by(field_name)
    )

    return {entry.get(field_name): entry.get("count") for entry in counts}


def get_bin_executable(filename):
    """
    Returns the location of the `filename` executable binary.
    """
    return str(Path(sys.executable).parent / filename)


def _stream_process(process, stream_to=logger.info):
    exitcode = process.poll()

    for line in process.stdout:
        stream_to(line.rstrip("\n"))

    has_terminated = exitcode is not None
    return has_terminated


def run_command(cmd, log_output=False):
    """
    Returns (exitcode, output) of executing the provided `cmd` in a shell.
    `cmd` can be provided as a string or as a list of arguments.

    If `log_output` is True, the stdout and stderr of the process will be captured
    and streamed to the `logger`.
    """
    if isinstance(cmd, list):
        cmd = " ".join(cmd)

    if not log_output:
        exitcode, output = subprocess.getstatusoutput(cmd)
        return exitcode, output

    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    while _stream_process(process):
        sleep(1)

    exitcode = process.poll()
    return exitcode, ""


def remove_prefix(text, prefix):
    """
    Removes the `prefix` from `text`.
    """
    if text.startswith(prefix):
        prefix_len = len(prefix)
        return text[prefix_len:]
    return text

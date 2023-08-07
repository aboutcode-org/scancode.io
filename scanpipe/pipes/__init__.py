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

import difflib
import logging
import subprocess
import sys
import uuid
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from time import sleep
from timeit import default_timer as timer

from django.db.models import Count

from scanpipe import humanize_time
from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.pipes import scancode

logger = logging.getLogger("scanpipe.pipes")


def make_codebase_resource(project, location, save=True, **extra_fields):
    """
    Create a CodebaseResource instance in the database for the given ``project``.

    The provided ``location`` is the absolute path of this resource.
    It must be rooted in `project.codebase_path` as only the relative path within the
    project codebase/ directory is stored in the database.

    Extra fields can be provided as keywords arguments to this function call::

        make_codebase_resource(
            project=project,
            location=resource.location,
            rootfs_path=resource.path,
            tag=layer_tag,
        )

    In this example, ``rootfs_path`` is an optional path relative to a rootfs root
    within an Image/VM filesystem context. e.g.: "/var/log/file.log"

    All paths use the POSIX separators.

    If a CodebaseResource already exists in the ``project`` with the same path,
    the error raised on save() is not stored in the database and the creation is
    skipped.
    """
    relative_path = Path(location).relative_to(project.codebase_path)
    resource_data = scancode.get_resource_info(location=str(location))

    if extra_fields:
        resource_data.update(**extra_fields)

    codebase_resource = CodebaseResource(
        project=project,
        path=relative_path,
        **resource_data,
    )

    if save:
        codebase_resource.save(save_error=False)
    return codebase_resource


def update_or_create_resource(project, resource_data):
    """Get, update or create a CodebaseResource then return it."""
    for_packages = resource_data.pop("for_packages", None) or []

    resource = CodebaseResource.objects.get_or_none(
        project=project,
        path=resource_data.get("path"),
    )

    if resource:
        resource.update_from_data(resource_data)
    else:
        resource = CodebaseResource.create_from_data(project, resource_data)

    for package_uid in for_packages:
        package = project.discoveredpackages.get(package_uid=package_uid)
        resource.add_package(package)

    return resource


def _clean_package_data(package_data):
    """Clean provided `package_data` to make it compatible with the model."""
    package_data = package_data.copy()
    if release_date := package_data.get("release_date"):
        if type(release_date) is str:
            if release_date.endswith("Z"):
                release_date = release_date[:-1]
            package_data["release_date"] = datetime.fromisoformat(release_date).date()
    return package_data


def update_or_create_package(project, package_data, codebase_resources=None):
    """
    Get, update or create a DiscoveredPackage then return it.
    Use the `project` and `package_data` mapping to lookup and creates the
    DiscoveredPackage using its Package URL and package_uid as a unique key.
    The package can be associated to `codebase_resources` providing a list or queryset
    of resources.
    """
    purl_data = DiscoveredPackage.extract_purl_data(package_data)
    package_data = _clean_package_data(package_data)
    # No values for package_uid requires to be empty string for proper queryset lookup
    package_uid = package_data.get("package_uid") or ""

    package = DiscoveredPackage.objects.get_or_none(
        project=project,
        package_uid=package_uid,
        **purl_data,
    )

    if package:
        package.update_from_data(package_data)
    else:
        package = DiscoveredPackage.create_from_data(project, package_data)

    if codebase_resources:
        package.add_resources(codebase_resources)

    return package


def update_or_create_dependency(
    project, dependency_data, for_package=None, strip_datafile_path_root=False
):
    """
    Get, update or create a DiscoveredDependency then returns it.
    Use the `project` and `dependency_data` mapping to lookup and creates the
    DiscoveredDependency using its dependency_uid and for_package_uid as a unique key.

    If `strip_datafile_path_root` is True, then
    `DiscoveredDependency.create_from_data()` will strip the root path segment
    from the `datafile_path` of `dependency_data` before looking up the
    corresponding CodebaseResource for `datafile_path`. This is used in the case
    where Dependency data is imported from a scancode-toolkit scan, where the
    root path segments are not stripped for `datafile_path`.
    """
    dependency = None
    dependency_uid = dependency_data.get("dependency_uid")

    if not dependency_uid:
        dependency_data["dependency_uid"] = uuid.uuid4()
    else:
        dependency = project.discovereddependencies.get_or_none(
            dependency_uid=dependency_uid,
        )

    if dependency:
        dependency.update_from_data(dependency_data)
    else:
        dependency = DiscoveredDependency.create_from_data(
            project,
            dependency_data,
            for_package=for_package,
            strip_datafile_path_root=strip_datafile_path_root,
        )

    return dependency


def get_or_create_relation(project, relation_data):
    """
    Get  or create a CodebaseRelation then return it.
    The support for update is not useful as there is no fields on the model that
    could be updated.
    """
    from_resource_path = relation_data.get("from_resource")
    to_resource_path = relation_data.get("to_resource")
    resource_qs = project.codebaseresources

    codebase_relation, _ = CodebaseRelation.objects.get_or_create(
        project=project,
        from_resource=resource_qs.get(path=from_resource_path),
        to_resource=resource_qs.get(path=to_resource_path),
        map_type=relation_data.get("map_type"),
    )

    return codebase_relation


def make_relation(from_resource, to_resource, map_type, **extra_fields):
    return CodebaseRelation.objects.create(
        project=from_resource.project,
        from_resource=from_resource,
        to_resource=to_resource,
        map_type=map_type,
        **extra_fields,
    )


def normalize_path(path):
    """Return a normalized path from a `path` string."""
    return "/" + path.strip("/")


def strip_root(location):
    """Return the provided `location` without the root directory."""
    return "/".join(str(location).strip("/").split("/")[1:])


def filename_now(sep="-"):
    """Return the current date and time in iso format suitable for filename."""
    now = datetime.now().isoformat(sep=sep, timespec="seconds")
    return now.replace(":", sep)


def count_group_by(queryset, field_name):
    """
    Return a summary of all existing values for the provided `field_name` on the
    `queryset`, including the count of each entry, as a dictionary.
    """
    counts = (
        queryset.values(field_name)
        .annotate(count=Count(field_name))
        .order_by(field_name)
    )

    return {entry.get(field_name): entry.get("count") for entry in counts}


def get_bin_executable(filename):
    """Return the location of the `filename` executable binary."""
    return str(Path(sys.executable).parent / filename)


def _stream_process(process, stream_to=logger.info):
    exitcode = process.poll()

    for line in process.stdout:
        stream_to(line.rstrip("\n"))

    has_terminated = exitcode is not None
    return has_terminated


def run_command(cmd, log_output=False):
    """
    Return (exitcode, output) of executing the provided `cmd` in a shell.
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
    Remove the `prefix` from `text`.
    Note that build-in `removeprefix` was added in Python3.9 but we need to keep
    this one for Python3.8 support.
    https://docs.python.org/3.9/library/stdtypes.html#str.removeprefix
    """
    if text.startswith(prefix):
        prefix_len = len(prefix)
        return text[prefix_len:]
    return text


def get_progress_percentage(current_index, total_count):
    """
    Return the percentage of progress given the current index and total count of
    objects.
    """
    if current_index < 0 or current_index >= total_count:
        raise ValueError("current_index must be between 0 and total_count - 1")

    progress = current_index / total_count * 100
    return progress


def log_progress(
    log_func,
    current_index,
    total_count,
    last_percent,
    increment_percent,
    start_time=None,
):
    """
    Log progress updates every `increment_percent` percentage points, given the
    current index and total count of objects.
    Return the latest percent logged.
    """
    progress_percentage = int(get_progress_percentage(current_index, total_count))
    if progress_percentage >= last_percent + increment_percent:
        last_percent = progress_percentage
        msg = f"Progress: {progress_percentage}% ({current_index:,d}/{total_count:,d})"

        if start_time:
            run_time = timer() - start_time
            eta = round(run_time / progress_percentage * (100 - progress_percentage))
            if eta:
                msg += f" ETA: {humanize_time(eta)}"

        log_func(msg)

    return last_percent


def get_text_str_diff_ratio(str_a, str_b):
    """
    Return a similarity ratio as a float between 0 and 1 by comparing the
    text content of the ``str_a`` and ``str_b``.

    Return None if any of the two resources str is empty.
    """
    if not (str_a and str_b):
        return

    if not isinstance(str_a, str) or not isinstance(str_b, str):
        raise ValueError("Values must be str")

    matcher = difflib.SequenceMatcher(a=str_a.splitlines(), b=str_b.splitlines())
    return matcher.quick_ratio()


def get_resource_diff_ratio(resource_a, resource_b):
    """
    Return a similarity ratio as a float between 0 and 1 by comparing the
    text content of the CodebaseResource ``resource_a`` and ``resource_b``.

    Return None if any of the two resources are not readable as text.
    """
    with suppress(IOError):
        return get_text_str_diff_ratio(
            str_a=resource_a.file_content,
            str_b=resource_b.file_content,
        )

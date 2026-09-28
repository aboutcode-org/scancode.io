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

import fcntl
import logging
import shutil
import subprocess
import time
import uuid
from contextlib import contextmanager
from fnmatch import fnmatch

import requests
from license_expression import Licensing

from scanpipe.pipes import fetch
from scanpipe.pipes import flag

logger = logging.getLogger(__name__)

_GENERIC_FAILURE = 1


def validate_package_license_integrity(project):
    """Validate the correctness of the package license."""
    # Patterns to ignore certain resources during license validation
    ignore_patterns = [
        "*test*",
        "*.sh",
    ]

    for package in project.discoveredpackages.all():
        package_lic = package.get_declared_license_expression()
        if package_lic:
            if package.type == "cargo":
                # A single cargo package only has one Cargo.toml file
                # meaning only one package is defined. Therefore, we don't
                # need to check for the package_uid
                # In addition, the package_uid is not populated to source files:
                # https://github.com/aboutcode-org/scancode.io/issues/2169
                # so we set package_uid to None to consider all resources
                # in the codebase for license validation.
                package_uid = None
            else:
                package_uid = package.package_uid
            resources = project.codebaseresources.has_license_expression()
            detected_lic_list = collect_detected_licenses(
                resources, ignore_patterns, package_uid
            )

            if detected_lic_list:
                lic_exp = " AND ".join(detected_lic_list)
                detected_lic_exp = str(Licensing().dedup(lic_exp))

                if detected_lic_exp != package_lic:
                    package_issues = package.extra_data.get("issues", [])

                    package_issues.append(
                        {
                            "issue_type": "License Mismatch",
                            "declared_license": package_lic,
                            "detected_codebase_license": detected_lic_exp,
                        }
                    )

                    package.update_extra_data({"issues": package_issues})

                    for datafile_path in package.datafile_paths:
                        if not datafile_path.startswith("https://"):
                            data_path = project.codebaseresources.get(
                                path=datafile_path
                            )
                            data_path.update(status=flag.LICENSE_ISSUE)

                            resource_issues = data_path.extra_data.get("issues", [])
                            resource_issues.append(
                                {
                                    "issue_type": "License Mismatch",
                                    "declared_license": package_lic,
                                    "detected_codebase_license": detected_lic_exp,
                                }
                            )

                            data_path.update_extra_data({"issues": resource_issues})


def contains_ignore_pattern(resource_path, ignore_patterns):
    """Check if the resource path matches any of the ignore patterns."""
    for pattern in ignore_patterns:
        if fnmatch(resource_path, pattern):
            return True
    return False


def filter_ignored_licenses(license_expression, licensing):
    """Filter out ignored licenses from a license expression."""
    # Some licenses are not useful for validating package license
    # integrity, so we ignore them.
    ignored_licenses = [
        "free-unknown",
        "unknown",
        "unknown-license-reference",
        "unknown-spdx",
    ]

    if license_expression is None:
        return None

    if isinstance(license_expression, licensing.Symbol):
        if (
            hasattr(license_expression, "key")
            and license_expression.key in ignored_licenses
        ):
            return None
        return license_expression

    # Handle AND operations
    if isinstance(license_expression, licensing.AND):
        return handle_operator_expression(license_expression, licensing, licensing.AND)

    # Handle OR operations
    if isinstance(license_expression, licensing.OR):
        return handle_operator_expression(license_expression, licensing, licensing.OR)

    return license_expression


def handle_operator_expression(expression, licensing, operator):
    """
    Process AND/OR operations in a license expression, filtering out
    ignored licenses.
    """
    args = []
    for arg in expression.args:
        filtered_arg = filter_ignored_licenses(arg, licensing)
        if filtered_arg is not None:
            args.append(filtered_arg)
    if not args:
        return None
    if len(args) == 1:
        return args[0]

    return operator(*args)


def collect_detected_licenses(resources, ignore_patterns, package_uid=None):
    """Collect detected licenses from resources, ignoring defined patterns."""
    licensing = Licensing()
    detected_lic_list = []

    for resource in resources:
        if contains_ignore_pattern(resource.path, ignore_patterns):
            continue

        # If a package_uid is provided, only consider resources linked to it
        if package_uid and package_uid not in resource.for_packages:
            continue

        license_str = resource.detected_license_expression
        if not license_str:
            continue
        try:
            parsed_lic = licensing.parse(license_str)

            # Filter out the ignored keys
            filtered_license = filter_ignored_licenses(parsed_lic, licensing)

            if filtered_license is not None:
                final_lic = str(filtered_license)

                if final_lic not in detected_lic_list:
                    # Apply parentheses so that the 'OR' expression will
                    # not be filtered out when doing deduplication later.
                    detected_lic_list.append(f"({final_lic})")

        except Exception:
            logger.warning(
                "Failed to parse the license expression: %s at %s",
                license_str,
                resource.path,
            )
    return detected_lic_list


def fetch_path(purl):
    """Fetch the purl and return the location of the fetched tarball"""
    try:
        return fetch.fetch_url(url=purl).path
    except (ValueError, requests.RequestException) as e:
        logger.warning("Failed to fetch package: %s - %s", purl, e)
        return None


def check_docker_command():
    """Check if the Docker command is available and the daemon is running."""
    docker_path = shutil.which("docker")
    if not docker_path:
        return False

    try:
        subprocess.run([docker_path, "info"], capture_output=True, check=True)  # noqa: S603
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@contextmanager
def file_lock(lock_path):
    """
    Exclusive cross-process lock backed by `fcntl.flock`.

    Blocks until the lock is free. Released when the `with` block exits or
    the process dies.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # "a" mode avoids truncating the lock file on every acquisition.
    with open(lock_path, "a") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def docker_image_exists(image):
    """Return True if the "image" is present in the local Docker image store."""
    cmd = ["docker", "image", "inspect", image]
    result = subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603
    return result.returncode == 0


def docker_rm_force(container_name):
    """Remove a container left behind after a timeout."""
    cmd = ["docker", "rm", "-f", container_name]
    subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        check=False,
    )


def container_state(container_name):
    """Return the container's state string, e.g. "created", or "" if unknown."""
    cmd = ["docker", "inspect", "--format", "{{.State.Status}}", container_name]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.strip()
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return ""


def rename_container(cmd, new_name):
    """Return a copy of a `docker run` command with its `--name` value replaced."""
    cmd = list(cmd)
    try:
        idx = cmd.index("--name")
    except ValueError:
        return cmd
    if idx + 1 < len(cmd):
        cmd[idx + 1] = new_name
    return cmd


def is_startup_race(returncode, stderr):
    """
    Return True if `docker run` failed with a startup race unique to
    Docker Desktop.

    A startup race is when two things happen at once and the wrong one
    wins. Docker Desktop exposes host directories to its container VM
    through a bridge that can lag a few milliseconds behind the host, so
    the daemon sometimes tries to use a path or rootfs before it has
    propagated. The failure is transient; a retry usually succeeds.

    Two scenarios:

    - Exit code 125 with `error mounting`: the bind-mount source was
      not visible yet.
    - `[FATAL tini`: the container started before the rootfs was fully
      mounted, so `/bin/sh` could not be resolved.

    Native Linux has no bridge, so neither occurs there.
    """
    if not stderr:
        return False
    if returncode == 125 and "error mounting" in stderr:
        return True
    if "[FATAL tini" in stderr:
        return True
    return False


def run_docker_container(cmd, container_name, timeout, task_description, retries=1):
    """
    Run `docker run` with a timeout and grace window, retrying automatically
    if a transient Docker Desktop startup race occurs or the daemon wedges.

    Return a CompletedProcess on success. Raise CalledProcessError on a
    real failure, or TimeoutExpired on a genuine timeout.
    """
    grace = 15

    for attempt in range(retries + 1):
        if attempt:
            logger.warning(f"{task_description}: retrying container in 5s")
            time.sleep(5)
            prefix = container_name.rsplit("-", 1)[0]
            container_name = f"{prefix}-{uuid.uuid4().hex[:12]}"
            cmd = rename_container(cmd, container_name)

        # Popen (not run) so we can inspect the daemon state after the grace
        # window, while the container may still be running.
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait up to `grace` seconds for docker run to finish,
            # capturing its stdout and stderr. The timeout is what lets us
            # detect a wedged daemon instead of blocking forever.
            stdout, stderr = proc.communicate(timeout=grace)
        except subprocess.TimeoutExpired:
            # Still running past the grace window. If the daemon never
            # actually started it, the state will be 'created' and no
            # amount of waiting will help.
            if container_state(container_name) == "created":
                proc.kill()
                proc.communicate()
                docker_rm_force(container_name)
                if attempt >= retries:
                    raise subprocess.CalledProcessError(
                        _GENERIC_FAILURE,
                        cmd,
                        stderr=(
                            f"container {container_name} stuck in "
                            f"'Created' state after {grace}s"
                        ),
                    )
                continue

            # The container is actually running. Wait out the rest of
            # the timeout.
            try:
                stdout, stderr = proc.communicate(timeout=max(1, timeout - grace))
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                state = container_state(container_name)
                logger.error(
                    f"{task_description}: timeout after {timeout}s; "
                    f"container state={state!r}"
                )
                docker_rm_force(container_name)
                raise

        if proc.returncode == 0:
            return subprocess.CompletedProcess(cmd, 0, stdout, stderr)

        if attempt < retries and is_startup_race(proc.returncode, stderr):
            logger.warning(
                f"{task_description}: startup race for {container_name}; retrying in 5s"
            )
            docker_rm_force(container_name)
            continue

        docker_rm_force(container_name)
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=stdout, stderr=stderr
        )

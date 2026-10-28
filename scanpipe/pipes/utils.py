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
import os
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

_DOCKER_CHECK_TIMEOUT = 5
_DOCKER_IMAGE_INSPECT_TIMEOUT = 30
_DOCKER_RM_TIMEOUT = 60

DEFAULT_DOCKER_SOCKET = "/var/run/docker.sock"


def check_docker_command():
    """Check if the Docker command is available and the daemon is running."""
    docker_path = shutil.which("docker")
    if not docker_path:
        return False

    try:
        subprocess.run(  # noqa: S603
            [docker_path, "info"],
            capture_output=True,
            check=True,
            timeout=_DOCKER_CHECK_TIMEOUT,
        )
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
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            check=False,
            timeout=_DOCKER_IMAGE_INSPECT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            f"docker image inspect {image} timed out after "
            f"{_DOCKER_IMAGE_INSPECT_TIMEOUT}s; treating as missing."
        )
        return False
    return result.returncode == 0


def docker_rm_force(container_name):
    """Remove a container left behind after a timeout."""
    cmd = ["docker", "rm", "-f", container_name]
    try:
        subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            check=False,
            timeout=_DOCKER_RM_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            f"docker rm -f {container_name} timed out after "
            f"{_DOCKER_RM_TIMEOUT}s; container may linger."
        )


def run_docker_container(cmd, container_name, timeout, task_description):
    """
    Run a `docker run` command with a timeout. The container is force-removed
    on failure or timeout so it does not linger in the daemon.

    Return a CompletedProcess on success. Raise CalledProcessError on failure,
    or TimeoutExpired on a genuine timeout.
    """
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except subprocess.TimeoutExpired:
        logger.error(
            f"{task_description}: timeout after {timeout}s; removing container"
        )
        docker_rm_force(container_name)
        raise
    except subprocess.CalledProcessError as exception:
        logger.error(
            f"{task_description}: container {container_name} exited with "
            f"{exception.returncode}; stderr={exception.stderr}"
        )
        docker_rm_force(container_name)
        raise

    return result


def has_docker_endpoint():
    """Return True when a Docker daemon endpoint is configured or present."""
    if os.environ.get("DOCKER_HOST"):
        return True
    return Path(DEFAULT_DOCKER_SOCKET).exists()

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

import hashlib
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlencode

import requests
from fetchcode import fetch_json_response
from packageurl import PackageURL

from scanpipe import pipes
from scanpipe.pipes import fetch
from scanpipe.pipes import utils
from scanpipe.pipes.resolve import convert_spdx_expression
from scanpipe.settings import scanpipe_settings

logger = logging.getLogger(__name__)


# Result of `get_patched_source_with_docker`:
# - `path`: extracted source tree, or "" when nothing could be produced
# - `used_fallback`: True when the patched-source build failed and we fell
#   back to the raw upstream `pkg.src` (unpatched)
# - `fallback_reason`: reason for the fallback, or ""
# - `failure_detail`: reason the fetch failed, or ""
PatchedSourceResult = namedtuple(
    "PatchedSourceResult",
    ["path", "used_fallback", "fallback_reason", "failure_detail"],
)

FALLBACK_REASON_PREFIX = "PATCHED_SOURCE_FALLBACK_REASON="


_DOCKER_BUILD_TIMEOUT = 1800
_DOCKER_IO_TIMEOUT = 600
_DOCKER_EVAL_TIMEOUT = 300

_binfmt_emulation_is_installed_cache = None

# `tonistiigi/binfmt` runs a `--privileged` container to read the host
# kernel's `/proc/sys/fs/binfmt_misc`. Pinned by digest so a tag update
# on the registry cannot silently swap the privileged container image.
# Update deliberately; refresh with:
#   docker inspect --format='{{index .RepoDigests 0}}' tonistiigi/binfmt
_BINFMT_CHECK_IMAGE = (
    "tonistiigi/binfmt@"
    "sha256:400a4873b838d1b89194d982c45e5fb3cda4593fbfd7e08a02e76b03b21166f0"
)


# Markers to identify meaningful failure lines in `nix-build` stderr.
_NIX_ERROR_MARKERS = (
    "Encountered missing or private dependencies:",
    "error: Cannot build",
    "error: builder failed",
)


# The name, commit, system, and output values are used in Nix code, shell
# scripts, git commands, and file paths. They must be carefully checked
# before use.
#
# The following patterns do not have `^`/`$` anchors as they are used with
# `.fullmatch()`, which already requires the entire string to match.
#
# NIX_NAME_RE keeps the value free of whitespace, "/", and shell
# metacharacters. It is the primary defense against injection; every Nix
# expression below also passes user input via `--argstr`, which treats
# the value as data, never as code.
NIX_NAME_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_\-+.]*")
# A git commit ID under SHA-1 is exactly 40 lowercase hex characters.
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
# A Nix system name has the form <arch>-<os>, e.g. x86_64-linux or
# aarch64-darwin.
SYSTEM_RE = re.compile(r"[a-z0-9_]+-[a-z0-9_]+")
# Common Nix output names: "out", "dev", "doc", "bin", "lib", "libexec",
# "share", "man", plus multi-output variants such as "lib32" and "lib64".
# The first character must be a letter so that "." and ".." are rejected.
OUTPUT_RE = re.compile(r"[a-z][a-z0-9]*")

# Official repository used to verify that a commit is not from a fork.
NIXPKGS_OWNER = "NixOS"
NIXPKGS_REPO = "nixpkgs"
NIXPKGS_DEFAULT_BRANCH = "nixos-unstable"


def _summarize_nix_build_error(stderr, max_lines=10):
    """
    Extract the meaningful failure from `nix-build` stderr.

    nix-build writes hundreds of lines of progress output ("copying
    path...", phase names) around the one or two lines that explain
    why the build failed. Return a short excerpt so the project's error
    message is actionable.
    """
    if not stderr:
        return ""

    lines = stderr.strip().splitlines()
    for i, line in enumerate(lines):
        if any(marker in line for marker in _NIX_ERROR_MARKERS):
            summary = "\n".join(lines[i : i + max_lines])
            if "Encountered missing or private dependencies:" in line:
                summary += (
                    "\n\nHint: this Haskell package targets an older compiler than "
                    "the one in this nixpkgs commit. Try an older commit, or a "
                    "Haskell package set that uses a matching compiler."
                )
            return summary

    return lines[-1] if lines else ""


# Each scan runs in its own RQ worker process, so several scans can run at
# once. They all share three things on the host:
#
#   1. The custom Nix Docker image.
#   2. The nixpkgs git repo and its worktrees.
#   3. The `nix-eval-cache` Docker volume (the Nix store).
#
# We use file locks (`fcntl.flock`) so only one process touches any of
# these at a time. The kernel drops the lock when the holder exits, even on
# a crash, so a dead worker can't leave a lock stuck. We don't want to set
# a timeout as the first nixpkgs clone can take minutes, and we don't want
# to treat a slow scan as a deadlock.
#
# The timestamp file is not a lock: it records when the Nix store GC
# (Garbage Collector) last ran, so GC runs at most once per interval
# instead of on every scan.
def _nixpkgs_cache_dir():
    """Return the nixpkgs cache directory resolved from scanpipe_settings."""
    return Path(scanpipe_settings.NIXPKGS_CACHE_DIR)


def _nixpkgs_bare_repo():
    """Return the path of the local bare nixpkgs repository."""
    return _nixpkgs_cache_dir() / "nixpkgs.git"


def _nixpkgs_repo_lock_path():
    """Return the lock file path for the nixpkgs bare repository."""
    return _nixpkgs_cache_dir() / "nixpkgs-repo.lock"


def _nixpkgs_gc_timestamp_path():
    """Return the timestamp file path for the last Nix store GC run."""
    return _nixpkgs_cache_dir() / "nixpkgs-gc.timestamp"


_NIXPKGS_CONTAINER_PATH = "/nixpkgs-local"
_NIXPKGS_WORKTREE_CACHE = {}


# `extract_nar_archive()` needs zstd and xz to decompress `.nar.zst` or
# `.nar.xz`. The stock `nixos/nix` image doesn't ship them, so the
# extraction step fetches them via `nix-shell -p` on every scan from
# `cache.nixos.org`. The Nix cache server throttles these repeated requests
# by slowing the response or returning 429/503 errors, causing the
# extraction to time out.
#
# To avoid that, we build a custom Nix image with zstd, xz, bzip2, and gzip
# installed.
#
# The Dockerfile also registers the image's base tooling (bash and the
# nix-* commands) as GC roots. Without this, `nix-collect-garbage` running
# against the shared `nix-eval-cache` volume would delete the image's own
# dependencies and leave `/bin/sh` pointing at a removed store path.
_NIX_IMAGE_CHANNEL = "nixos-26.05"
_NIX_DOCKER_BASE_IMAGE = "nixos/nix:2.35.3"

_NIX_IMAGE_DOCKERFILE = f"""\
FROM {_NIX_DOCKER_BASE_IMAGE}
RUN nix-channel --add https://nixos.org/channels/{_NIX_IMAGE_CHANNEL} nixpkgs \\
 && nix-channel --update \\
 && nix-env -iA nixpkgs.zstd nixpkgs.xz nixpkgs.bzip2 nixpkgs.gzip \\
 && GCROOTS=/nix/var/nix/gcroots/base \\
 && mkdir -p "$GCROOTS" \\
 && ln -sf "$(readlink -f /bin/sh)" "$GCROOTS/sh" \\
 && for tool in nix-build nix-store nix-env nix-instantiate nix-collect-garbage; do \\
      ln -sf "$(readlink -f "$(command -v $tool)")" "$GCROOTS/$tool"; \\
    done
"""

# Generate a unique image tag from a hash of the Dockerfile contents.
# This ensures that modifying the Dockerfile automatically changes the tag,
# forcing Docker to rebuild the image instead of reusing a stale cached version
_NIX_IMAGE_TAG = hashlib.sha256(_NIX_IMAGE_DOCKERFILE.encode()).hexdigest()[:8]
NIX_IMAGE = f"scancode-nix:{_NIX_IMAGE_TAG}"

_resolved_nix_image = None


def _ensure_nix_image():
    """
    Ensure the custom Nix image exists locally, building it if necessary.
    Return the image name to use for `docker run`.
    Uses a file lock to safely support concurrent calls.
    """
    global _resolved_nix_image
    if _resolved_nix_image is not None:
        return _resolved_nix_image

    if utils.docker_image_exists(NIX_IMAGE):
        _resolved_nix_image = NIX_IMAGE
        return _resolved_nix_image

    # Lock the file to avoid crashing during concurrent runs.
    with utils.file_lock(_nixpkgs_cache_dir() / "nix-image.lock"):
        # Another process may have built it while we waited for the lock.
        if utils.docker_image_exists(NIX_IMAGE):
            _resolved_nix_image = NIX_IMAGE
            return _resolved_nix_image

        logger.info(f"Custom Nix image '{NIX_IMAGE}' not found. Building it now.")

        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text(_NIX_IMAGE_DOCKERFILE)
            build_cmd = [
                "docker",
                "build",
                "-t",
                NIX_IMAGE,
                "-f",
                str(dockerfile_path),
                tmpdir,
            ]
            try:
                subprocess.run(  # noqa: S603
                    build_cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=_DOCKER_BUILD_TIMEOUT,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Failed to build {NIX_IMAGE}: {e.stderr.strip()}"
                ) from e
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"Timeout building {NIX_IMAGE} after {_DOCKER_BUILD_TIMEOUT}s."
                ) from e

    _resolved_nix_image = NIX_IMAGE
    return _resolved_nix_image


# The `nix-eval-cache` volume holds the Nix store, which caches the
# packages and dependencies that scans fetch and build. Its disk usage
# grows as more distinct packages are scanned. To keep it from growing
# forever, we periodically run:
#
#     nix-collect-garbage --delete-older-than <SCANCODEIO_NIXPKGS_GC_OLDER_THAN>
#
# inside the custom image, against the shared volume. This removes store
# paths that have not been read or written for the defined period.
#
# A timestamp file limits how often GC runs: at most once every
# `SCANCODEIO_NIXPKGS_GC_INTERVAL_HOURS` hours, and only for store paths
# older than `SCANCODEIO_NIXPKGS_GC_OLDER_THAN`. Defaults: 3 hours and
# 12 hours.
#
# The GC does NOT touch the custom Nix image. The image is built once and
# survives GC, host reboots, and even full volume deletion.
#
#   SCANCODEIO_NIXPKGS_GC_INTERVAL_HOURS — run GC at most this often. 0 disables.
#   SCANCODEIO_NIXPKGS_GC_OLDER_THAN     — passed to `--delete-older-than`.


def _gc_due(now):
    """Return True if GC has not run for at least the configured interval."""
    interval = scanpipe_settings.NIXPKGS_GC_INTERVAL_HOURS
    if interval <= 0:
        return False

    timestamp_path = _nixpkgs_gc_timestamp_path()
    if not timestamp_path.exists():
        return True
    try:
        last_run = float(timestamp_path.read_text().strip())
    except (ValueError, OSError):
        # Corrupt or unreadable timestamp; treat as "due".
        return True
    return (now - last_run) >= interval * 3600


def _run_nixpkgs_gc_if_due():
    """
    Run `nix-collect-garbage --delete-older-than
    <SCANCODEIO_NIXPKGS_GC_OLDER_THAN>` on the shared Nix store cache, but
    at most once per `SCANCODEIO_NIXPKGS_GC_INTERVAL_HOURS`.
    """
    now = time.time()
    if not _gc_due(now):
        return

    nix_image = _ensure_nix_image()

    with utils.file_lock(_nixpkgs_cache_dir() / "nixpkgs-gc.lock"):
        if not _gc_due(now):
            return

        older_than = scanpipe_settings.NIXPKGS_GC_OLDER_THAN
        logger.info(
            f"Running nix-collect-garbage --delete-older-than "
            f"{older_than} on the shared Nix store cache."
        )
        cmd = [
            "docker",
            "run",
            "--rm",
            "--init",
            "-v",
            "nix-eval-cache:/nix",
            nix_image,
            "nix-collect-garbage",
            "--delete-older-than",
            older_than,
        ]
        try:
            subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=_DOCKER_IO_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.warning("nix-collect-garbage timed out; skipping.")
            return

        try:
            _nixpkgs_gc_timestamp_path().write_text(str(now))
        except OSError as e:
            logger.debug(f"Could not write GC timestamp: {e}")


def binfmt_emulation_is_installed():
    """Return True if multi-arch binfmt handlers are registered on the host."""
    global _binfmt_emulation_is_installed_cache
    if _binfmt_emulation_is_installed_cache is not None:
        return _binfmt_emulation_is_installed_cache
    cmd = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--privileged",
        _BINFMT_CHECK_IMAGE,
    ]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        _binfmt_emulation_is_installed_cache = "qemu" in result.stdout
        return _binfmt_emulation_is_installed_cache
    except FileNotFoundError:
        logger.debug("docker CLI not found; cannot check binfmt emulation.")
    except subprocess.CalledProcessError as e:
        logger.debug(
            f"binfmt check container exited with {e.returncode}: {e.stderr.strip()}"
        )
    except subprocess.TimeoutExpired:
        logger.debug("binfmt check container timed out after 30s.")
    except subprocess.SubprocessError as e:
        logger.debug(f"binfmt check failed: {e}")
    _binfmt_emulation_is_installed_cache = False
    return _binfmt_emulation_is_installed_cache


def prepare_nix_environment():
    """
    Prepare the Nix runtime for a scan.
    Ensure the custom Nix image exists and run the periodic store GC.
    """
    _ensure_nix_image()
    _run_nixpkgs_gc_if_due()


# Nixpkgs is a huge repo, and evaluating a package needs the full tree at
# the exact commit referenced by the PURL. Without a local clone, every scan
# fetches a tarball from GitHub. At scale, GitHub rate-limits these requests
# and the pipeline stalls.
#
# So we keep one bare git clone of nixpkgs on the host. Each scan
# shallow fetches its commit, creates a temporary worktree, and bind-mounts
# it into the container read-only. The Nix expression imports from that path
# instead of `fetchTarball`, so no network access is needed inside the
# container.
def _clone_nixpkgs_bare_repo():
    """
    Clone the nixpkgs bare repo.
    Return the repo path, or "" on failure.
    """
    _nixpkgs_cache_dir().mkdir(parents=True, exist_ok=True)
    bare_repo = _nixpkgs_bare_repo()
    logger.info(f"First run: creating a local bare clone of nixpkgs at {bare_repo}.")

    cmd = [
        "git",
        "clone",
        "--bare",
        "--filter=blob:none",
        "--no-tags",
        scanpipe_settings.NIXPKGS_REPO_URL,
        str(bare_repo),
    ]
    try:
        subprocess.run(  # noqa: S603
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        return str(bare_repo)
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to create nixpkgs bare clone: {e.stderr.strip()}. "
            f"Falling back to fetchTarball."
        )
        shutil.rmtree(bare_repo, ignore_errors=True)
    except subprocess.TimeoutExpired:
        logger.error(
            "Timeout creating nixpkgs bare clone; falling back to fetchTarball."
        )
        shutil.rmtree(bare_repo, ignore_errors=True)
    return ""


def _ensure_nixpkgs_bare_repo():
    """Ensure a local bare clone of nixpkgs exists."""
    if not scanpipe_settings.NIXPKGS_USE_LOCAL_CACHE:
        return ""

    if not shutil.which("git"):
        logger.warning(
            "git is not available; falling back to fetchTarball for nixpkgs. "
            "Install git to enable the local cache and avoid GitHub rate limits."
        )
        return ""

    bare_repo = _nixpkgs_bare_repo()
    if bare_repo.exists():
        return str(bare_repo)

    with utils.file_lock(_nixpkgs_repo_lock_path()):
        # Re-check inside the lock: another process may have cloned while
        # we were waiting.
        if bare_repo.exists():
            return str(bare_repo)
        return _clone_nixpkgs_bare_repo()


def _prepare_nixpkgs_worktree(commit_hash):
    """
    Fetch `commit_hash` into the bare repo and create a worktree
    for it. Return the worktree's host path, or "" on failure.
    """
    bare_repo = _ensure_nixpkgs_bare_repo()
    if not bare_repo:
        return ""

    worktree_dir = _nixpkgs_cache_dir() / "worktrees"
    worktree_dir.mkdir(parents=True, exist_ok=True)
    worktree_path = worktree_dir / f"{commit_hash}-{uuid.uuid4().hex[:8]}"

    with utils.file_lock(_nixpkgs_repo_lock_path()):
        try:
            fetch_cmd = [
                "git",
                "-C",
                bare_repo,
                "fetch",
                "--depth",
                "1",
                "--no-tags",
                "origin",
                commit_hash,
            ]
            subprocess.run(  # noqa: S603
                fetch_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
            )
            worktree_cmd = [
                "git",
                "-C",
                bare_repo,
                "worktree",
                "add",
                "--detach",
                str(worktree_path),
                commit_hash,
            ]
            subprocess.run(  # noqa: S603
                worktree_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            return str(worktree_path)
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to prepare nixpkgs worktree for commit {commit_hash}: "
                f"{e.stderr.strip()}. Falling back to fetchTarball."
            )
            shutil.rmtree(worktree_path, ignore_errors=True)
        except subprocess.TimeoutExpired:
            logger.warning(
                f"Timeout preparing nixpkgs worktree for commit {commit_hash}; "
                f"falling back to fetchTarball."
            )
            shutil.rmtree(worktree_path, ignore_errors=True)
        return ""


def _get_nixpkgs_worktree(commit_hash):
    """
    Return a worktree path for `commit_hash`, cached per process. Fetched
    once, reused until `cleanup_worktrees` removes it.
    """
    if commit_hash in _NIXPKGS_WORKTREE_CACHE:
        return _NIXPKGS_WORKTREE_CACHE[commit_hash]

    worktree_path = _prepare_nixpkgs_worktree(commit_hash)
    if worktree_path:
        _NIXPKGS_WORKTREE_CACHE[commit_hash] = worktree_path
    return worktree_path


def _remove_nixpkgs_worktree(worktree_path):
    """Remove a worktree created by `_prepare_nixpkgs_worktree`."""
    if not worktree_path:
        return

    bare_repo = str(_nixpkgs_bare_repo())
    if not Path(bare_repo).exists():
        shutil.rmtree(worktree_path, ignore_errors=True)
        return

    with utils.file_lock(_nixpkgs_repo_lock_path()):
        try:
            cmd = [
                "git",
                "-C",
                bare_repo,
                "worktree",
                "remove",
                "--force",
                worktree_path,
            ]
            subprocess.run(  # noqa: S603
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # Remove the directory directly, then prune the now-stale metadata.
            shutil.rmtree(worktree_path, ignore_errors=True)
            try:
                prune_cmd = ["git", "-C", bare_repo, "worktree", "prune"]
                subprocess.run(  # noqa: S603
                    prune_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                logger.debug(f"Failed to prune git worktrees: {e}")


def cleanup_nixpkgs_worktrees():
    """
    Remove every nixpkgs worktree created during this process's lifetime
    and clear the in-process cache.
    """
    for path in list(_NIXPKGS_WORKTREE_CACHE.values()):
        _remove_nixpkgs_worktree(path)
    _NIXPKGS_WORKTREE_CACHE.clear()


def _nixpkgs_mount_args(worktree_path):
    """
    Return the `-v` arguments that mount a worktree into the
    container read-only, or `[]` if no worktree is available.
    """
    if not worktree_path:
        return []
    return ["-v", f"{worktree_path}:{_NIXPKGS_CONTAINER_PATH}:ro"]


def _nixpkgs_import_expr(commit_hash, worktree_path, system_config, config_str):
    """
    Build the Nix expression that imports nixpkgs at `commit_hash`.

    With a worktree mounted at `_NIXPKGS_CONTAINER_PATH`, the expression
    imports from there (no network). Otherwise it falls back to
    `fetchTarball` from GitHub, which might subject to rate-limiting.
    """
    config = f"{{ {system_config} {config_str} }}"
    if worktree_path:
        return f"import {_NIXPKGS_CONTAINER_PATH} {config}"
    return (
        f'import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/'
        f'{commit_hash}.tar.gz") {config}'
    )


def _build_nixpkgs_import(commit_hash, system, for_build=True):
    """
    Return the Nix expression that imports nixpkgs at the given commit.

    Use ``for_build=True`` when the expression will compile the package
    (cross-compilation flags are added), and ``for_build=False`` when it
    only needs to read metadata or resolve a store path.
    """
    if for_build:
        if _is_non_linux_system(system):
            system_config = ""
        else:
            system_config = (
                f'localSystem = builtins.currentSystem; crossSystem = "{system}";'
            )
        config_str = (
            "config = { "
            "allowBroken = true; "
            "allowUnfree = true; "
            "allowUnsupportedSystem = true; "
            "};"
        )
    else:
        system_config = f'system = "{system}";' if system else ""
        config_str = "config = { allowBroken = true; allowUnfree = true; };"

    worktree_path = _get_nixpkgs_worktree(commit_hash)
    return _nixpkgs_import_expr(commit_hash, worktree_path, system_config, config_str)


def _is_non_linux_system(system):
    """Return True if the target system is not a Linux variant."""
    target_os = system.split("-")[-1] if "-" in system else system
    return bool(target_os) and target_os != "linux"


def _system_barrier_message(system):
    """
    Return the warning about cross-system evaluation, or ""
    when the target system is Linux.
    """
    if not _is_non_linux_system(system):
        return ""
    return (
        f"Target system '{system}' requires OS-specific SDKs that cannot be "
        f"evaluated inside the Linux-based Nix Docker container. The source "
        f"tree was evaluated in the container's native Linux environment, so "
        f"it will contain Linux-specific patches instead of {system} patches. "
        f"Impact on deployment-to-development mapping is expected to be "
        f"minimal, but a small number of unmapped files may appear due to "
        f"missing OS-specific structural patches."
    )


def _github_api_headers():
    """Return GitHub API request headers, adding a token when configured."""
    headers = {"Accept": "application/vnd.github+json"}
    token = (
        scanpipe_settings.GITHUB_TOKEN
        or os.environ.get("GITHUB_TOKEN", "")
        or os.environ.get("GH_TOKEN", "")
    ).strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_api_is_unavailable(response):
    """
    Return True if the response indicates the GitHub API failed due to
    temporary unavailability or rate limits, rather than a genuinely
    missing resource.
    """
    return response.status_code in (403, 429) or response.status_code >= 500


def _commit_is_on_any_branch(commit_hash, headers, repo_url, branches):
    """
    Return True if `commit_hash` is reachable from at least one branch,
    False if reachable from none, None if the GitHub API failed.
    """
    for branch in branches:
        compare_url = f"{repo_url}/compare/{commit_hash}...{branch}"
        try:
            response = requests.get(compare_url, headers=headers, timeout=30)
        except requests.RequestException as e:
            logger.warning(f"Could not compare {commit_hash!r} to {branch}: {e}")
            return None

        if response.status_code == 404:
            continue

        if _github_api_is_unavailable(response):
            logger.warning(
                f"GitHub API unavailable while verifying {commit_hash!r} "
                f"(HTTP {response.status_code})."
            )
            return None

        try:
            response.raise_for_status()
            status = response.json().get("status")
        except (requests.HTTPError, ValueError) as e:
            logger.warning(f"Invalid response for {branch}: {e}")
            return None

        # `behind` and `identical` mean the branch is an ancestor of the
        # commit. `ahead` and `diverged` mean it is not.
        if status in ("behind", "identical"):
            return True

    return False


def verify_commit_in_nixpkgs(commit_hash):
    """
    Return True if ``commit_hash`` is reachable from an official nixpkgs
    branch (``master``, ``nixos-unstable``, or any ``release-*`` branch),
    False otherwise, and None if GitHub could not be queried.
    """
    if not COMMIT_RE.fullmatch(commit_hash):
        return False

    headers = _github_api_headers()
    repo_url = f"https://api.github.com/repos/{NIXPKGS_OWNER}/{NIXPKGS_REPO}"

    try:
        commit_response = requests.get(
            f"{repo_url}/commits/{commit_hash}", headers=headers, timeout=30
        )
        if commit_response.status_code == 404:
            return False
        if _github_api_is_unavailable(commit_response):
            logger.warning(
                f"GitHub API unavailable during initial check for "
                f"{commit_hash!r} (HTTP {commit_response.status_code})."
            )
            return None
        commit_response.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Could not perform existence check for {commit_hash!r}: {e}")
        return None

    try:
        release_branches = []
        url = f"{repo_url}/branches?per_page=100"

        while url:
            branches_response = requests.get(url, headers=headers, timeout=30)
            branches_response.raise_for_status()

            release_branches.extend(
                [
                    branch["name"]
                    for branch in branches_response.json()
                    if branch["name"].startswith("release-")
                ]
            )

            # Follow GitHub's 'Link' header to the next page, if it exists
            url = branches_response.links.get("next", {}).get("url")

        # Prioritize default/master
        branches = [NIXPKGS_DEFAULT_BRANCH, "master"] + release_branches
    except (requests.RequestException, ValueError, TypeError) as e:
        logger.warning(f"Could not list nixpkgs branches: {e}")
        return None

    return _commit_is_on_any_branch(commit_hash, headers, repo_url, branches)


def _validate_purl_qualifiers(purl):
    """Validate the PURL qualifiers and return the commit hash."""
    qualifiers = purl.qualifiers or {}

    if not purl.version and "commit" not in qualifiers:
        raise ValueError("Version or a 'commit' qualifier is required.")

    if "system" not in qualifiers:
        raise ValueError(
            "The 'system' qualifier is required to resolve system-specific binaries."
        )
    if not SYSTEM_RE.fullmatch(qualifiers["system"]):
        raise ValueError(f"Invalid system: {qualifiers['system']!r}")

    if "output" in qualifiers and not OUTPUT_RE.fullmatch(qualifiers["output"]):
        raise ValueError(f"Invalid output: {qualifiers['output']!r}")

    commit_hash = qualifiers.get("commit", "")
    if commit_hash and not COMMIT_RE.fullmatch(commit_hash):
        raise ValueError(f"Invalid commit hash: {commit_hash!r}")

    return commit_hash


def check_input_and_return_purl(project):
    """Validate the input and return a Nix PURL."""
    input_sources = project.inputsources.all()
    if len(input_sources) != 1:
        raise ValueError("Only 1 nix purl is accepted.")

    project_input = str(input_sources[0])
    input_purl = PackageURL.from_string(project_input)
    if input_purl.type != "nix":
        raise ValueError("Only nix purl is supported.")

    namespace = input_purl.namespace
    if not namespace or namespace.lower() != "nixpkgs":
        raise ValueError(
            "Only official nixpkgs repository is supported (i.e. namespace=nixpkgs)."
        )

    if not NIX_NAME_RE.fullmatch(input_purl.name):
        raise ValueError(f"Invalid Nix package name: {input_purl.name!r}")

    commit_hash = _validate_purl_qualifiers(input_purl)

    # Verify the commit exists in the official NixOS/nixpkgs history so that
    # a commit pointing to a fork cannot be used to inject arbitrary Nix code.
    if commit_hash:
        _require_official_commit(commit_hash, label="commit")
    return input_purl


def _validate_resolved_commit_hash(release_commit_hash, user_commit_hash):
    """
    Validate a commit hash resolved from external package metadata.

    Return the hash unchanged when it is empty or when it equals the
    user-supplied (already-verified) commit. Raise ValueError if it fails
    any check.
    """
    if not release_commit_hash or release_commit_hash == user_commit_hash:
        return release_commit_hash

    if not COMMIT_RE.fullmatch(release_commit_hash):
        raise ValueError(
            f"Invalid resolved commit hash from package metadata: "
            f"{release_commit_hash!r}"
        )
    _require_official_commit(release_commit_hash, label="resolved commit")
    return release_commit_hash


def _require_official_commit(commit_hash, label="commit"):
    """
    Raise ValueError unless `commit_hash` is on an official nixpkgs branch.

    `label` distinguishes error messages for the user-supplied commit
    ("commit") from the metadata-resolved one ("resolved commit").
    """
    is_official = verify_commit_in_nixpkgs(commit_hash)
    if is_official is None:
        raise ValueError(
            f"Could not verify that {label} {commit_hash!r} belongs to "
            f"the official NixOS/nixpkgs repository: the GitHub API "
            f"was unreachable or rate limited. Configure "
            f"SCANCODEIO_GITHUB_TOKEN (or GITHUB_TOKEN / GH_TOKEN) "
            f"to raise the limit, or retry later."
        )
    if not is_official:
        raise ValueError(
            f"The {label} {commit_hash!r} is not reachable from any "
            f"official NixOS/nixpkgs branch (master, "
            f"{NIXPKGS_DEFAULT_BRANCH}, or release-*)."
        )


def fetch_inputs(purl, output_dir):
    """
    Fetch the system specific binary and the exact source tree with the
    patches and configurations applied for the given input purl. Return a
    tuple of (source_path, binary_path, output_format,
    concluded_commit_hash, error_messages, warning_messages).
    """
    data = get_package_data(purl)
    name = purl.name
    version = purl.version

    commit_hash = purl.qualifiers.get("commit", "")
    system = purl.qualifiers.get("system", "")
    user_output = purl.qualifiers.get("output", "")
    error_messages = []
    warning_messages = []

    barrier_warning = _system_barrier_message(system)
    if barrier_warning:
        logger.warning(barrier_warning)
        warning_messages.append(barrier_warning)

    output_format, path, release_commit_hash = get_nix_store_path(
        data, name, version, system, commit_hash, user_output
    )

    release_commit_hash = _validate_resolved_commit_hash(
        release_commit_hash, commit_hash
    )
    concluded_commit_hash = release_commit_hash or commit_hash

    bin_path, bin_warning_msgs, bin_error_msgs = _fetch_or_build_binary(
        name, purl, output_dir, system, concluded_commit_hash, output_format, path
    )
    warning_messages.extend(bin_warning_msgs)
    error_messages.extend(bin_error_msgs)

    patched_source_path, source_warning_msgs, source_error_msgs = _fetch_patched_source(
        name, purl, output_dir, system, concluded_commit_hash
    )
    warning_messages.extend(source_warning_msgs)
    error_messages.extend(source_error_msgs)

    return (
        patched_source_path,
        bin_path,
        output_format,
        concluded_commit_hash,
        error_messages,
        warning_messages,
    )


def get_nix_package_metadata(purl, commit_hash):
    """
    Return a dict with ``license``, ``homepage``, and ``description``
    of nixpkgs metadata for the target package identified by ``purl``.
    """
    name = purl.name
    system = purl.qualifiers.get("system", "")

    if not name or not commit_hash:
        return {}

    worktree_path = _get_nixpkgs_worktree(commit_hash)
    nixpkgs_import = _build_nixpkgs_import(commit_hash, system, for_build=False)

    nix_expression = f"""
    {{ name }}:
    let
        pkgs = {nixpkgs_import};
        target = pkgs.lib.getAttrFromPath (pkgs.lib.splitString "." name) pkgs;
        meta = target.meta or {{}};
        license = meta.license or [];

        # Helper function to extract a license ID from one license item
        getLicenseId = licenseItem:
            if builtins.isAttrs licenseItem && licenseItem ? spdxId
            then licenseItem.spdxId
            else if builtins.isString licenseItem
            then licenseItem
            else null;

        licenseList = if builtins.isList license then license else [ license ];

        # Map the helper over the list, filter out nulls, and deduplicate
        validLicenseIds =
            pkgs.lib.unique (
                builtins.filter (extractedId: extractedId != null)
                (map getLicenseId licenseList)
            );

        # Declared licenses are combined with " AND "
        licenseId =
            if validLicenseIds != []
            then builtins.concatStringsSep " AND " validLicenseIds
            else null;
    in
    {{
        license = licenseId;
        homepage = meta.homepage or null;
        description = meta.description or null;
    }}
    """

    container_name = f"nix-meta-{uuid.uuid4().hex[:12]}"
    nix_image = _ensure_nix_image()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        container_name,
        "-v",
        "nix-eval-cache:/nix",
        *_nixpkgs_mount_args(worktree_path),
        nix_image,
        "nix-instantiate",
        "--eval",
        "--strict",
        "--json",
        "--argstr",
        "name",
        name,
        "-E",
        nix_expression,
    ]

    task_description = f"Evaluating metadata for {name}"
    try:
        result = utils.run_docker_container(
            cmd, container_name, _DOCKER_EVAL_TIMEOUT, task_description
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error evaluating metadata for '{name}': {e.stderr}")
        return {}
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout evaluating metadata for '{name}'")
        return {}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning(f"Could not parse metadata JSON for '{name}': {result.stdout!r}")
        return {}


def create_package_from_nix_metadata(project, purl, metadata):
    """
    Create a DiscoveredPackage for the Nix package using the declared
    license found in nixpkgs ``meta.license``.
    """
    spdx_id = (metadata.get("license") or "").strip()
    declared_expression = ""
    if spdx_id:
        try:
            declared_expression = convert_spdx_expression(spdx_id)
        except Exception as e:
            logger.warning(
                f"Could not convert SPDX id {spdx_id!r} to a ScanCode "
                f"license expression: {e}"
            )
            declared_expression = spdx_id

    homepage = metadata.get("homepage") or ""
    if isinstance(homepage, list):
        homepage = homepage[0] if homepage else ""

    package_data = {
        "type": "nix",
        "name": purl.name,
        "version": purl.version or "",
        "namespace": purl.namespace,
        "declared_license_expression": declared_expression,
        "declared_license_expression_spdx": spdx_id,
        "homepage_url": homepage,
        "description": metadata.get("description") or "",
        "datasource_id": "nixpkgs_meta",
    }
    return pipes.update_or_create_package(project, package_data)


def _fetch_or_build_binary(
    name, purl, output_dir, system, concluded_commit_hash, output_format, path
):
    """Fetch the binary from cache or build it locally and return its path."""
    nix_bin_download_url = get_nix_download_url(path) if path else ""
    bin_path = ""
    warning_messages = []
    error_messages = []

    if nix_bin_download_url:
        try:
            bin_path = fetch.fetch_url(nix_bin_download_url).path
        except (ValueError, requests.RequestException) as e:
            logger.warning(f"Failed to fetch package: {nix_bin_download_url} - {e}")

    if bin_path:
        logger.info(f"Downloaded binary for {purl} to {bin_path}")
        return bin_path, warning_messages, error_messages

    if concluded_commit_hash:
        logger.info(
            f"Binary not found in cache for {purl}. Attempting local Nix build..."
        )
        bin_path, error_message = build_binary_with_docker(
            name, output_dir, system, concluded_commit_hash, output_format
        )
        if error_message:
            error_messages.append(error_message)
    if bin_path:
        logger.info(f"Successfully built binary for {purl} to {bin_path}")
        warning_messages.append(
            f"Binary not found in cache for {purl}. Built locally using "
            f"commit {concluded_commit_hash} with a Linux-based Nix "
            f"Docker container."
        )
    else:
        error_message = f"Failed to fetch or build the binary for {purl}"
        logger.error(error_message)
        error_messages.append(error_message)

    return bin_path, warning_messages, error_messages


def _fetch_patched_source(name, purl, output_dir, system, concluded_commit_hash):
    """Fetch the patched source tree. Return its path, or empty on failure."""
    warning_messages = []
    error_messages = []

    if not concluded_commit_hash:
        return "", warning_messages, error_messages

    source_result = get_patched_source_with_docker(
        name, output_dir, system, concluded_commit_hash
    )

    if not source_result.path:
        detail = (
            f" Reason: {source_result.failure_detail}"
            if source_result.failure_detail
            else ""
        )
        source_error = (
            f"Failed to fetch the patched source for {purl} "
            f"(commit={concluded_commit_hash}, system={system}).{detail} "
            f"D2D scan will be disabled."
        )
        logger.error(source_error)
        error_messages.append(source_error)

    if source_result.used_fallback:
        detail = (
            f" Reason: {source_result.fallback_reason}."
            if source_result.fallback_reason
            else ""
        )
        fallback_warning = (
            f"The patched source build for {name} failed; D2D will run "
            f"against the raw upstream source (pkg.src) without nixpkgs "
            f"patches.{detail} Mismatches between the source and binary "
            f"trees may include files that were only added or modified by "
            f"patches."
        )
        logger.warning(fallback_warning)
        warning_messages.append(fallback_warning)

    return source_result.path, warning_messages, error_messages


def build_binary_with_docker(name, output_dir, system, commit_hash, output_format):
    """
    Fetch a Nix package and build its binary from source using Docker.
    Exports the resulting store path as a .nar file for standard extraction.

    Return a tuple of (path, error_msg), where `path` is the path to the
    exported `.nar` file or an empty string on failure.
    """
    nar_filename = f"{name}-bin.nar"
    extracted_path = Path(output_dir) / nar_filename
    absolute_out_dir = str(Path(output_dir).resolve())
    error_msg = ""

    nixpkgs_import = _build_nixpkgs_import(commit_hash, system)

    # Defaulting to 'debug' if none is specified.
    effective_output = output_format or "debug"

    # Fall back to the default target if the effective_output is not
    # defined in the recipe for this package.
    nix_expression = (
        "{ name, output }: "
        "let "
        f"  pkgs = {nixpkgs_import}; "
        '  target = pkgs.lib.getAttrFromPath (pkgs.lib.splitString "." name) pkgs; '
        "  hasIt = builtins.isAttrs target && builtins.hasAttr output target; "
        f"in if hasIt then target.${{output}} else target"
    )

    # Build the Nix package, verify it succeeded, and export the output as
    # a .nar file. `shlex.quote` makes the values shell-safe on the command
    # line.
    container_script = f"""
    OUT_PATH=$(nix-build --no-out-link \\
      --argstr name {shlex.quote(name)} \\
      --argstr output {shlex.quote(effective_output)} \\
      -E '{nix_expression}')
    if [ -z "$OUT_PATH" ] || [ ! -e "$OUT_PATH" ]; then
        echo "Error: nix-build failed to return a valid store path." >&2
        exit 1
    fi
    nix-store --dump "$OUT_PATH" > /build_output/{shlex.quote(nar_filename)}
    """

    container_name = f"nix-bin-build-{uuid.uuid4().hex[:12]}"
    nix_image = _ensure_nix_image()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        container_name,
        "-v",
        "nix-eval-cache:/nix",
        *_nixpkgs_mount_args(_get_nixpkgs_worktree(commit_hash)),
        "-v",
        f"{absolute_out_dir}:/build_output",
        nix_image,
        "/bin/sh",
        "-c",
        container_script,
    ]

    task_description = f"Building ({name} for {system})"

    try:
        utils.run_docker_container(
            cmd, container_name, _DOCKER_BUILD_TIMEOUT, task_description
        )
        if extracted_path.exists():
            return str(extracted_path), ""
        error_msg = f"Failed: {task_description} did not produce {nar_filename}"
        logger.error(error_msg)
    except subprocess.CalledProcessError as e:
        summary = _summarize_nix_build_error(e.stderr)
        error_msg = f"Failed: {task_description}: {summary}"
        logger.error(error_msg)
    except subprocess.TimeoutExpired:
        error_msg = f"Failed: {task_description} with error: Process timed out"
        logger.error(error_msg)
    return "", error_msg


def get_nix_store_path(data, name, version, system, commit_hash, user_output):
    """Get the Nix store path and release commit hash."""
    outputs_to_try = [user_output] if user_output else ["debug", "out"]
    path = ""
    release_commit_hash = ""
    output_format = ""

    for output in outputs_to_try:
        if data:
            release_commit_hash, path = get_commit_hash_nix_store_path(
                data, system, output, version, commit_hash
            )

        if not data or not path:
            if commit_hash:
                path = get_nix_store_path_with_nix(name, system, output, commit_hash)

        if path:
            output_format = output
            break

    if not path:
        if not commit_hash:
            raise ValueError(
                "Please provide a 'commit' qualifier in the PURL "
                "for Nix to determine the download URL or build it locally."
            )
        output_format = user_output or "debug"

    return output_format, path, release_commit_hash


def get_commit_hash_nix_store_path(data, system, output, version, commit_hash=""):
    """
    Find and return the commit_hash and store path (/nix/store/<path>)
    based on the qualifiers.
    """
    releases = data.get("releases") or []
    releases = [release for release in releases if release.get("version") == version]
    for release in releases:
        for platform in release.get("platforms", []):
            release_commit_hash = platform.get("commit_hash", "")
            if platform.get("system") != system:
                continue
            if commit_hash and release_commit_hash != commit_hash:
                continue
            for out in platform.get("outputs", []):
                out_path = out.get("path")
                if out.get("name") == output and out_path:
                    return release_commit_hash, out_path
    return "", ""


def get_package_data(purl):
    """Fetch package data from https://search.devbox.sh/."""
    api_url = f"https://search.devbox.sh/v2/pkg?{urlencode({'name': purl.name})}"
    try:
        return fetch_json_response(api_url)
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.warning(f"Failed to fetch package data for {purl}: {e}")
        return None


def get_nix_store_path_with_nix(name, system, output, commit_hash):
    """Find and return the store path using `nix`."""
    worktree_path = _get_nixpkgs_worktree(commit_hash)
    nixpkgs_import = _build_nixpkgs_import(commit_hash, system, for_build=False)

    nix_expression = (
        "{ name, output }: "
        "let "
        f"  pkgs = {nixpkgs_import}; "
        '  target = pkgs.lib.getAttrFromPath (pkgs.lib.splitString "." name) pkgs; '
        "  hasIt = builtins.isAttrs target && builtins.hasAttr output target; "
        f'in if hasIt then target.${{output}}.outPath else ""'
    )

    container_name = f"nix-eval-{uuid.uuid4().hex[:12]}"
    nix_image = _ensure_nix_image()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        container_name,
        "-v",
        "nix-eval-cache:/nix",
        *_nixpkgs_mount_args(worktree_path),
        nix_image,
        "nix-instantiate",
        "--eval",
        "--raw",
        "--argstr",
        "name",
        name,
        "--argstr",
        "output",
        output,
        "-E",
        nix_expression,
    ]

    task_description = f"Evaluating store path for {name} ({output})"

    try:
        result = utils.run_docker_container(
            cmd, container_name, _DOCKER_EVAL_TIMEOUT, task_description
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error evaluating attribute for package '{name}': {e.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout evaluating attribute for package '{name}'")
    return ""


def get_nix_download_url(path):
    """Construct a download URL from cache.nixos.org based on store path."""
    base_name = path.rstrip("/").split("/")[-1]
    narinfo_hash = base_name.split("-")[0]

    narinfo_url = f"https://cache.nixos.org/{narinfo_hash}.narinfo"
    url_path = get_narinfo_url(narinfo_url)

    if not url_path:
        logger.warning(f"{narinfo_url} is not accessible.")
        return ""

    return f"https://cache.nixos.org/{url_path}"


def get_narinfo_url(narinfo_url, retries=3, timeout=10):
    """
    Visit the narinfo url and return the URL value, retrying on transient
    failures.

    "cache.nixos.org" and its CDN occasionally return 429, 503, or a
    network error for a single request. A failed lookup forces the caller
    into a local Nix build, which is much slower and, for non-Linux
    targets, may fail on a system barrier. Retrying with backoff recovers
    from these transient failures at low cost.
    """
    last_error = ""
    for attempt in range(retries):
        try:
            response = requests.get(narinfo_url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            if attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            logger.debug(f"{narinfo_url}: {last_error} after {retries} attempts")
            return ""

        if response.status_code == 200:
            for line in response.text.splitlines():
                if line.startswith("URL:"):
                    return line.split(":", 1)[1].strip()
            return ""

        # Retrying will not help with these permanent errors
        if response.status_code in (400, 403, 404):
            logger.debug(f"{narinfo_url}: HTTP {response.status_code}, not retrying")
            return ""

        # Retry with backoff
        last_error = f"HTTP {response.status_code}"
        if attempt < retries - 1:
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                delay = min(int(retry_after), 30)
            else:
                delay = 2**attempt
            time.sleep(delay)
            continue

    logger.debug(f"{narinfo_url}: {last_error} after {retries} attempts")
    return ""


def _stage_archive(archive_path, output_dir):
    """
    Ensure the archive lives inside output_dir so it is visible to the
    Docker daemon that resolves the `-v` mount source.

    Return (staged_path, staged). `staged` is True when a new copy was
    created inside `output_dir`, False when the archive was already there.
    """
    target = output_dir / archive_path.name
    staged = False
    if archive_path == target:
        return target, staged

    is_present = (
        target.exists() and target.stat().st_size == archive_path.stat().st_size
    )
    if not is_present:
        shutil.copy2(archive_path, target)
        staged = True
    return target, staged


def _decompress_pipeline_for(archive_name):
    """
    Return the shell pipeline that decompresses `archive_name` to stdout.

    The custom Nix image has zstd, xz, bzip2, and gzip on `$PATH`, so
    the pipeline is a direct call to the appropriate decompressor. No
    `nix-shell -p <tool>` is involved, so no fetch from
    "cache.nixos.org" happens at extraction time.
    """
    # `shlex.quote` makes the archive path safe to use in a shell command on
    # its own. The filename comes from the remote cache's `narinfo`, so no
    # local pattern constrains it.
    safe_path = shlex.quote(f"/input/{archive_name}")
    if archive_name.endswith(".zst"):
        return f"zstdcat {safe_path}"
    if archive_name.endswith(".xz"):
        return f"xzcat {safe_path}"
    if archive_name.endswith(".bz2"):
        return f"bzcat {safe_path}"
    if archive_name.endswith(".gz"):
        return f"zcat {safe_path}"
    return f"cat {safe_path}"


def extract_nar_archive(archive_path, output_dir, output):
    """Extract a compressed Nix NAR archive."""
    if not OUTPUT_RE.fullmatch(output):
        raise ValueError(f"Invalid output: {output!r}")

    archive_path = Path(archive_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Docker mounts are resolved by the daemon, not the client. To make the
    # archive visible to the daemon that runs the container, it must live
    # in `output_dir` — the one path this project shares with that daemon.
    archive_path, staged = _stage_archive(archive_path, output_dir)

    archive_dir = str(archive_path.parent)
    archive_name = archive_path.name
    extracted_path = output_dir / "to" / output

    # `shlex.quote` makes the output name safe to use in a shell command on
    # its own. `OUTPUT_RE` already guarantees this, but quoting keeps the line
    # safe even if the pattern changes later.
    safe_output = shlex.quote(output)

    decompress_cmd = _decompress_pipeline_for(archive_name)
    restore_pipeline = (
        f"{decompress_cmd} | nix-store --restore /output/to/{safe_output}"
    )

    # nix-store --restore runs as root inside the container and preserves the
    # NAR's ownership metadata, so the extracted tree ends up owned by root.
    # Chown it back to the calling user so ScanCode can extract nested archives,
    # read the files, and clean up afterwards.
    host_uid = os.getuid()
    host_gid = os.getgid()

    container_script = (
        f"rm -rf /output/to/{safe_output} "
        f"&& mkdir -p /output/to "
        f"&& {restore_pipeline} "
        f"&& chown -R {host_uid}:{host_gid} /output/to "
        f"&& chmod -R u+w /output/to"
    )

    container_name = f"nix-nar-extract-{uuid.uuid4().hex[:12]}"
    nix_image = _ensure_nix_image()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        container_name,
        "-v",
        f"{archive_dir}:/input:ro",
        "-v",
        f"{output_dir}:/output",
        nix_image,
        "/bin/sh",
        "-c",
        container_script,
    ]

    task_description = f"Extracting {archive_name}"

    try:
        utils.run_docker_container(
            cmd, container_name, _DOCKER_IO_TIMEOUT, task_description
        )
        return str(extracted_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract {archive_name} with error: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error(f"Failed to extract {archive_name}: Process timed out")
    finally:
        if staged:
            try:
                archive_path.unlink(missing_ok=True)
            except OSError as e:
                logger.debug(f"Could not remove staged archive {archive_path}: {e}")
    return ""


def extract_nar_archive_to_codebase(archive_path, codebase_path, output_format):
    """
    Extract the NAR archive into the project's codebase/ directory.

    Return a tuple ``(success, error_message)``. When the extraction
    produces no files, the empty ``to/`` directory is removed and
    ``success=False`` is returned.
    """
    extracted_path = extract_nar_archive(archive_path, codebase_path, output_format)

    to_dir = Path(codebase_path) / "to"
    is_empty = to_dir.exists() and not list(to_dir.rglob("*"))

    if not extracted_path or is_empty:
        if to_dir.exists():
            shutil.rmtree(to_dir)
        return False, "Failed to extract NAR archive, D2D scan disabled."

    return True, ""


def get_patched_source_with_docker(name, output_dir, system, commit_hash):
    """
    Fetch a Nix package source and apply its official patches, falling back
    to raw archives if package source cannot be built.
    """
    extracted_path = Path(output_dir) / "from"
    extracted_path.mkdir(parents=True, exist_ok=True)
    absolute_out_dir = str(extracted_path.resolve())

    host_uid = os.getuid()
    host_gid = os.getgid()

    nixpkgs_import = _build_nixpkgs_import(commit_hash, system)

    # `applyPatches` unpacks `pkg.src`, applies `pkg.patches`, and copies
    # the resulting tree to `$out`.
    nix_expression = f"""
    {{ name }}:
    let
        pkgs = {nixpkgs_import};
        pkg = pkgs.lib.getAttrFromPath (pkgs.lib.splitString "." name) pkgs;
    in
    if !(pkg ? src) then pkg
    else pkgs.applyPatches {{
        name = "${{name}}-patched-src";
        src = pkg.src;
        patches = pkg.patches or [];
        prePatch = pkg.prePatch or "";
        postPatch = pkg.postPatch or "";
    }}"""

    fallback_expression = f"""
    {{ name }}:
    let
        pkgs = {nixpkgs_import};
        pkg = pkgs.lib.getAttrFromPath (pkgs.lib.splitString "." name) pkgs;
    in
        if pkg ? gemFile then pkg.gemFile
        else if pkg ? src then pkg.src
        else pkg
    """

    # A quoted heredoc ("<< 'DELIM'") passes its body literally, with no
    # shell expansion. That keeps the multi-line Nix expression intact and
    # means any shell-looking text in it is treated as data. The delimiter
    # is random so the expression cannot contain a line matching it and
    # end the heredoc early.
    heredoc_delimiter = f"SCANCODE_NIX_{uuid.uuid4().hex[:16]}"

    # This bash script must NOT be indented in Python.
    # If the closing heredoc line has spaces before it, bash will fail to
    # parse it. The following script first attempts a standard patched
    # build; if that fails (or yields no files), it falls back to fetching
    # the raw source archive. The result is copied to the mounted `from/`
    # directory with correct ownership so the host can extract and process
    # it. `shlex.quote` keeps the value shell-safe; `--argstr` passes it
    # as Nix data, never code.
    container_script = f"""
set -e

cat << '{heredoc_delimiter}' > /tmp/expr.nix
{nix_expression}
{heredoc_delimiter}

cat << '{heredoc_delimiter}' > /tmp/fallback.nix
{fallback_expression}
{heredoc_delimiter}

# Try standard patched build
OUT_PATH=$(nix-build --no-out-link --argstr name {shlex.quote(name)} \
    /tmp/expr.nix || true)

VALID_FILES=0
if [ -n "$OUT_PATH" ] && [ -d "$OUT_PATH" ]; then
    VALID_FILES=$(ls -A1 "$OUT_PATH" 2>/dev/null | grep -v "^env-vars$" | wc -l)
fi

if [ -z "$OUT_PATH" ]; then
    FALLBACK_REASON="primary nix-build returned no store path"
elif [ ! -d "$OUT_PATH" ]; then
    FALLBACK_REASON="primary store path is not a directory"
elif [ "$VALID_FILES" -eq 0 ]; then
    FALLBACK_REASON="primary output contained only env-vars"
fi

if [ -n "$FALLBACK_REASON" ]; then
    echo "PATCHED_SOURCE_FALLBACK_REASON=$FALLBACK_REASON" >&2
    OUT_PATH=$(nix-build --no-out-link --argstr name {shlex.quote(name)} \
        /tmp/fallback.nix || true)
fi

if [ -z "$OUT_PATH" ] || [ ! -e "$OUT_PATH" ]; then
    echo "Error: nix-build failed to return a valid store path." >&2
    rm -f /tmp/expr.nix /tmp/fallback.nix
    exit 1
fi

if [ -d "$OUT_PATH" ]; then
    cp -a "$OUT_PATH/." /build_output/
else
    cp -L "$OUT_PATH" /build_output/
fi

chown -R $HOST_UID:$HOST_GID /build_output/
chmod -R u+w /build_output/

rm -f /tmp/expr.nix /tmp/fallback.nix
"""

    container_name = f"nix-patched-src-{uuid.uuid4().hex[:12]}"
    nix_image = _ensure_nix_image()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        container_name,
        "-e",
        f"HOST_UID={host_uid}",
        "-e",
        f"HOST_GID={host_gid}",
        "-v",
        "nix-eval-cache:/nix",
        *_nixpkgs_mount_args(_get_nixpkgs_worktree(commit_hash)),
        "-v",
        f"{absolute_out_dir}:/build_output",
        nix_image,
        "/bin/sh",
        "-c",
        container_script,
    ]

    task_description = f"Fetching patched source for {name} ({system})"

    failure_detail = ""
    try:
        result = utils.run_docker_container(
            cmd, container_name, _DOCKER_BUILD_TIMEOUT, task_description
        )
        if any(extracted_path.iterdir()):
            used_fallback = False
            fallback_reason = ""
            for line in result.stderr.splitlines():
                if line.startswith(FALLBACK_REASON_PREFIX):
                    used_fallback = True
                    fallback_reason = line[len(FALLBACK_REASON_PREFIX) :].strip()
                    break
            if used_fallback:
                logger.warning(
                    f"Primary patched-source build failed for {name}: {fallback_reason}"
                )
            return PatchedSourceResult(
                path=str(extracted_path),
                used_fallback=used_fallback,
                fallback_reason=fallback_reason,
                failure_detail="",
            )
        failure_detail = "Container produced no output"
        logger.warning(
            f"Patched-source extraction produced no files for {name} "
            f"(system={system}, commit={commit_hash})."
        )
    except subprocess.CalledProcessError as e:
        failure_detail = _summarize_nix_build_error(e.stderr) or "docker run failed"
        logger.error(f"Failed: {failure_detail}")
    except subprocess.TimeoutExpired:
        failure_detail = "Container timed out"
        logger.error(failure_detail)

    shutil.rmtree(extracted_path, ignore_errors=True)
    return PatchedSourceResult(
        path="",
        used_fallback=False,
        fallback_reason="",
        failure_detail=failure_detail,
    )

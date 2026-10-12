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

import atexit
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from collections import namedtuple
from pathlib import Path

import requests
from fetchcode import fetch_json_response
from packageurl import PackageURL

from scanpipe.pipes import utils

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


# Markers to identify meaningful failure lines in `nix-build` stderr.
_NIX_ERROR_MARKERS = (
    "Encountered missing or private dependencies:",
    "error: Cannot build",
    "error: builder failed",
)


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
_NIXPKGS_CACHE_DIR = Path(
    os.environ.get(
        "SCANCODE_NIXPKGS_CACHE_DIR",
        str(Path(os.path.expanduser("~")) / ".cache" / "scancode-nix"),
    )
)
_NIXPKGS_BARE_REPO = _NIXPKGS_CACHE_DIR / "nixpkgs.git"
_NIXPKGS_REPO_URL = os.environ.get(
    "SCANCODE_NIXPKGS_REPO_URL",
    "https://github.com/NixOS/nixpkgs.git",
)
_NIXPKGS_CONTAINER_PATH = "/nixpkgs-local"
_NIXPKGS_WORKTREE_CACHE = {}

_NIX_IMAGE_LOCK_PATH = _NIXPKGS_CACHE_DIR / "nix-image.lock"
_NIXPKGS_REPO_LOCK_PATH = _NIXPKGS_CACHE_DIR / "nixpkgs-repo.lock"
_NIX_GC_LOCK_PATH = _NIXPKGS_CACHE_DIR / "nix-gc.lock"
_NIX_GC_TIMESTAMP_PATH = _NIXPKGS_CACHE_DIR / "nix-gc.timestamp"


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
_NIX_IMAGE_DOCKERFILE = """\
FROM nixos/nix
RUN nix-channel --add https://nixos.org/channels/nixos-24.05 nixpkgs \\
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
    with utils.file_lock(_NIX_IMAGE_LOCK_PATH):
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
#     nix-collect-garbage --delete-older-than <SCANCODE_NIX_GC_OLDER_THAN>
#
# inside the custom image, against the shared volume. This removes store
# paths that have not been read or written for the defined period.
#
# A timestamp file limits how often GC runs: at most once every
# `SCANCODE_NIX_GC_INTERVAL_HOURS` hours, and only for store paths older
# than `SCANCODE_NIX_GC_OLDER_THAN`. Defaults: 3 hours and 12 hours.
#
# The GC does NOT touch the custom Nix image. The image is built once and
# survives GC, host reboots, and even full volume deletion.
#
#   SCANCODE_NIX_GC_INTERVAL_HOURS — run GC at most this often. 0 disables.
#   SCANCODE_NIX_GC_OLDER_THAN     — passed to `--delete-older-than`.

_NIX_GC_INTERVAL_HOURS = int(os.environ.get("SCANCODE_NIX_GC_INTERVAL_HOURS", "3"))
_NIX_GC_OLDER_THAN = os.environ.get("SCANCODE_NIX_GC_OLDER_THAN", "12h")


def _gc_due(now):
    """Return True if GC has not run for at least the configured interval."""
    if not _NIX_GC_TIMESTAMP_PATH.exists():
        return True
    try:
        last_run = float(_NIX_GC_TIMESTAMP_PATH.read_text().strip())
    except (ValueError, OSError):
        # Corrupt or unreadable timestamp; treat as "due".
        return True
    return (now - last_run) >= _NIX_GC_INTERVAL_HOURS * 3600


def _run_nix_gc_if_due():
    """
    Run `nix-collect-garbage --delete-older-than
    <SCANCODE_NIX_GC_OLDER_THAN>` on the shared Nix store cache, but at
    most once per `SCANCODE_NIX_GC_INTERVAL_HOURS`.
    """
    if _NIX_GC_INTERVAL_HOURS <= 0:
        return

    now = time.time()
    if not _gc_due(now):
        return

    nix_image = _ensure_nix_image()

    with utils.file_lock(_NIX_GC_LOCK_PATH):
        if not _gc_due(now):
            return

        logger.info(
            f"Running nix-collect-garbage --delete-older-than "
            f"{_NIX_GC_OLDER_THAN} on the shared Nix store cache."
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
            _NIX_GC_OLDER_THAN,
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
            _NIX_GC_TIMESTAMP_PATH.write_text(str(now))
        except OSError as e:
            logger.debug(f"Could not write GC timestamp: {e}")


def prepare_nix_environment():
    """Ensure the custom Nix image exists and run the periodic store GC."""
    _ensure_nix_image()
    _run_nix_gc_if_due()


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
    _NIXPKGS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(
        f"First run: creating a local bare clone of nixpkgs at {_NIXPKGS_BARE_REPO}."
    )

    cmd = [
        "git",
        "clone",
        "--bare",
        "--filter=blob:none",
        "--no-tags",
        _NIXPKGS_REPO_URL,
        str(_NIXPKGS_BARE_REPO),
    ]
    try:
        subprocess.run(  # noqa: S603
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        return str(_NIXPKGS_BARE_REPO)
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to create nixpkgs bare clone: {e.stderr.strip()}. "
            f"Falling back to fetchTarball."
        )
        shutil.rmtree(_NIXPKGS_BARE_REPO, ignore_errors=True)
    except subprocess.TimeoutExpired:
        logger.error(
            "Timeout creating nixpkgs bare clone; falling back to fetchTarball."
        )
        shutil.rmtree(_NIXPKGS_BARE_REPO, ignore_errors=True)
    return ""


def _ensure_nixpkgs_bare_repo():
    """Ensure a local bare clone of nixpkgs exists."""
    if os.environ.get("SCANCODE_NIXPKGS_USE_LOCAL_CACHE", "1") == "0":
        return ""

    if not shutil.which("git"):
        logger.warning(
            "git is not available; falling back to fetchTarball for nixpkgs. "
            "Install git to enable the local cache and avoid GitHub rate limits."
        )
        return ""

    if _NIXPKGS_BARE_REPO.exists():
        return str(_NIXPKGS_BARE_REPO)

    with utils.file_lock(_NIXPKGS_REPO_LOCK_PATH):
        # Re-check inside the lock: another process may have cloned while
        # we were waiting.
        if _NIXPKGS_BARE_REPO.exists():
            return str(_NIXPKGS_BARE_REPO)
        return _clone_nixpkgs_bare_repo()


def _prepare_nixpkgs_worktree(commit_hash):
    """
    Fetch `commit_hash` into the bare repo and create a worktree
    for it. Return the worktree's host path, or "" on failure.
    """
    bare_repo = _ensure_nixpkgs_bare_repo()
    if not bare_repo:
        return ""

    worktree_dir = _NIXPKGS_CACHE_DIR / "worktrees"
    worktree_dir.mkdir(parents=True, exist_ok=True)
    worktree_path = worktree_dir / f"{commit_hash}-{uuid.uuid4().hex[:8]}"

    with utils.file_lock(_NIXPKGS_REPO_LOCK_PATH):
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

    bare_repo = str(_NIXPKGS_BARE_REPO)
    if not Path(bare_repo).exists():
        shutil.rmtree(worktree_path, ignore_errors=True)
        return

    with utils.file_lock(_NIXPKGS_REPO_LOCK_PATH):
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


atexit.register(cleanup_nixpkgs_worktrees)


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


def check_input_and_return_purl(project):
    """Validate the input and return a Nix PURL."""
    input_sources = project.inputsources.all()
    if len(input_sources) != 1:
        error_msg = "Only 1 nix purl is accepted."
        raise ValueError(error_msg)

    project_input = str(input_sources[0])
    input_purl = PackageURL.from_string(project_input)
    if input_purl.type != "nix":
        error_msg = "Only nix purl is supported."
        raise ValueError(error_msg)

    namespace = input_purl.namespace
    if not namespace or namespace.lower() != "nixpkgs":
        raise ValueError(
            "Only official nixpkgs repository is supported (i.e. namespace=nixpkgs)."
        )

    qualifiers = input_purl.qualifiers or {}
    if not input_purl.version and "commit" not in qualifiers:
        raise ValueError("Version or a 'commit' qualifier is required.")

    if "system" not in qualifiers:
        raise ValueError(
            "The 'system' qualifier is required to resolve system-specific binaries."
        )

    return input_purl


def fetch_inputs(purl, output_dir):
    """
    Fetch the system specific binary and the exact source tree with the
    patches and configurations applied for the given input purl. Return a
    tuple of (source_path, binary_path, output_format, error_messages,
    warning_messages).
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

    concluded_commit_hash = release_commit_hash or commit_hash

    bin_path = ""
    nix_bin_download_url = get_nix_download_url(path) if path else ""
    if nix_bin_download_url:
        bin_path = utils.fetch_path(nix_bin_download_url)

    if bin_path:
        logger.info(f"Downloaded binary for {purl} to {bin_path}")
    else:
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
            warning_message = (
                f"Binary not found in cache for {purl}. Built locally using "
                f"commit {concluded_commit_hash} with a Linux-based Nix "
                f"Docker container."
            )
            logger.warning(warning_message)
            warning_messages.append(warning_message)
        else:
            error_message = f"Failed to fetch or build the binary for {purl}"
            logger.error(error_message)
            error_messages.append(error_message)

    patched_source_path = ""
    if concluded_commit_hash:
        source_result = get_patched_source_with_docker(
            name, output_dir, system, concluded_commit_hash
        )
        patched_source_path = source_result.path

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

    return (
        patched_source_path,
        bin_path,
        output_format,
        error_messages,
        warning_messages,
    )


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

    # Handle architecture and system incompatibilities.
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

    worktree_path = _get_nixpkgs_worktree(commit_hash)
    nixpkgs_import = _nixpkgs_import_expr(
        commit_hash, worktree_path, system_config, config_str
    )

    # Defaulting to 'debug' if none is specified.
    effective_output = output_format or "debug"

    # Fall back to the default target if the effective_output is not
    # defined in the recipe for this package.
    nix_expression = (
        f"let "
        f"  pkgs = {nixpkgs_import}; "
        f"  target = pkgs.{name}; "
        f"  hasIt = builtins.isAttrs target && "
        f'builtins.hasAttr "{effective_output}" target; '
        f"in if hasIt then target.{effective_output} else target"
    )

    # Build the Nix package, verify it succeeded, and export the output as
    # a .nar file.
    container_script = f"""
    OUT_PATH=$(nix-build --no-out-link -E '{nix_expression}')
    if [ -z "$OUT_PATH" ] || [ ! -e "$OUT_PATH" ]; then
        echo "Error: nix-build failed to return a valid store path." >&2
        exit 1
    fi
    nix-store --dump "$OUT_PATH" > /build_output/{nar_filename}
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
        *_nixpkgs_mount_args(worktree_path),
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
            raise Exception(
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
    releases = [r for r in releases if r.get("version") == version]

    for release in releases:
        release_version = release.get("version", "")
        if version and release_version != version:
            continue
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
    api_url = f"https://search.devbox.sh/v2/pkg?name={purl.name}"
    try:
        return fetch_json_response(api_url)
    except Exception as e:
        logger.warning(f"Failed to fetch package data for {purl}: {e}")
        return None


def get_nix_store_path_with_nix(name, system, output, commit_hash):
    """Find and return the store path using `nix`."""
    system_config = f'system = "{system}";' if system else ""
    config_str = "config = { allowBroken = true; allowUnfree = true; };"

    worktree_path = _get_nixpkgs_worktree(commit_hash)
    nixpkgs_import = _nixpkgs_import_expr(
        commit_hash, worktree_path, system_config, config_str
    )

    nix_expression = (
        "let "
        f"  pkgs = {nixpkgs_import}; "
        f"  target = pkgs.{name}; "
        f'  hasIt = builtins.isAttrs target && builtins.hasAttr "{output}" target; '
        f'in if hasIt then target.{output}.outPath else ""'
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
    if archive_name.endswith(".zst"):
        return f"zstdcat /input/{archive_name}"
    if archive_name.endswith(".xz"):
        return f"xzcat /input/{archive_name}"
    if archive_name.endswith(".bz2"):
        return f"bzcat /input/{archive_name}"
    if archive_name.endswith(".gz"):
        return f"zcat /input/{archive_name}"
    return f"cat /input/{archive_name}"


def extract_nar_archive(archive_path, output_dir, output):
    """Extract a compressed Nix NAR archive."""
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

    decompress_cmd = _decompress_pipeline_for(archive_name)
    restore_pipeline = f"{decompress_cmd} | nix-store --restore /output/to/{output}"

    # nix-store --restore runs as root inside the container and preserves the
    # NAR's ownership metadata, so the extracted tree ends up owned by root.
    # Chown it back to the calling user so ScanCode can extract nested archives,
    # read the files, and clean up afterwards.
    host_uid = os.getuid()
    host_gid = os.getgid()

    container_script = (
        f"rm -rf /output/to/{output} "
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

    worktree_path = _get_nixpkgs_worktree(commit_hash)
    nixpkgs_import = _nixpkgs_import_expr(
        commit_hash, worktree_path, system_config, config_str
    )

    # `applyPatches` unpacks `pkg.src`, applies `pkg.patches`, and copies
    # the resulting tree to `$out`.
    nix_expression = f"""
    let
        pkgs = {nixpkgs_import};
        pkg = pkgs.{name};
    in
    if !(pkg ? src) then pkg
    else pkgs.applyPatches {{
        name = "{name}-patched-src";
        src = pkg.src;
        patches = pkg.patches or [];
        prePatch = pkg.prePatch or "";
        postPatch = pkg.postPatch or "";
    }}"""

    fallback_expression = f"""
    let
        pkgs = {nixpkgs_import};
        pkg = pkgs.{name};
    in
        if pkg ? gemFile then pkg.gemFile
        else if pkg ? src then pkg.src
        else pkg
    """

    # This bash script must NOT be indented in Python.
    # If EOF has spaces before it, bash will fail to parse it.
    # The following script first attempts a standard patched build; if that
    # fails (or yields no files), it falls back to fetching the raw source
    # archive. The result is copied to the mounted `from/` directory with
    # correct ownership so the host can extract and process it.
    container_script = f"""
set -e

cat << 'EOF' > /tmp/expr.nix
{nix_expression}
EOF

cat << 'EOF' > /tmp/fallback.nix
{fallback_expression}
EOF

# Try standard patched build
OUT_PATH=$(nix-build --no-out-link /tmp/expr.nix || true)

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
    OUT_PATH=$(nix-build --no-out-link /tmp/fallback.nix || true)
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
        *_nixpkgs_mount_args(worktree_path),
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


def ensure_multiarch_emulation():
    """
    Configure Docker host with binfmt emulators to support
    multi-architecture execution and builds.
    """
    cmd = [
        "docker",
        "run",
        "--privileged",
        "--rm",
        "--init",
        "tonistiigi/binfmt",
        "--install",
        "all",
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)  # noqa: S603
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Could not install binfmt multi-arch emulators: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Timeout trying to setup binfmt emulators. Skipping.")
        return False

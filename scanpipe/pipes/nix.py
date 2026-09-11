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
import logging
import os
import shutil
import subprocess
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
PatchedSourceResult = namedtuple(
    "PatchedSourceResult", ["path", "used_fallback", "fallback_reason"]
)

FALLBACK_REASON_PREFIX = "PATCHED_SOURCE_FALLBACK_REASON="


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
        raise Exception(
            "Only official nixpkgs repository is supported (i.e. namespace=nixpkgs)."
        )

    qualifiers = input_purl.qualifiers or {}
    if not input_purl.version and "commit" not in qualifiers:
        raise Exception("Version or a 'commit' qualifier is required.")

    if "system" not in qualifiers:
        raise Exception(
            "The 'system' qualifier is required to resolve system-specific binaries."
        )

    return input_purl


def fetch_inputs(purl, output_dir):
    """
    Fetch the system specific binary and the exact source tree with the
    patches and configurations applied for the given input purl. Return a
    tuple of (source_path, binary_path, output_format, error_message,
    warning_message).
    """
    data = get_package_data(purl)
    name = purl.name
    version = purl.version

    commit_hash = purl.qualifiers.get("commit", "")
    system = purl.qualifiers.get("system", "")
    user_output = purl.qualifiers.get("output", "")
    error_message = ""
    warning_message = ""

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
            bin_path = build_binary_with_docker(
                name, output_dir, system, concluded_commit_hash, output_format
            )
        if bin_path:
            logger.info(f"Successfully built binary for {purl} to {bin_path}")
            warning_message = (
                f"Binary not found in cache for {purl}. Built locally using "
                f"commit {concluded_commit_hash} with a Linux-based Nix "
                f"Docker container."
            )
            logger.warning(warning_message)
        else:
            error_message = f"Failed to fetch or build the binary for {purl}"
            logger.error(error_message)

    source_result = PatchedSourceResult("", False, "")
    if concluded_commit_hash:
        source_result = get_patched_source_with_docker(
            name, output_dir, system, concluded_commit_hash
        )

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
        if warning_message:
            warning_message = f"{warning_message}\n{fallback_warning}"
        else:
            warning_message = fallback_warning
        logger.warning(fallback_warning)

    return (
        source_result.path,
        bin_path,
        output_format,
        error_message,
        warning_message,
    )


def build_binary_with_docker(name, output_dir, system, commit_hash, output_format):
    """
    Fetch a Nix package and build its binary from source using Docker.
    Exports the resulting store path as a .nar file for standard extraction.

    Return an empty string if build fails.
    """
    nar_filename = f"{name}-bin.nar"
    extracted_path = Path(output_dir) / nar_filename
    absolute_out_dir = str(Path(output_dir).resolve())

    # Handle architecture and system incompatibilities
    target_os = system.split("-")[-1] if "-" in system else system
    if target_os and target_os != "linux":
        logger.warning(
            f"SYSTEM BARRIER DETECTED: Target system '{system}' requires "
            f"OS-specific SDKs that cannot be evaluated inside the "
            f"Linux-based Nix Docker container. Defaulting the build to "
            f"the container's native Linux architecture."
        )
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

    nixpkgs_import = (
        f'import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/'
        f'{commit_hash}.tar.gz") {{ {system_config} {config_str} }}'
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

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        "nix-eval-cache:/nix",
        "-v",
        f"{absolute_out_dir}:/build_output",
        "nixos/nix",
        "/bin/sh",
        "-c",
        container_script,
    ]

    task_description = f"Building ({name} for {system})"

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=1800)  # noqa: S603
        if extracted_path.exists():
            return str(extracted_path)
        return ""
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed: {task_description} with error: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error(f"Failed: {task_description} with error: Process timed out")
    return ""


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
    based on the qualifiers
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
                if out.get("name") == output:
                    return release_commit_hash, out.get("path")
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
    """Find and return the store path using 'nix'"""
    system_config = f'system = "{system}";' if system else ""
    config_str = "config = { allowBroken = true; allowUnfree = true; };"

    nix_expression = (
        "let "
        f"  pkgs = import (fetchTarball "
        f'"https://github.com/NixOS/nixpkgs/archive/{commit_hash}.tar.gz") '
        f"{{ {system_config} {config_str} }}; "
        f"  target = pkgs.{name}; "
        f'  hasIt = builtins.isAttrs target && builtins.hasAttr "{output}" target; '
        f'in if hasIt then target.{output}.outPath else ""'
    )

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        "nix-eval-cache:/nix",
        "nixos/nix",
        "nix-instantiate",
        "--eval",
        "--raw",
        "-E",
        nix_expression,
    ]

    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, check=True, timeout=300
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error evaluating attribute for package '{name}': {e.stderr}")
        return ""
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout evaluating attribute for package '{name}'")
        return ""


def get_nix_download_url(path):
    """Construct a download url from cache.nixos.org based on store path"""
    base_name = path.rstrip("/").split("/")[-1]
    narinfo_hash = base_name.split("-")[0]

    narinfo_url = f"https://cache.nixos.org/{narinfo_hash}.narinfo"
    url_path = get_narinfo_url(narinfo_url)

    if not url_path:
        logger.warning(f"{narinfo_url} is not accessible.")
        return ""

    return f"https://cache.nixos.org/{url_path}"


def get_narinfo_url(narinfo_url):
    """Visit the narinfo url, parse and return the URL value"""
    try:
        response = requests.get(narinfo_url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return ""

    for line in response.text.splitlines():
        if line.startswith("URL:"):
            return line.split(":", 1)[1].strip()

    return ""


def cleanup_docker_volumes():
    """Cleanup the Docker volumes used for Nix."""
    if not shutil.which("docker"):
        return

    cmd = ["docker", "volume", "rm", "-f", "nix-eval-cache"]
    try:
        subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603
    except Exception as e:
        logger.debug(f"Failed to cleanup Docker volumes: {e}")


atexit.register(cleanup_docker_volumes)


def _get_decompress_cmd(archive_name):
    """Return (compression_type, decompress_cmd) for the archive name."""
    if archive_name.endswith(".xz"):
        return "xz", f"xzcat /input/{archive_name}"
    if archive_name.endswith(".zst"):
        return "zstd", f"zstdcat /input/{archive_name}"
    if archive_name.endswith(".bz2"):
        return "bzip2", f"bzcat /input/{archive_name}"
    if archive_name.endswith(".gz"):
        return "gzip", f"zcat /input/{archive_name}"
    return None, f"cat /input/{archive_name}"


def _stage_archive(archive_path, output_dir):
    """
    Ensure the archive lives inside output_dir so it is visible to the Docker
    daemon that resolves the `-v` mount source. Return the staged path.
    """
    target = output_dir / archive_path.name
    if archive_path == target:
        return target

    is_present = (
        target.exists() and target.stat().st_size == archive_path.stat().st_size
    )
    if not is_present:
        shutil.copy2(archive_path, target)
    return target


def extract_nar_archive(archive_path, output_dir, output):
    """Extract a compressed Nix NAR archive."""
    archive_path = Path(archive_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Docker mounts are resolved by the daemon, not the client. To make the
    # archive visible to the daemon that runs the container, it must live
    # in `output_dir` — the one path this project shares with that daemon.
    archive_path = _stage_archive(archive_path, output_dir)

    archive_dir = str(archive_path.parent)
    archive_name = archive_path.name
    extracted_path = output_dir / "to" / output

    compression_type, decompress_cmd = _get_decompress_cmd(archive_name)

    if compression_type:
        restore_pipeline = (
            f"nix-shell -p {compression_type} --run "
            f"'{decompress_cmd} | nix-store --restore /output/to/{output}'"
        )
    else:
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

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        "nix-eval-cache:/nix",
        "-v",
        f"{archive_dir}:/input:ro",
        "-v",
        f"{output_dir}:/output",
        "nixos/nix",
        "/bin/sh",
        "-c",
        container_script,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)  # noqa: S603
        return str(extracted_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract {archive_name} with error: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error(f"Failed to extract {archive_name}: Process timed out")
    finally:
        if archive_path.parent == output_dir:
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

    # Get the OS part from the system string (e.g. 'aarch64-darwin' to 'darwin')
    target_os = system.split("-")[-1] if "-" in system else system

    if target_os and target_os != "linux":
        logger.warning(
            f"SYSTEM BARRIER DETECTED: Target system '{system}' requires "
            f"OS-specific SDKs that cannot be evaluated inside the "
            f"Linux-based Nix Docker container."
        )
        logger.warning(
            f"FALLBACK IN EFFECT: Evaluating the source using the container's "
            f"native Linux environment. The extracted source tree will "
            f"contain Linux-specific patches instead of {system} patches. "
            f"Impact on the deployment to development mapping is expected to "
            f"be minimal: you may observe a small number of unmapped files "
            f"due to missing OS-specific structural patches."
        )
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

    nixpkgs_import = (
        f'import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/'
        f'{commit_hash}.tar.gz") {{ {system_config} {config_str} }}'
    )

    # Build patched source, but first `cd` into the actual source root
    # (`$sourceRoot`) so we copy only its contents, not the wrapper
    # directory that Nix creates during unpacking. This prevents
    # duplicate paths like `from/<hash>-source/src/...`.
    nix_expression = f"""
    let
        pkgs = {nixpkgs_import};
        pkg = pkgs.{name};
    in
    pkg.overrideAttrs (old: {{
        name = (old.name or "{name}") + "-patched-src";
        phases = [ "unpackPhase" "patchPhase" "installPhase" ];
        installPhase = ''
            mkdir -p $out
            rm -f env-vars

            if [ -n "$sourceRoot" ] && [ -d "$sourceRoot" ]; then
                cd "$sourceRoot"
            fi

            cp -a . $out/
        '';
        outputs = [ "out" ];
        separateDebugInfo = false;
        doCheck = false;
        doInstallCheck = false;
    }})"""

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

cat << 'EOF' > /build_output/expr.nix
{nix_expression}
EOF

cat << 'EOF' > /build_output/fallback.nix
{fallback_expression}
EOF

# Try standard patched build
OUT_PATH=$(nix-build --no-out-link /build_output/expr.nix || true)

# Check if output is empty or only contains env-vars which is generated by Nix
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

# Use raw archive if standard build failed or was empty
if [ -n "$FALLBACK_REASON" ]; then
    echo "PATCHED_SOURCE_FALLBACK_REASON=$FALLBACK_REASON" >&2
    OUT_PATH=$(nix-build --no-out-link /build_output/fallback.nix || true)
fi

# If both completely failed, clean up and exit
if [ -z "$OUT_PATH" ] || [ ! -e "$OUT_PATH" ]; then
    echo "Error: nix-build failed to return a valid store path." >&2
    rm -f /build_output/expr.nix /build_output/fallback.nix
    exit 1
fi

# Copy contents (if directory) or the single file (if archive)
if [ -d "$OUT_PATH" ]; then
    cp -a "$OUT_PATH/." /build_output/
else
    cp -L "$OUT_PATH" /build_output/
fi

# Set ownership to the host user so Python can extract it
chown -R $HOST_UID:$HOST_GID /build_output/
chmod -R u+w /build_output/

# Cleanup the temp nix files
rm -f /build_output/expr.nix /build_output/fallback.nix
"""

    cmd = [
        "docker",
        "run",
        "--rm",
        "-e",
        f"HOST_UID={host_uid}",
        "-e",
        f"HOST_GID={host_gid}",
        "-v",
        "nix-eval-cache:/nix",
        "-v",
        f"{absolute_out_dir}:/build_output",
        "nixos/nix",
        "/bin/sh",
        "-c",
        container_script,
    ]

    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, check=True, timeout=600
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
            )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error("Process timed out")

    shutil.rmtree(extracted_path, ignore_errors=True)
    return PatchedSourceResult(path="", used_fallback=False, fallback_reason="")


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

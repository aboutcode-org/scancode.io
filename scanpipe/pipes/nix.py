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
import shutil
import subprocess
from pathlib import Path

import requests
from fetchcode import fetch_json_response
from packageurl import PackageURL

from scanpipe.pipes import utils

logger = logging.getLogger(__name__)


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
    tuple of (source_path, binary_path, output_format).
    """
    data = get_package_data(purl)
    name = purl.name
    version = purl.version

    commit_hash = purl.qualifiers.get("commit", "")
    system = purl.qualifiers.get("system", "")
    user_output = purl.qualifiers.get("output", "")

    output_format, path, release_commit_hash = get_nix_store_path(
        data, name, version, system, commit_hash, user_output
    )

    nix_bin_download_url = get_nix_download_url(path) if path else ""

    src_path = ""
    concluded_commit_hash = release_commit_hash or commit_hash
    if concluded_commit_hash:
        src_path = get_patched_source_with_docker(
            name, output_dir, system, concluded_commit_hash
        )

    bin_path = ""
    if nix_bin_download_url:
        bin_path = utils.fetch_path(nix_bin_download_url)
        logger.info(f"Downloaded binary for {purl} to {bin_path}")
    else:
        logger.info(f"Unable to download the binary for {purl}")

    return src_path, bin_path, output_format


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
                "for Nix to determine the download URL."
            )
        raise Exception(f"Unable to determine the download URL for {name}")

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
        'in if hasIt then target.{output}.outPath else ""'
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


def extract_nar_archive(archive_path, output_dir, output):
    """Extract a compressed Nix NAR archive."""
    archive_path = Path(archive_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_dir = str(archive_path.parent)
    archive_name = archive_path.name

    extracted_path = output_dir / "to" / output

    if archive_name.endswith(".xz"):
        compression_type = "xz"
        decompress_cmd = f"xzcat /input/{archive_name}"
    elif archive_name.endswith(".zst"):
        compression_type = "zstd"
        decompress_cmd = f"zstdcat /input/{archive_name}"
    elif archive_name.endswith(".bz2"):
        compression_type = "bzip2"
        decompress_cmd = f"bzcat /input/{archive_name}"
    elif archive_name.endswith(".gz"):
        compression_type = "gzip"
        decompress_cmd = f"zcat /input/{archive_name}"
    else:
        compression_type = None
        decompress_cmd = f"cat /input/{archive_name}"

    if compression_type:
        restore_pipeline = (
            f"nix-shell -p {compression_type} --run "
            f"'{decompress_cmd} | nix-store --restore /output/to/{output}'"
        )
    else:
        restore_pipeline = f"{decompress_cmd} | nix-store --restore /output/to/{output}"

    container_script = (
        f"rm -rf /output/to/{output} && mkdir -p /output/to && {restore_pipeline}"
    )

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{archive_dir}:/input:ro",
        "-v",
        f"{output_dir}:/output",
        "nixos/nix",
        "sh",
        "-c",
        container_script,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)  # noqa: S603
        return str(extracted_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract {archive_name} with error: {e.stderr.strip()}")
        return ""
    except subprocess.TimeoutExpired:
        logger.error(f"Failed to extract {archive_name}: Process timed out")
        return ""


def get_patched_source_with_docker(name, output_dir, system, commit_hash):
    """Fetch a Nix package source and apply its official patches."""
    extracted_path = Path(output_dir) / "from"
    extracted_path.mkdir(parents=True, exist_ok=True)
    absolute_out_dir = str(extracted_path.resolve())

    # Get the OS part from the system string (e.g. 'aarch64-darwin' to 'darwin')
    target_os = system.split("-")[-1] if "-" in system else system

    # Check for OS incompatibility
    # Since the Docker container uses 'nixos/nix' which is linux-based, it
    # cannot build the patched sources for other systems
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
        # Empty string forces Nix to use the container's native architecture
        system_config = ""
    else:
        # Use crossSystem for compatible cross-architectures
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

    nix_expression = (
        f"let "
        f"  pkgs = {nixpkgs_import}; "
        f"  pkg = pkgs.{name}; "
        f"in "
        f"pkg.overrideAttrs (old: {{ "
        f'  name = (old.name or "{name}") + "-patched-src"; '
        f'  phases = [ "unpackPhase" "patchPhase" "installPhase" ]; '
        f'  installPhase = "mkdir -p $out && cp -a . $out/"; '
        f'  outputs = [ "out" ]; '
        f"  separateDebugInfo = false; "
        f"  doCheck = false; "
        f"  doInstallCheck = false; "
        f"}})"
    )

    container_script = f"""
    OUT_PATH=$(nix-build --no-out-link -E '{nix_expression}')
    if [ -z "$OUT_PATH" ] || [ ! -d "$OUT_PATH" ]; then
        echo "Error: nix-build failed to return a valid store path." >&2
        exit 1
    fi
    cp -a "$OUT_PATH/." /build_output/
    """

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{absolute_out_dir}:/build_output",
        "nixos/nix",
        "sh",
        "-c",
        container_script,
    ]

    task_description = f"Nix Build & Patch ({name} for {system})"

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)  # noqa: S603
        return str(extracted_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed: {task_description} with error: {e.stderr.strip()}")
        return ""
    except subprocess.TimeoutExpired:
        logger.error(f"==> Failed: {task_description} with error: Process timed out")
        return ""


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

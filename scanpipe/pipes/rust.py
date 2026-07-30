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

import shutil
import subprocess
import logging
import requests

from packageurl import PackageURL
from pathlib import Path
from scanpipe.pipes import fetch
from scanpipe.pipes import run_command_safely


logger = logging.getLogger(__name__)


def build_crates(codebase_dir):
    """
    Build the Rust crate from sources in an isolated Docker container.

    Uses the official rust image to safely sandbox the build process and
    injects RUSTFLAGS to force DWARF debug symbol generation (-C debuginfo=2)
    required for binary-to-source mapping.

    Return True if build successfully, False otherwise.
    """

    # Find the Cargo.toml file in the codebase directory
    codebase_dir = Path(codebase_dir)
    cargo_toml_path = None
    for path in codebase_dir.rglob("Cargo.toml"):
        cargo_toml_path = path
        break
    if cargo_toml_path:
        to_dir = codebase_dir / "to"
    else:
        return False

    cargo_toml_path = Path(cargo_toml_path)
    build_dir = Path(to_dir)

    # Calculate paths relative to the container's mounted /codebase directory
    rel_cargo_toml = cargo_toml_path.relative_to(codebase_dir).as_posix()
    rel_build_dir = build_dir.relative_to(codebase_dir).as_posix()

    container_cargo_toml = f"/codebase/{rel_cargo_toml}"
    container_build_dir = f"/codebase/{rel_build_dir}"

    cmd = [
        "docker", "run",
        "--rm",  # Automatically remove the container when it exits
        "--volume", f"{codebase_dir}:/codebase",
        "--workdir", "/codebase",
        "--env", "RUSTFLAGS=-C debuginfo=2",  # Force DWARF generation in release mode
        "rust:latest",
        "cargo", "build",
        "--release",
        "--locked",
        "--manifest-path", container_cargo_toml,
        "--target-dir", container_build_dir,
    ]

    try:
        run_command_safely(cmd)
    except subprocess.SubprocessError as error:
        logger.warning(f"Failed to build the Rust crate in Docker: {error}")
        return False

    from_dir = codebase_dir / "from"
    from_dir.mkdir(exist_ok=True)
    for item in codebase_dir.iterdir():
        if item != to_dir and item != from_dir:
            shutil.move(str(item), str(from_dir / item.name))
    return True


def check_input_and_return_purl(project):
    """Validate the input and return a cargo PURL."""
    input_sources = project.inputsources.all()
    if len(input_sources) != 1:
        error_msg = "Only 1 cargo purl is accepted."
        raise ValueError(error_msg)
    # Strip the qualifiers as this is not needed.
    project_input = str(input_sources[0]).split("?")[0]
    input_purl = PackageURL.from_string(project_input)

    if input_purl.type != "cargo":
        error_msg = "Only cargo purl is supported."
        raise ValueError(error_msg)
    if not input_purl.version:
        error_msg = "Version is required."
        raise ValueError(error_msg)

    return input_purl


def fetch_inputs(purl):
    """Fetch the source for the given input purl"""
    purl_str = PackageURL.to_string(purl)

    purl_src_path = fetch_path(purl_str)

    if not purl_src_path:
        err_msg = f"No source could be resolved for {purl}."
        raise ValueError(err_msg)

    return purl_src_path


def fetch_path(purl):
    """Fetch the purl and return the location of the fetched tarball"""
    try:
        return fetch.fetch_url(url=purl).path
    except (ValueError, requests.RequestException) as e:
        logger.warning("Failed to fetch package: %s - %s", purl, e)
        return None

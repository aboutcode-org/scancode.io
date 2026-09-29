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

import logging
import shutil
import subprocess
from pathlib import Path

import tomllib
from packageurl import PackageURL

from scanpipe.pipes import run_command_safely

logger = logging.getLogger(__name__)


def build_crates(codebase_dir, cargo_toml_path):
    """
    Build the Rust crate from source in an isolated Docker container.
    Use the official Rust image for the build process.
    Return True if the build succeeds, False otherwise.
    """
    to_dir = codebase_dir / "to"
    cargo_toml_path = Path(cargo_toml_path)
    build_dir = Path(to_dir)

    # Get the relative paths
    relative_cargo_toml = cargo_toml_path.relative_to(codebase_dir).as_posix()
    relative_build_dir = build_dir.relative_to(codebase_dir).as_posix()

    container_cargo_toml = f"/codebase/{relative_cargo_toml}"
    container_build_dir = f"/codebase/{relative_build_dir}"

    # Since we will use the .d file for deployment and development file
    # mapping, we will not require building with DWARF debug symbols. If we
    # later decide to include DWARF, we can add the following to the
    # command:
    # "--env", "RUSTFLAGS=-C debuginfo=2",
    cmd = [
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{codebase_dir}:/codebase",
        "--workdir",
        "/codebase",
        "rust:latest",
        "cargo",
        "build",
        "--release",
        "--locked",
        "--manifest-path",
        container_cargo_toml,
        "--target-dir",
        container_build_dir,
    ]

    try:
        run_command_safely(cmd)
    except subprocess.SubprocessError as error:
        logger.warning(f"Failed to build the Rust crate in Docker: {error}")
        return False

    # Move the development code under the /codebase/from/
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
    # Strip the qualifiers if present as this is not needed
    project_input = str(input_sources[0]).split("?")[0]
    input_purl = PackageURL.from_string(project_input)

    if input_purl.type != "cargo":
        error_msg = "Only cargo purl is supported."
        raise ValueError(error_msg)
    if not input_purl.version:
        error_msg = "Version is required."
        raise ValueError(error_msg)

    return input_purl


def get_repository_value_from_cargo_toml(cargo_toml_path):
    """Get the repository value from Cargo.toml."""
    path = Path(cargo_toml_path)
    if not path.exists():
        raise FileNotFoundError(f"{cargo_toml_path} not found")

    with path.open("rb") as f:
        data = tomllib.load(f)

    return data.get("package", {}).get("repository", "")


def get_cargo_toml_path(codebase_dir):
    """Get the Cargo.toml path from the codebase directory."""
    cargo_toml_path = None
    # There is only one "Cargo.toml" per published package
    for path in codebase_dir.rglob("Cargo.toml"):
        cargo_toml_path = path
        break
    return cargo_toml_path

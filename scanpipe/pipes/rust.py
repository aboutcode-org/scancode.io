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

from scanpipe.pipes import fetch
from scanpipe.pipes import run_command_safely

logger = logging.getLogger(__name__)

# Pinned Rust toolchain image to make builds reproducible across releases.
RUST_DOCKER_IMAGE = "rust:1.99"


def build_crates(codebase_dir, cargo_toml_path):
    """
    Build the Rust crate from source in an isolated Docker container.
    Use the official Rust image for the build process.
    The image version is defined in RUST_DOCKER_IMAGE.

    Return a 3-tuple ``(success, cargo_toml_path, devel_codebase_dir)``.
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
        RUST_DOCKER_IMAGE,
        "cargo",
        "build",
        "--release",
        "--manifest-path",
        container_cargo_toml,
        "--target-dir",
        container_build_dir,
    ]

    # Conditionally add --locked if Cargo.lock exists alongside Cargo.toml
    # Many published crates don't ship a Cargo.lock. Having `--locked`
    # makes cargo fail if the lock file is missing or stale.
    cargo_lock_path = cargo_toml_path.with_name("Cargo.lock")
    if cargo_lock_path.exists():
        cmd.append("--locked")

    try:
        run_command_safely(cmd)
    except subprocess.SubprocessError as error:
        logger.warning(f"Failed to build the Rust crate in Docker: {error}")
        return False, cargo_toml_path, codebase_dir

    # Move the development code under the /codebase/from/
    from_dir = codebase_dir / "from"
    from_dir.mkdir(exist_ok=True)
    for item in codebase_dir.iterdir():
        if item != to_dir and item != from_dir:
            shutil.move(str(item), str(from_dir / item.name))

    new_cargo_toml_path = from_dir / cargo_toml_path.relative_to(codebase_dir)
    return True, new_cargo_toml_path, from_dir


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


def fetch_inputs(purl):
    """Fetch the source for the given input purl."""
    purl_str = PackageURL.to_string(purl)
    purl_src_path = fetch.fetch_path(purl_str)
    if not purl_src_path:
        err_msg = f"No source could be resolved for {purl}."
        raise ValueError(err_msg)
    return Path(purl_src_path)


def get_cargo_toml_path(codebase_dir, purl):
    """Return the root Cargo.toml path of the extracted ``purl`` crate."""
    path = Path(codebase_dir) / f"{purl.name}-{purl.version}" / "Cargo.toml"
    if path.exists():
        return path
    return None


def get_rust_file_paths(location):
    """Retrieve Rust file paths from a ``.d`` dep-info file."""
    file_paths = {}
    rust_lib_path, rust_file_paths = parse_d_file(location)
    if rust_file_paths:
        file_paths["rust_file_paths"] = rust_file_paths
    return rust_lib_path, file_paths


def parse_d_file(path):
    """Parse the .d file from rust package."""
    try:
        context = Path(path).read_text()
    except OSError:
        return "", []

    cleaned_context = context.replace("\\\n", " ")

    # Invalid .d file
    if ":" not in cleaned_context:
        return "", []

    rust_lib, dep_paths = cleaned_context.split(":", 1)
    rust_lib_path = rust_lib.strip()

    file_paths = []
    for file_path in dep_paths.split():
        file_path = file_path.strip()
        if file_path:
            file_paths.append(file_path)

    return rust_lib_path, file_paths


def find_crate_subdirectory(source_repo_path, purl):
    """
    Return the path to the crate subdirectory within a monorepo archive,
    or None if the crate lives at the archive root.

    The search looks for a ``Cargo.toml`` whose parent directory is named
    after the crate or the crate-version pair.
    """
    source_repo_path = Path(source_repo_path)

    # Archives usually have a single top-level directory named after the
    # repo and version, e.g. ``uselesskey-0.2.0/``. Use it as the new
    # search root when present.
    top_level_dirs = [entry for entry in source_repo_path.iterdir() if entry.is_dir()]
    if len(top_level_dirs) == 1:
        source_repo_path = top_level_dirs[0]

    # Look for a directory named after the crate, either with just the
    # crate name (``uselesskey-hmac``) or with the version added
    # (``uselesskey-hmac-0.2.0``).
    expected_crate_dir_names = {
        purl.name,
        f"{purl.name}-{purl.version}",
    }

    for cargo_toml in source_repo_path.rglob("Cargo.toml"):
        candidate_crate_dir = cargo_toml.parent
        if candidate_crate_dir.name in expected_crate_dir_names:
            return candidate_crate_dir

    return None

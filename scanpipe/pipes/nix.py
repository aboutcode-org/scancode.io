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

import json
import os
import re
import shutil
import stat
import subprocess
from contextlib import suppress
from itertools import islice
from pathlib import Path
from urllib.parse import urlencode

import requests
from license_expression import Licensing
from packageurl import PackageURL

from scanpipe import pipes
from scanpipe.pipes import fetch
from scanpipe.pipes import flag
from scanpipe.pipes import scancode
from scanpipe.pipes.resolve import convert_spdx_expression

REQUIRED_COMMANDS = ["nix-build", "nix-instantiate", "nix-store", "xz", "zstd"]
NIX_CACHE_URL = "https://cache.nixos.org"
DEVBOX_SEARCH_URL = "https://search.devbox.sh/v2/pkg"
NIXPKGS_API_URL = "https://api.github.com/repos/NixOS/nixpkgs"

NIX_EVAL_TIMEOUT = 600
NIX_BUILD_TIMEOUT = 1800
DOWNLOAD_CHUNK_SIZE = 1024 * 1024

GITHUB_RATE_LIMIT_ERROR = (
    "The GitHub API rate limit is reached. Provide a GitHub token for "
    "api.github.com with the SCANCODEIO_FETCH_HEADERS setting."
)

# The PURL values end up in Nix expressions arguments, URLs, and file paths:
# only a strict set of characters is accepted.
ATTRIBUTE_PATH_REGEX = re.compile(r"[a-zA-Z0-9_][a-zA-Z0-9_\-+.]*")
COMMIT_REGEX = re.compile(r"[0-9a-f]{40}")
SYSTEM_REGEX = re.compile(r"[a-z0-9_]+-[a-z0-9_]+")
OUTPUT_REGEX = re.compile(r"[a-z][a-z0-9]*")

# A misspelled qualifier, such as "outptu", would be silently ignored.
SUPPORTED_QUALIFIERS = {"commit", "output", "system"}

# The nixpkgs licenses without SPDX id, such as "LicenseRef-nixos-unfree", are not
# known by ScanCode: a single one would turn the whole expression into "unknown".
NIXOS_LICENSE_REF_REGEX = re.compile(r"LicenseRef-nixos-[\w.+-]+")
UNKNOWN_LICENSE_REF = "LicenseRef-scancode-unknown-license-reference"

# A ScanCode "or later" license key: a versioned license key followed by "-plus",
# such as "gpl-3.0-plus" for "gpl-3.0". The "m-plus" font license is not one.
OR_LATER_LICENSE_KEY_REGEX = re.compile(r"(?P<base_key>.+-\d+(\.\d+)*)-plus")

# The package outputs holding headers and documentation, not the deployed code.
NON_DEPLOYED_OUTPUTS = {"dev", "devdoc", "devman", "doc", "info", "man"}

DECOMPRESS_COMMANDS = {
    "none": ["cat"],
    "xz": ["xz", "--decompress", "--stdout"],
    "zstd": ["zstd", "--decompress", "--stdout"],
}

# Licenses detected in the source that are not useful to compare with the
# declared license.
IGNORED_LICENSE_KEYS = {
    "free-unknown",
    "unknown",
    "unknown-license-reference",
    "unknown-spdx",
}

# The user input is passed as `--argstr` values, never interpolated in the
# expression. `fetchTarball` downloads nixpkgs at the given commit, no local
# clone is required.
NIXPKGS_EXPRESSION = """
{ commit, attributePath, system ? builtins.currentSystem }:
let
  nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/archive/${commit}.tar.gz";
  pkgs = import nixpkgs {
    inherit system;
    config = {
      allowUnfree = true;
      allowBroken = true;
      allowUnsupportedSystem = true;
      allowInsecurePredicate = _: true;
    };
  };
  package = pkgs.lib.getAttrFromPath (pkgs.lib.splitString "." attributePath) pkgs;
in
"""

METADATA_EXPRESSION = (
    NIXPKGS_EXPRESSION
    + """
let
  meta = package.meta or { };
  # Recent nixpkgs combine licenses with operators, such as "OR [ mit asl20 ]",
  # converted by toSPDX. A license without SPDX id is a "LicenseRef-nixos-" one.
  getLicenseExpression = license:
    if builtins.isAttrs license && license ? licenseType
    then pkgs.lib.licenses.toSPDX license
    else if builtins.isAttrs license
    then license.spdxId or "LicenseRef-nixos-${license.shortName or "unknown"}"
    else if builtins.isString license then license
    else null;
  licenseExpressions = map getLicenseExpression (pkgs.lib.toList (meta.license or [ ]));
  getOutputPath = output: { name = output; value = package.${output}.outPath; };
in
{
  version = package.version or "";
  description = meta.description or "";
  homepage = meta.homepage or "";
  licenses = builtins.filter (expression: expression != null) licenseExpressions;
  outputs = builtins.listToAttrs (map getOutputPath (package.outputs or [ "out" ]));
}
"""
)

PATCHED_SOURCE_EXPRESSION = (
    NIXPKGS_EXPRESSION
    + """
pkgs.applyPatches {
  name = "source";
  src = package.src;
  patches = package.patches or [ ];
  prePatch = package.prePatch or "";
  postPatch = package.postPatch or "";
}
"""
)

UPSTREAM_SOURCE_EXPRESSION = NIXPKGS_EXPRESSION + "package.src"


class NixCommandError(Exception):
    pass


def get_missing_commands():
    """Return the list of commands required by the Nix pipeline not installed."""
    return [command for command in REQUIRED_COMMANDS if not shutil.which(command)]


def get_nix_purl(project):
    """Return the Nix PURL provided as the unique input of the ``project``."""
    input_sources = project.inputsources.all()
    if len(input_sources) != 1:
        raise ValueError("Only 1 Nix PURL is accepted as input.")

    purl = PackageURL.from_string(input_sources[0].download_url)
    validate_nix_purl(purl)
    return purl


def validate_nix_purl(purl):
    """Raise a ValueError if the ``purl`` is not a supported Nix PURL."""
    if purl.type != "nix" or purl.namespace != "nixpkgs":
        raise ValueError("Only pkg:nix/nixpkgs/ PURLs are supported.")

    if not ATTRIBUTE_PATH_REGEX.fullmatch(purl.name):
        raise ValueError(f"Invalid Nix package name: {purl.name!r}")

    qualifiers = purl.qualifiers or {}
    if unsupported_qualifiers := sorted(set(qualifiers) - SUPPORTED_QUALIFIERS):
        raise ValueError(
            f"Unsupported qualifiers: {', '.join(unsupported_qualifiers)}. "
            f"The supported qualifiers are: {', '.join(sorted(SUPPORTED_QUALIFIERS))}"
        )

    system = qualifiers.get("system", "")
    if not SYSTEM_REGEX.fullmatch(system):
        raise ValueError(
            "A valid 'system' qualifier is required, for example: system=x86_64-linux"
        )

    commit = qualifiers.get("commit", "")
    if commit and not COMMIT_REGEX.fullmatch(commit):
        raise ValueError(f"Invalid commit: {commit!r}, a 40 characters SHA-1.")

    if not commit and not purl.version:
        raise ValueError("A version or a 'commit' qualifier is required.")

    output = qualifiers.get("output", "")
    if output and not OUTPUT_REGEX.fullmatch(output):
        raise ValueError(f"Invalid output: {output!r}")


def get_binary_group(project):
    """
    Return the optional steps group mapping the binaries of the ``project`` Nix
    PURL input: "MacOS" for a macOS ``system`` qualifier, or else "Elf". The
    input is validated later by the pipeline.
    """
    input_source = project.inputsources.first()
    if not input_source:
        return "Elf"

    system = ""
    with suppress(ValueError):
        purl = PackageURL.from_string(input_source.download_url)
        system = purl.qualifiers.get("system", "")

    if system.endswith("-darwin"):
        return "MacOS"
    return "Elf"


def get_nixpkgs_commit(purl):
    """
    Return the nixpkgs commit of the ``purl``, from its qualifiers or from the
    package releases listed by search.devbox.sh, after checking that the commit
    belongs to the official NixOS/nixpkgs history.
    """
    commit = purl.qualifiers.get("commit") or find_release_commit(purl)

    if not COMMIT_REGEX.fullmatch(commit):
        raise ValueError(f"Invalid commit: {commit!r}")

    if not is_official_nixpkgs_commit(commit):
        raise ValueError(
            f"The commit {commit} is not part of the official NixOS/nixpkgs "
            "master or release-* branches."
        )

    return commit


def get_devbox_releases(package_name):
    """
    Return the ``package_name`` releases listed by search.devbox.sh, or an empty
    list when the package is unknown.
    """
    query = urlencode({"name": package_name})
    session = fetch.get_request_session(DEVBOX_SEARCH_URL)
    response = session.get(
        f"{DEVBOX_SEARCH_URL}?{query}", timeout=fetch.HTTP_REQUEST_TIMEOUT
    )
    if response.status_code == 404:
        return []

    response.raise_for_status()
    return response.json().get("releases") or []


def find_release_commit(purl):
    """Return the nixpkgs commit of the ``purl`` version and system on devbox."""
    system = purl.qualifiers["system"]
    for release in get_devbox_releases(purl.name):
        if release.get("version") != purl.version:
            continue
        for platform in release.get("platforms") or []:
            if platform.get("system") == system:
                return platform.get("commit_hash", "")

    raise ValueError(
        f"No nixpkgs commit found for {purl.name}@{purl.version} on {system}. "
        "Provide the nixpkgs commit with the 'commit' qualifier."
    )


def is_official_nixpkgs_commit(commit):
    """
    Return True if the ``commit`` is reachable from the master branch, or from
    a release-* branch for backports.
    A fork commit can be downloaded through the official repository URL, so the
    commit is checked against the official branches.
    """
    session = fetch.get_request_session(NIXPKGS_API_URL)
    if is_commit_on_branch(session, commit, "master"):
        return True

    release_branches = get_release_branches(session)
    return any(
        is_commit_on_branch(session, commit, branch) for branch in release_branches
    )


def check_github_response(response):
    """
    Raise an HTTPError for an error ``response`` of the GitHub API, with a hint
    to provide a token when the rate limit is reached.
    """
    is_rate_limited = (
        response.status_code == 429
        or response.headers.get("x-ratelimit-remaining") == "0"
    )
    if is_rate_limited:
        raise requests.HTTPError(GITHUB_RATE_LIMIT_ERROR, response=response)

    response.raise_for_status()


def is_commit_on_branch(session, commit, branch):
    """Return True if the ``commit`` is an ancestor of, or equal to, the ``branch``."""
    compare_url = f"{NIXPKGS_API_URL}/compare/{commit}...{branch}"
    response = session.get(compare_url, timeout=fetch.HTTP_REQUEST_TIMEOUT)
    if response.status_code == 404:
        return False

    check_github_response(response)
    # "ahead" means the branch has commits after the commit.
    return response.json().get("status") in ("ahead", "identical")


def get_release_branches(session):
    """Return the nixpkgs release-* branch names, most recent first."""
    url = f"{NIXPKGS_API_URL}/git/matching-refs/heads/release-?per_page=100"
    branches = []
    while url:
        response = session.get(url, timeout=fetch.HTTP_REQUEST_TIMEOUT)
        check_github_response(response)
        branches.extend(
            ref["ref"].removeprefix("refs/heads/") for ref in response.json()
        )
        url = response.links.get("next", {}).get("url")

    return sorted(branches, reverse=True)


def run_nix_command(arguments, timeout, cache_directory=None):
    """
    Run a Nix command and return its standard output. The nixpkgs tarballs are
    cached in the ``cache_directory`` when provided, instead of the user cache.
    """
    environment = None
    if cache_directory:
        environment = {**os.environ, "XDG_CACHE_HOME": str(cache_directory)}

    try:
        completed_process = subprocess.run(  # noqa: S603
            arguments,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired as error:
        raise NixCommandError(
            f"{arguments[0]} timed out after {timeout} seconds"
        ) from error

    if completed_process.returncode:
        error_lines = completed_process.stderr.strip().splitlines()
        raise NixCommandError("\n".join(error_lines[-20:]))

    return completed_process.stdout


def get_nix_expression_arguments(attribute_path, commit, system=None):
    """Return the ``--argstr`` arguments of the nixpkgs expressions."""
    arguments = [
        "--argstr",
        "attributePath",
        attribute_path,
        "--argstr",
        "commit",
        commit,
    ]
    if system:
        arguments.extend(["--argstr", "system", system])
    return arguments


def get_package_metadata(attribute_path, commit, system, cache_directory=None):
    """
    Return the version, description, homepage, licenses SPDX expressions, and the
    store path of each output of the package for the target ``system``.
    """
    arguments = [
        "nix-instantiate",
        "--eval",
        "--strict",
        "--json",
        *get_nix_expression_arguments(attribute_path, commit, system),
        "--expr",
        METADATA_EXPRESSION,
    ]
    output = run_nix_command(
        arguments, timeout=NIX_EVAL_TIMEOUT, cache_directory=cache_directory
    )
    return json.loads(output)


def get_selected_outputs(outputs, selected_output=None):
    """
    Return the ``outputs`` to download: the ``selected_output`` when provided, or
    else the outputs holding deployed code, or else all the outputs.
    Raise a ValueError if the ``selected_output`` is not one of the ``outputs``.
    """
    if not selected_output:
        deployed_outputs = {
            output: store_path
            for output, store_path in outputs.items()
            if output not in NON_DEPLOYED_OUTPUTS
        }
        return deployed_outputs or outputs

    if selected_output not in outputs:
        available_outputs = ", ".join(sorted(outputs))
        raise ValueError(
            f"The output {selected_output!r} does not exist, "
            f"available outputs: {available_outputs}"
        )

    return {selected_output: outputs[selected_output]}


def build_source(expression, attribute_path, commit, cache_directory=None):
    """Build the source ``expression`` and return its store path."""
    arguments = [
        "nix-build",
        "--no-out-link",
        *get_nix_expression_arguments(attribute_path, commit),
        "--expr",
        expression,
    ]
    output = run_nix_command(
        arguments, timeout=NIX_BUILD_TIMEOUT, cache_directory=cache_directory
    )
    return output.strip().splitlines()[-1]


def fetch_source(attribute_path, commit, destination, cache_directory=None):
    """
    Copy the package source, with the nixpkgs patches applied, to ``destination``.
    Fall back to the upstream source when the patched source cannot be built, for
    a patch or an evaluation error, and return this error, or an empty string.

    The source is evaluated for the system running ScanCode.io: the patches
    are the same for most systems.
    """
    patch_error = ""
    try:
        store_path = build_source(
            PATCHED_SOURCE_EXPRESSION, attribute_path, commit, cache_directory
        )
    except NixCommandError as error:
        patch_error = str(error)
        store_path = build_source(
            UPSTREAM_SOURCE_EXPRESSION, attribute_path, commit, cache_directory
        )

    copy_store_path(store_path, destination)
    return patch_error


def copy_store_path(store_path, destination):
    """
    Copy the ``store_path`` content to ``destination``. A store path can be a
    directory or a single file, such as a source archive.
    """
    store_path = Path(store_path)
    destination.mkdir(parents=True, exist_ok=True)

    if store_path.is_dir():
        shutil.copytree(store_path, destination, symlinks=True, dirs_exist_ok=True)
    else:
        archive_name = store_path.name.split("-", 1)[-1]
        shutil.copyfile(store_path, destination / archive_name)

    make_writable(destination)


def make_writable(directory):
    """
    Add the write permission on all the ``directory`` content, as the Nix store
    files are read-only and the project work directory must remain deletable.
    """
    for path in [directory, *directory.rglob("*")]:
        if path.is_symlink():
            continue
        path.chmod(path.stat().st_mode | stat.S_IWUSR)


def get_narinfo(store_path):
    """
    Return the narinfo entries of the ``store_path`` from the Nix binary cache,
    or an empty dict when the store path is not available in the cache.
    """
    store_hash = Path(store_path).name.split("-", 1)[0]
    narinfo_url = f"{NIX_CACHE_URL}/{store_hash}.narinfo"
    session = fetch.get_request_session(narinfo_url)
    response = session.get(narinfo_url, timeout=fetch.HTTP_REQUEST_TIMEOUT)
    if response.status_code == 404:
        return {}

    response.raise_for_status()
    entries = [line.split(": ", 1) for line in response.text.splitlines()]
    return {entry[0]: entry[1] for entry in entries if len(entry) == 2}


def fetch_binary(store_path, destination, download_directory):
    """
    Download the ``store_path`` from the Nix binary cache and extract it to
    ``destination``. Return False when the store path is not in the cache.
    """
    narinfo = get_narinfo(store_path)
    if not narinfo:
        return False

    nar_location = Path(download_directory) / f"{Path(store_path).name}.nar"
    download_file(f"{NIX_CACHE_URL}/{narinfo['URL']}", nar_location)
    restore_nar(nar_location, narinfo.get("Compression", "none"), destination)
    nar_location.unlink()
    return True


def download_file(url, file_location):
    """
    Download the ``url`` to ``file_location`` by chunks, as a NAR archive can be
    larger than the available memory.
    """
    session = fetch.get_request_session(url)
    with session.get(url, stream=True, timeout=fetch.HTTP_REQUEST_TIMEOUT) as response:
        response.raise_for_status()
        chunks = response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE)
        with open(file_location, "wb") as downloaded_file:
            downloaded_file.writelines(chunks)


def restore_nar(nar_location, compression, destination):
    """Extract the ``compression`` compressed NAR archive to ``destination``."""
    decompress_command = DECOMPRESS_COMMANDS.get(compression)
    if not decompress_command:
        raise ValueError(f"Unsupported NAR compression: {compression}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        open(nar_location, "rb") as nar_file,
        subprocess.Popen(  # noqa: S603
            decompress_command,
            stdin=nar_file,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as decompress_process,
    ):
        try:
            restore_process = subprocess.run(  # noqa: S603
                ["nix-store", "--restore", str(destination)],  # noqa: S607
                stdin=decompress_process.stdout,
                capture_output=True,
                text=True,
                timeout=NIX_BUILD_TIMEOUT,
            )
        except subprocess.TimeoutExpired as error:
            decompress_process.kill()
            raise NixCommandError(
                f"Cannot extract {nar_location}: timed out after "
                f"{NIX_BUILD_TIMEOUT} seconds"
            ) from error

        # Closing the pipe stops the decompression when the restore failed.
        decompress_process.stdout.close()
        decompress_error = decompress_process.stderr.read().decode()
        decompress_process.wait()

    if decompress_process.returncode or restore_process.returncode:
        extract_errors = [decompress_error.strip(), restore_process.stderr.strip()]
        extract_error = "\n".join(error for error in extract_errors if error)
        raise NixCommandError(f"Cannot extract {nar_location}: {extract_error}")

    make_writable(destination)


def collect_garbage():
    """
    Delete the Nix store paths not used by a garbage collector root, such as the
    nixpkgs and the sources fetched for a scan, so the disk usage does not grow
    across scans. The installed Nix packages are kept, as their profiles are roots.
    """
    run_nix_command(["nix-store", "--gc"], timeout=NIX_BUILD_TIMEOUT)


def combine_license_expressions(license_expressions):
    """
    Return the SPDX ``license_expressions`` combined with AND, the compound ones
    in parentheses.
    """
    if len(license_expressions) == 1:
        return license_expressions[0]

    return " AND ".join(
        f"({expression})" if " " in expression else expression
        for expression in license_expressions
    )


def convert_nixpkgs_license_expression(license_expression_spdx):
    """
    Return the ScanCode license expression of the nixpkgs SPDX
    ``license_expression_spdx``, the nixpkgs licenses without SPDX id converted
    to unknown license references.
    """
    known_license_expression_spdx = NIXOS_LICENSE_REF_REGEX.sub(
        UNKNOWN_LICENSE_REF, license_expression_spdx
    )
    return convert_spdx_expression(known_license_expression_spdx)


def create_nix_package(project, purl, metadata, commit):
    """
    Create the Nix package of the ``project`` from the nixpkgs ``metadata``, with
    the nixpkgs ``commit`` and the system it was evaluated for.
    """
    declared_license_spdx = combine_license_expressions(metadata["licenses"])
    declared_license = ""
    if declared_license_spdx:
        declared_license = convert_nixpkgs_license_expression(declared_license_spdx)

    homepage = metadata["homepage"]
    if isinstance(homepage, list):
        homepage = homepage[0] if homepage else ""

    package_data = {
        "type": purl.type,
        "namespace": purl.namespace,
        "name": purl.name,
        "version": metadata["version"] or purl.version,
        "declared_license_expression": declared_license,
        "declared_license_expression_spdx": declared_license_spdx,
        "homepage_url": homepage,
        "description": metadata["description"],
        "datasource_id": "nixpkgs_meta",
        "extra_data": {
            "nixpkgs_commit": commit,
            "system": purl.qualifiers["system"],
        },
    }
    return pipes.update_or_create_package(project, package_data)


def add_resources_to_package(package, resource_qs, batch_size=2000):
    """Assign the ``resource_qs`` resources to the ``package``, by batches."""
    through_model = package.codebase_resources.through
    resource_ids = resource_qs.values_list("id", flat=True).iterator()

    while batch := list(islice(resource_ids, batch_size)):
        through_model.objects.bulk_create(
            [
                through_model(
                    discoveredpackage_id=package.pk,
                    codebaseresource_id=resource_id,
                )
                for resource_id in batch
            ],
            ignore_conflicts=True,
        )


def scan_undeployed_from_files(project, progress_logger=None):
    """
    Scan the ``from/`` files not deployed in the binary, keeping their
    ``not-deployed`` status. The license check needs the whole source, including
    the legal files that are usually not deployed.
    """
    undeployed_files = (
        project.codebaseresources.files()
        .from_codebase()
        .filter(status=flag.NOT_DEPLOYED)
    )
    undeployed_file_ids = list(undeployed_files.values_list("id", flat=True))

    scancode.scan_for_files(project, undeployed_files, progress_logger=progress_logger)
    project.codebaseresources.filter(
        id__in=undeployed_file_ids, status=flag.SCANNED
    ).update(status=flag.NOT_DEPLOYED)


def get_base_license_key(license_key):
    """Return the ``license_key`` without its "or later" suffix."""
    if or_later_match := OR_LATER_LICENSE_KEY_REGEX.fullmatch(license_key):
        return or_later_match.group("base_key")
    return license_key


def get_uncovered_license_keys(project, declared_license_expression):
    """
    Return the sorted license keys detected in the ``from/`` source that are not
    part of the ``declared_license_expression``. A license and its "or later"
    variant cover each other, as the GPL text of a COPYING file is detected
    without the "or later" notice of the source headers.
    """
    licensing = Licensing()
    declared_keys = set(licensing.license_keys(declared_license_expression))

    from_resources = project.codebaseresources.from_codebase().has_license_expression()
    detected_expressions = from_resources.values_list(
        "detected_license_expression", flat=True
    ).distinct()

    detected_keys = set()
    for detected_expression in detected_expressions.iterator():
        detected_keys.update(licensing.license_keys(detected_expression))

    declared_base_keys = {get_base_license_key(key) for key in declared_keys}
    return sorted(
        key
        for key in detected_keys - IGNORED_LICENSE_KEYS
        if get_base_license_key(key) not in declared_base_keys
    )

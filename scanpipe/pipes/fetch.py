# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

import cgi
import json
import logging
import os
import re
import tempfile
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlparse

import requests
from commoncode import command
from commoncode.hash import multi_checksums
from commoncode.text import python_safe_name
from plugincode.location_provider import get_location

from scanpipe import pipes

logger = logging.getLogger("scanpipe.pipes")

Download = namedtuple("Download", "uri directory filename path size sha1 md5")


def fetch_http(uri, to=None):
    """
    Download a given `uri` in a temporary directory and return the directory's
    path.
    """
    response = requests.get(uri)

    if response.status_code != 200:
        raise requests.RequestException

    content_disposition = response.headers.get("content-disposition", "")
    _, params = cgi.parse_header(content_disposition)
    filename = params.get("filename")
    if not filename:
        # Using `response.url` in place of provided `Scan.uri` since the former
        # will be more accurate in case of HTTP redirect.
        filename = Path(urlparse(response.url).path).name

    download_directory = to or tempfile.mkdtemp()
    output_file = Path(download_directory, filename)

    file_content = response.content
    with open(output_file, "wb") as f:
        f.write(file_content)

    checksums = multi_checksums(output_file, ("md5", "sha1"))

    return Download(
        uri=uri,
        directory=download_directory,
        filename=filename,
        path=output_file,
        size=len(file_content),
        sha1=checksums["sha1"],
        md5=checksums["md5"],
    )


class FetchDockerImageError(Exception):
    pass


# key of a plugin-provided location
FETCHCODE_SKOPEO_BINDIR = "fetchcode_container.skopeo.bindir"

FETCHCODE_SKOPEO_PATH_ENVVAR = "FETCHCODE_SKOPEO_PATH"


def _get_skopeo_location(_cache=[]):
    """
    Return the path to the skopeo command line executable, trying:
    - an environment variable ``FETCHCODE_SKOPEO_PATH``,
    - a plugin-provided path,
    - the system PATH.
    Raise an Exception if the skopeo binary cannot be found.
    """
    if _cache:
        return _cache[0]

    # try the environment first
    cmd_loc = os.environ.get(FETCHCODE_SKOPEO_PATH_ENVVAR)
    if cmd_loc:
        cmd_loc = Path(cmd_loc)

    # try a plugin-provided path second
    if not cmd_loc:
        bin_location = get_location(FETCHCODE_SKOPEO_BINDIR)
        if bin_location:
            cmd_loc = Path(bin_location) / "skopeo"

    # try the PATH
    if not cmd_loc:
        cmd_loc = command.find_in_path("skopeo")
        if cmd_loc:
            cmd_loc = Path(cmd_loc)

    if not cmd_loc or not os.path.isfile(cmd_loc):
        raise Exception(
            "CRITICAL: skopeo executable is not installed. "
            "Unable to continue: you need to install a valid fetchcode-container "
            "plugin with a valid executable available. "
            "OR set the FETCHCODE_SKOPEO_PATH environment variable. "
            "OR ensure that skopeo is installed and available in the PATH."
        )
    _cache.append(cmd_loc)
    return cmd_loc


def get_docker_image_platform(docker_reference):
    """
    Return a platform mapping of a docker reference.
    If there are more than one, return the first one by default.
    """
    skopeo_executable = _get_skopeo_location()
    cmd = (
        f"{skopeo_executable} inspect --insecure-policy --raw --no-creds "
        f"{docker_reference}"
    )

    logger.info(f"Fetching image os/arch data: {cmd}")
    exitcode, output = pipes.run_command(cmd)
    logger.info(output)
    if exitcode != 0:
        raise FetchDockerImageError(output)

    # Data has this shape:
    #
    # "schemaVersion": 2,
    # "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
    # "manifests": [
    #    {
    #       "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
    #       "size": 886,
    #       "digest": "sha256:305bad5caac7716b0715bfc77c8d8e19b070aa6c",
    #       "platform": {
    #          "architecture": "amd64",
    #          "os": "windows",
    #          "os.version": "10.0.19041.985"
    #       },
    #      {
    #        "digest": "sha256:973ab50414f9597fdbd2b496e089c26229196259d",
    #        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
    #        "platform": {
    #          "architecture": "arm",
    #          "os": "linux",
    #          "variant": "v7"
    #        },
    #        "size": 529

    inspection = json.loads(output)
    for manifest in inspection.get("manifests") or []:
        platform = manifest.get("platform") or {}
        if platform:
            return (
                platform.get("os") or "linux",
                platform.get("architecture") or "amd64",
                platform.get("variant") or "",
            )


def fetch_docker_image(docker_reference, to=None):
    """
    Fetch a docker image from the provided Docker image `docker_reference`
    docker:// reference URL. Return a `download` object.

    Docker references are documented here:
    https://github.com/containers/skopeo/blob/0faf16017/docs/skopeo.1.md#image-names
    """

    whitelist = r"^docker://[a-zA-Z0-9_.:/@-]+$"
    if not re.match(whitelist, docker_reference):
        raise ValueError("Invalid Docker reference.")

    name = python_safe_name(docker_reference.replace("docker://", ""))
    filename = f"{name}.tar"
    download_directory = to or tempfile.mkdtemp()
    output_file = Path(download_directory, filename)
    target = f"docker-archive:{output_file}"

    skopeo_executable = _get_skopeo_location()
    platform_args = []
    platform = get_docker_image_platform(docker_reference)
    if platform:
        os, arch, variant = platform
        if os:
            platform_args.append(f"--override-os={os}")
        if arch:
            platform_args.append(f"--override-arch={arch}")
        if variant:
            platform_args.append(f"--override-variant={variant}")
    platform_args = " ".join(platform_args)

    cmd = (
        f"{skopeo_executable} copy --insecure-policy "
        f"{platform_args} {docker_reference} {target}"
    )
    logger.info(f"Fetching image with: {cmd}")
    exitcode, output = pipes.run_command(cmd)
    logger.info(output)
    if exitcode != 0:
        raise FetchDockerImageError(output)

    checksums = multi_checksums(output_file, ("md5", "sha1"))

    return Download(
        uri=docker_reference,
        directory=download_directory,
        filename=filename,
        path=output_file,
        size=output_file.stat().st_size,
        sha1=checksums["sha1"],
        md5=checksums["md5"],
    )


def _get_fetcher(url):
    """Return the fetcher function based on the provided `url`."""
    if url.startswith("docker://"):
        return fetch_docker_image
    return fetch_http


def fetch_urls(urls):
    """
    Fetch provided `urls` list.
    The `urls` can also be provided as a string containing one URL per line.
    Return the fetched URLs as `downloads` objects and a list of `errors`.
    """
    downloads = []
    errors = []

    if isinstance(urls, str):
        urls = [url.strip() for url in urls.split()]

    for url in urls:
        fetcher = _get_fetcher(url)
        logger.info(f'Fetching "{url}" using {fetcher.__name__}')
        try:
            downloaded = fetcher(url)
        except Exception:
            errors.append(url)
        else:
            downloads.append(downloaded)

    return downloads, errors

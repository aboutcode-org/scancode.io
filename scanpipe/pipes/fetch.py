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

import ipaddress
import json
import logging
import os
import re
import socket
import tempfile
from collections import namedtuple
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urljoin
from urllib.parse import urlparse

from django.utils.http import parse_header_parameters

import git
import requests
import urllib3
from commoncode import command
from commoncode.hash import multi_checksums
from commoncode.text import python_safe_name
from fetchcode.pypi import Pypi as PyPIFetcher
from packageurl import PackageURL
from packageurl.contrib import purl2url
from packageurl.contrib import url2purl
from plugincode.location_provider import get_location
from requests import auth as request_auth

from scanpipe.pipes import run_command_safely
from scanpipe.settings import scanpipe_settings

logger = logging.getLogger("scanpipe.pipes")

Download = namedtuple("Download", "uri directory filename path size sha1 md5")

# Time (in seconds) to wait for the server to send data before giving up.
# The ``REQUEST_CONNECTION_TIMEOUT`` defines:
# - Connect timeout: The maximum time to wait for the client to establish a connection
#   to the server.
# - Read timeout: The maximum time to wait for a server response once the connection
#   is established.
# Notes: Use caution when lowering this value, as some servers
# (e.g., https://cdn.kernel.org/) may take longer to respond to HTTP requests under
# certain conditions.
HTTP_REQUEST_TIMEOUT = 30

# Maximum number of HTTP redirects to follow when fetching a URL, re-validating
# the target of each hop with ``is_safe_url`` to prevent a safe URL from
# redirecting the request to an internal address.
MAX_REDIRECT_HOPS = 5

REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})

# Backslash and control/whitespace characters can make ``urlparse`` and the
# urllib3-based HTTP client disagree on the host part of a URL, defeating the
# ``is_safe_url`` check below.
UNSAFE_URL_CHARS_RE = re.compile(r"[\x00-\x20\x7f\\]")


def get_request_session(uri):
    """Return a Requests session setup with authentication and headers."""
    session = requests.Session()
    netloc = urlparse(uri).netloc

    if credentials := scanpipe_settings.FETCH_BASIC_AUTH.get(netloc):
        session.auth = request_auth.HTTPBasicAuth(*credentials)

    elif credentials := scanpipe_settings.FETCH_DIGEST_AUTH.get(netloc):
        session.auth = request_auth.HTTPDigestAuth(*credentials)

    if headers := scanpipe_settings.FETCH_HEADERS.get(netloc):
        session.headers.update(headers)

    return session


def fetch_http(uri, to=None):
    """
    Download a given `uri` in a temporary directory and return the directory's
    path.
    """
    response = _request_with_safe_redirects(uri, "get")

    if response.status_code != 200:
        raise requests.RequestException

    content_disposition = response.headers.get("content-disposition", "")
    _, params = parse_header_parameters(content_disposition)
    filename = params.get("filename")
    if not filename:
        # Using `response.url` in place of provided `Scan.uri` since the former
        # will be more accurate in case of HTTP redirect.
        filename = unquote(Path(urlparse(response.url).path).name)

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


def get_docker_image_platform(docker_url):
    """
    Return a platform mapping of a docker reference.
    If there are more than one, return the first one by default.
    """
    skopeo_executable = _get_skopeo_location()

    authentication_args = []
    authfile = scanpipe_settings.SKOPEO_AUTHFILE_LOCATION
    if authfile:
        authentication_args.append(f"--authfile={authfile}")

    netloc = urlparse(docker_url).netloc
    if credential := scanpipe_settings.SKOPEO_CREDENTIALS.get(netloc):
        # Username and password for accessing the registry.
        authentication_args.append(f"--creds={credential}")
    elif not authfile:
        # Access the registry anonymously.
        authentication_args.append("--no-creds")

    cmd_args = (
        str(skopeo_executable),
        "inspect",
        "--insecure-policy",
        "--raw",
        *authentication_args,
        docker_url,
    )

    logger.info(f"Fetching image os/arch data: {cmd_args}")
    output = run_command_safely(cmd_args)
    logger.info(output)

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


def fetch_docker_image(docker_url, to=None):
    """
    Fetch a docker image from the provided Docker image `docker_url`,
    using the "docker://reference" URL syntax.
    Return a `Download` object.

    Docker references are documented here:
    https://github.com/containers/skopeo/blob/0faf16017/docs/skopeo.1.md#image-names
    """
    whitelist = r"^docker://[a-zA-Z0-9_.:/@-]+$"
    if not re.match(whitelist, docker_url):
        raise ValueError("Invalid Docker reference.")

    reference = docker_url.replace("docker://", "")
    filename = f"{python_safe_name(reference)}.tar"
    download_directory = to or tempfile.mkdtemp()
    output_file = Path(download_directory, filename)
    target = f"docker-archive:{output_file}"
    skopeo_executable = _get_skopeo_location()

    platform_args = []
    if platform := get_docker_image_platform(docker_url):
        os, arch, variant = platform
        if os:
            platform_args.append(f"--override-os={os}")
        if arch:
            platform_args.append(f"--override-arch={arch}")
        if variant:
            platform_args.append(f"--override-variant={variant}")

    authentication_args = []
    if authfile := scanpipe_settings.SKOPEO_AUTHFILE_LOCATION:
        authentication_args.append(f"--authfile={authfile}")

    netloc = urlparse(docker_url).netloc
    if credential := scanpipe_settings.SKOPEO_CREDENTIALS.get(netloc):
        # Credentials for accessing the source registry.
        authentication_args.append(f"--src-creds={credential}")

    cmd_args = (
        str(skopeo_executable),
        "copy",
        "--insecure-policy",
        *platform_args,
        *authentication_args,
        docker_url,
        target,
    )
    logger.info(f"Fetching image with: {cmd_args}")
    output = run_command_safely(cmd_args)
    logger.info(output)

    checksums = multi_checksums(output_file, ("md5", "sha1"))

    return Download(
        uri=docker_url,
        directory=download_directory,
        filename=filename,
        path=output_file,
        size=output_file.stat().st_size,
        sha1=checksums["sha1"],
        md5=checksums["md5"],
    )


def fetch_git_repo(url, to=None):
    """Fetch provided git `url` as a clone and return a `Download` object."""
    download_directory = to or tempfile.mkdtemp()
    url = url.rstrip("/")
    filename = url.split("/")[-1]
    to_path = Path(download_directory) / filename
    # Disable any prompt, especially for credentials
    git_env = {"GIT_TERMINAL_PROMPT": "0"}

    git.Repo.clone_from(url=url, to_path=to_path, depth=1, env=git_env)

    return Download(
        uri=url,
        directory=download_directory,
        filename=filename,
        path=to_path,
        size="",
        sha1="",
        md5="",
    )


def fetch_package_url(url):
    """Fetch a package from the provided `url` and return a `Download` object."""
    # Ensure the provided Package URL is valid, or raise a ValueError.
    purl = PackageURL.from_string(url)

    # Resolve a Download URL using purl2url.
    if download_url := purl2url.get_download_url(url):
        return fetch_http(download_url)

    # PyPI is not supported by purl2url.
    # It requires an API call to resolve download URLs.
    if purl.type == "pypi":
        if download_url := PyPIFetcher.get_download_url(url, preferred_type="sdist"):
            return fetch_http(download_url)

    raise ValueError(f"Could not resolve a download URL for {url}.")


SCHEME_TO_FETCHER_MAPPING = {
    "http": fetch_http,
    "https": fetch_http,
    "docker": fetch_docker_image,
}


def get_fetcher(url):
    """Return the fetcher function based on the provided `url` scheme."""
    if url.startswith("git@"):
        raise ValueError("SSH 'git@' URLs are not supported. Use https:// instead.")

    if url.rstrip("/").endswith(".git"):
        return fetch_git_repo

    if url.startswith("pkg:"):
        return fetch_package_url

    # Not using `urlparse(url).scheme` for the scheme as it converts to lower case.
    scheme = url.split("://")[0]

    if fetcher := SCHEME_TO_FETCHER_MAPPING.get(scheme):
        return fetcher

    error_msg = f"URL scheme '{scheme}' is not supported."
    if scheme.lower() in SCHEME_TO_FETCHER_MAPPING:
        error_msg += f" Did you mean: '{scheme.lower()}'?"
    raise ValueError(error_msg)


def fetch_url(url):
    """Fetch provided `url` and return the result as a `Download` object."""
    fetcher = get_fetcher(url)
    logger.info(f'Fetching "{url}" using {fetcher.__name__}')
    downloaded = fetcher(url)
    return downloaded


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
        if not url:
            continue

        try:
            downloaded = fetch_url(url)
        except Exception:
            errors.append(url)
        else:
            downloads.append(downloaded)

    return downloads, errors


def is_safe_url(url):
    """
    Check that a URL does not point to a private or internal network address.
    Mitigates SSRF by ensuring the target host resolves only to public IPs.
    """
    # Reject characters that can make `urlparse` and the urllib3-based HTTP
    # client disagree on the host part of the same URL.
    if UNSAFE_URL_CHARS_RE.search(url):
        return False

    if urlparse(url).scheme not in ("http", "https"):
        return False

    # Use urllib3's own URL parser, the one `requests` relies on to pick a
    # connection host, so this check and the actual request always agree on
    # which host is being contacted.
    host = urllib3.util.parse_url(url).host
    if not host:
        return False

    # Resolve the hostname to catch internal addresses hidden behind DNS.
    # `getaddrinfo` is used instead of `gethostbyname` to also cover IPv6-only
    # records, since a client may connect over either address family.
    try:
        address_infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False

    resolved_ips = {address_info[4][0] for address_info in address_infos}
    if not resolved_ips:
        return False

    # Reject private, loopback, link-local, reserved, and multicast addresses.
    # If any resolved address is unsafe, the host is rejected since the HTTP
    # client is free to connect to any of them.
    for resolved_ip in resolved_ips:
        ip = ipaddress.ip_address(resolved_ip)
        unsafe = (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
        if unsafe:
            return False

    return True


def _request_with_safe_redirects(url, method_name):
    """
    Perform an HTTP request for `url` using the session `method_name`
    ("get" or "head"), re-validating each redirect target with `is_safe_url`
    before following it.
    Raise `requests.RequestException` if the URL, or any redirect target, is
    unsafe or if too many redirects are followed.
    """
    request_session = get_request_session(url)
    session_method = getattr(request_session, method_name)

    for _ in range(MAX_REDIRECT_HOPS + 1):
        if not is_safe_url(url):
            raise requests.RequestException(f"Unsafe URL: {url}")

        response = session_method(
            url, timeout=HTTP_REQUEST_TIMEOUT, allow_redirects=False
        )
        if response.status_code not in REDIRECT_STATUS_CODES:
            return response

        url = urljoin(url, response.headers["location"])

    raise requests.RequestException("Too many redirects.")


def check_url(url):
    """Check that a URL is safe and accessible."""
    try:
        response = _request_with_safe_redirects(url, "head")
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return False

    return True


def check_urls_availability(urls):
    """Check the safety and accessibility of a list of URLs."""
    errors = [url for url in urls if not check_url(url) if url.startswith("http")]
    return errors


def set_project_purl_from_input_url(project, input_urls):
    """Auto-fill the project PURL when the sole input is a single resolvable URL."""
    if not project.purl and input_urls and len(input_urls) == 1:
        if purl := url2purl.get_purl(input_urls[0]):
            project.update(purl=str(purl))

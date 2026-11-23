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

import base64
import ipaddress
import json
import logging
import os
import re
import socket
import tempfile
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urljoin
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError
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


def is_unsafe_ip_address(ip_address):
    """
    Return True if ``ip_address`` is not a public unicast address: private,
    loopback, link-local, shared (CGNAT), reserved, or multicast.
    """
    address = ipaddress.ip_address(ip_address)
    # Older Python versions do not classify an IPv4-mapped IPv6 address, such as
    # ``::ffff:127.0.0.1``, from its IPv4 address.
    if ipv4_mapped_address := getattr(address, "ipv4_mapped", None):
        address = ipv4_mapped_address

    return not address.is_global or address.is_multicast


def parse_allowed_private_host(allowed_entry):
    """
    Return the ``(host, port)`` pair of an ``ALLOWED_PRIVATE_HOSTS`` entry, the port
    is None for an entry without port.
    Raise ImproperlyConfigured if the entry is not a ``host`` or ``host:port``.
    """
    error_message = (
        f'Invalid SCANCODEIO_ALLOWED_PRIVATE_HOSTS entry: "{allowed_entry}". '
        f"Use host or host:port entries, without scheme or path."
    )
    # A scheme, path, query, or credentials would be parsed as another host.
    if any(character in allowed_entry for character in "/?#@"):
        raise ImproperlyConfigured(error_message)

    try:
        parsed_entry = urllib3.util.parse_url(f"//{allowed_entry}")
    except urllib3.exceptions.LocationParseError as error:
        raise ImproperlyConfigured(error_message) from error

    if not parsed_entry.host:
        raise ImproperlyConfigured(error_message)

    return parsed_entry.host.strip("[]").lower(), parsed_entry.port


def parse_purldb_address(purldb_url):
    """
    Return the ``(host, port)`` pair of the ``PURLDB_URL`` setting.
    Raise ImproperlyConfigured if it is not an HTTP URL.
    """
    parsed_url = urllib3.util.parse_url(purldb_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.host:
        raise ImproperlyConfigured(
            f'Invalid PURLDB_URL setting: "{purldb_url}". '
            f"Use an http:// or https:// URL."
        )

    return parsed_url.host.strip("[]").lower(), get_url_port(parsed_url)


def get_allowed_private_addresses():
    """
    Return the ``(host, port)`` pairs of the ``ALLOWED_PRIVATE_HOSTS`` setting, the
    port is None for an entry without port, and of the ``PURLDB_URL`` setting.
    """
    allowed_addresses = {
        parse_allowed_private_host(allowed_entry)
        for allowed_entry in scanpipe_settings.ALLOWED_PRIVATE_HOSTS
        if allowed_entry
    }

    # The PurlDB scan worker sends the scan results to the webhook URL provided by
    # the configured PurlDB service, usually on a private network.
    if purldb_url := getattr(settings, "PURLDB_URL", ""):
        allowed_addresses.add(parse_purldb_address(purldb_url))

    return allowed_addresses


def is_allowed_private_host(host, port):
    """
    Return True if ``host`` and ``port`` are listed in the ``ALLOWED_PRIVATE_HOSTS``
    setting. An entry without port only allows the default HTTP and HTTPS ports.
    """
    host = host.strip("[]").lower()
    allowed_addresses = get_allowed_private_addresses()
    if (host, port) in allowed_addresses:
        return True

    is_default_port = port in urllib3.connection.port_by_scheme.values()
    return is_default_port and (host, None) in allowed_addresses


def get_url_port(parsed_url):
    """Return the port of the ``parsed_url``, or the default port of its scheme."""
    return parsed_url.port or urllib3.connection.port_by_scheme[parsed_url.scheme]


def get_public_ip_addresses(host):
    """
    Return the IP addresses ``host`` resolves to, or an empty list if it does not
    resolve or if any of its addresses is not public.
    """
    # `getaddrinfo` is used instead of `gethostbyname` to also cover IPv6-only
    # records, since a client may connect over either address family.
    try:
        address_infos = socket.getaddrinfo(host.strip("[]"), None)
    except (socket.gaierror, UnicodeError):
        return []

    ip_addresses = list(
        dict.fromkeys(address_info[4][0] for address_info in address_infos)
    )
    # If any resolved address is unsafe, the host is rejected since the client is
    # free to connect to any of them.
    if any(is_unsafe_ip_address(ip_address) for ip_address in ip_addresses):
        return []

    return ip_addresses


class PublicAddressConnectionMixin:
    """
    Connect only to the public addresses of the host, validated on the same DNS
    resolution as the connection, or to a host of ``ALLOWED_PRIVATE_HOSTS``.
    Through a proxy, this applies to the proxy address, and the proxy resolves the
    target host.
    """

    def _new_conn(self):
        host = self._dns_host
        if is_allowed_private_host(host, self.port):
            return super()._new_conn()

        ip_addresses = get_public_ip_addresses(host)
        if not ip_addresses:
            raise urllib3.exceptions.NewConnectionError(
                self, f"{host} does not resolve to public addresses only."
            )

        connection_error = None
        for ip_address in ip_addresses:
            # The host name is restored for the TLS SNI, the certificate check, and
            # the Host header.
            self._dns_host = ip_address
            try:
                return super()._new_conn()
            except (
                urllib3.exceptions.NewConnectionError,
                urllib3.exceptions.ConnectTimeoutError,
            ) as error:
                connection_error = error
            finally:
                self._dns_host = host

        raise connection_error


class PublicAddressHTTPConnection(
    PublicAddressConnectionMixin, urllib3.connection.HTTPConnection
):
    pass


class PublicAddressHTTPSConnection(
    PublicAddressConnectionMixin, urllib3.connection.HTTPSConnection
):
    pass


class PublicAddressHTTPConnectionPool(urllib3.connectionpool.HTTPConnectionPool):
    ConnectionCls = PublicAddressHTTPConnection


class PublicAddressHTTPSConnectionPool(urllib3.connectionpool.HTTPSConnectionPool):
    ConnectionCls = PublicAddressHTTPSConnection


PUBLIC_ADDRESS_POOL_CLASSES_BY_SCHEME = {
    "http": PublicAddressHTTPConnectionPool,
    "https": PublicAddressHTTPSConnectionPool,
}


class PublicAddressHTTPAdapter(requests.adapters.HTTPAdapter):
    """Requests adapter connecting only through ``PublicAddressConnectionMixin``."""

    def init_poolmanager(self, *args, **pool_kwargs):
        super().init_poolmanager(*args, **pool_kwargs)
        self.poolmanager.pool_classes_by_scheme = PUBLIC_ADDRESS_POOL_CLASSES_BY_SCHEME

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_manager = super().proxy_manager_for(proxy, **proxy_kwargs)
        proxy_manager.pool_classes_by_scheme = PUBLIC_ADDRESS_POOL_CLASSES_BY_SCHEME
        return proxy_manager


class NoCredentialsAuth(request_auth.AuthBase):
    """
    Send the request without credentials: without an explicit authentication,
    Requests applies the credentials of the netrc file.
    """

    def __call__(self, prepared_request):
        return prepared_request


def get_request_session(uri, include_credentials=True):
    """
    Return a Requests session connecting only to public addresses or allowed
    private hosts, setup with the authentication and headers of the ``uri`` host
    when ``include_credentials`` is True.
    """
    session = requests.Session()
    public_address_adapter = PublicAddressHTTPAdapter()
    session.mount("http://", public_address_adapter)
    session.mount("https://", public_address_adapter)

    if not include_credentials:
        session.auth = NoCredentialsAuth()
        return session

    netloc = urlparse(uri).netloc

    if credentials := scanpipe_settings.FETCH_BASIC_AUTH.get(netloc):
        session.auth = request_auth.HTTPBasicAuth(*credentials)

    elif credentials := scanpipe_settings.FETCH_DIGEST_AUTH.get(netloc):
        session.auth = request_auth.HTTPDigestAuth(*credentials)

    if headers := scanpipe_settings.FETCH_HEADERS.get(netloc):
        session.headers.update(headers)

    return session


def get_safe_filename(filename):
    """
    Return the base name of the ``filename`` provided by the server, so a
    download cannot be written outside of its download directory.
    """
    safe_filename = Path(filename).name
    if safe_filename in ("", ".", ".."):
        raise ValueError(f"Invalid download filename: {filename}")
    return safe_filename


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
    output_file = Path(download_directory, get_safe_filename(filename))

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


@contextmanager
def skopeo_authfile(docker_url):
    """
    Yield the location of the skopeo authentication file for the registry of the
    ``docker_url``, or an empty string for an anonymous access.

    The ``SKOPEO_CREDENTIALS`` of the registry are written to a temporary file,
    deleted on exit: as a command argument, they would be visible to the other
    processes of the server.
    """
    registry = urlparse(docker_url).netloc
    credential = scanpipe_settings.SKOPEO_CREDENTIALS.get(registry)
    if not credential:
        yield scanpipe_settings.SKOPEO_AUTHFILE_LOCATION
        return

    encoded_credential = base64.b64encode(credential.encode()).decode()
    authfile_data = {"auths": {registry: {"auth": encoded_credential}}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as authfile:
        json.dump(authfile_data, authfile)
        authfile.flush()
        yield authfile.name


DOCKER_HUB_REGISTRY = "docker.io"


def get_docker_registry(docker_url):
    """
    Return the registry host, with its port, of the ``docker_url`` reference.
    As in the Docker reference syntax, the first component is the registry when it
    contains a "." or a ":", is "localhost", or has uppercase letters.
    Otherwise, the registry is Docker Hub.
    """
    reference = docker_url.removeprefix("docker://")
    first_component, separator, _remainder = reference.partition("/")
    has_registry = bool(separator) and (
        any(character in first_component for character in ".:")
        or first_component == "localhost"
        or first_component != first_component.lower()
    )
    if has_registry:
        return first_component
    return DOCKER_HUB_REGISTRY


def validate_docker_registry(docker_url):
    """
    Raise a ValueError if the registry of the ``docker_url`` reference does not
    resolve to public addresses only, and is not an allowed private host.
    """
    registry = get_docker_registry(docker_url)
    # Skopeo resolves the host again and follows the registry redirects: this check
    # rejects a private registry, not a DNS rebinding.
    if "@" in registry or not is_safe_url(f"https://{registry}/"):
        raise ValueError(f"Unsafe Docker registry: {registry}")


def get_docker_image_platform(docker_url):
    """
    Return a platform mapping of a docker reference.
    If there are more than one, return the first one by default.
    """
    skopeo_executable = _get_skopeo_location()

    with skopeo_authfile(docker_url) as authfile:
        # Access the registry anonymously without an authentication file.
        authentication_arg = f"--authfile={authfile}" if authfile else "--no-creds"
        cmd_args = (
            str(skopeo_executable),
            "inspect",
            "--insecure-policy",
            "--raw",
            authentication_arg,
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

    validate_docker_registry(docker_url)

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

    with skopeo_authfile(docker_url) as authfile:
        authentication_args = [f"--authfile={authfile}"] if authfile else []
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


def get_curl_resolve_entry(url):
    """
    Return a curl ``HOST:PORT:ADDRESSES`` resolve entry pinning the host of ``url``
    to its public addresses, or an empty string for an allowed private host.
    Raise a ValueError if the host does not resolve to public addresses only.
    """
    parsed_url = urllib3.util.parse_url(url)
    port = get_url_port(parsed_url)
    if is_allowed_private_host(parsed_url.host, port):
        return ""

    ip_addresses = get_public_ip_addresses(parsed_url.host)
    if not ip_addresses:
        raise ValueError(f"Unsafe URL: {url}")

    bracketed_addresses = [
        f"[{ip_address}]" if ":" in ip_address else ip_address
        for ip_address in ip_addresses
    ]
    return f"{parsed_url.host}:{port}:{','.join(bracketed_addresses)}"


def get_git_environment(url):
    """
    Return the environment variables to clone the git ``url`` without prompt nor
    redirect, connecting only to the validated addresses of its host.
    Raise a ValueError if the URL is not an HTTP URL to a public or allowed host.
    """
    # Same SSRF protection as ``fetch_http``: no private or internal address.
    if not is_safe_url(url):
        raise ValueError(f"Unsafe URL: {url}")

    git_config = {
        # Do not follow the redirects: their target is not checked by ``is_safe_url``
        # and could be an internal address.
        "http.followRedirects": "false",
    }
    # Git resolves the host again: it connects to the validated addresses instead.
    if resolve_entry := get_curl_resolve_entry(url):
        git_config["http.curloptResolve"] = resolve_entry

    git_environment = {
        # Disable any prompt, especially for credentials
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_COUNT": str(len(git_config)),
    }
    for index, (config_key, config_value) in enumerate(git_config.items()):
        git_environment[f"GIT_CONFIG_KEY_{index}"] = config_key
        git_environment[f"GIT_CONFIG_VALUE_{index}"] = config_value

    return git_environment


def fetch_git_repo(url, to=None):
    """Fetch provided git `url` as a clone and return a `Download` object."""
    git_env = get_git_environment(url)

    download_directory = to or tempfile.mkdtemp()
    url = url.rstrip("/")
    filename = url.split("/")[-1]
    to_path = Path(download_directory) / filename

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


def fetch_package_url(url, to=None):
    """Fetch a package from the provided `url` and return a `Download` object."""
    # Ensure the provided Package URL is valid, or raise a ValueError.
    purl = PackageURL.from_string(url)

    # Resolve a Download URL using purl2url.
    if download_url := purl2url.get_download_url(url):
        return fetch_http(download_url, to=to)

    # PyPI is not supported by purl2url.
    # It requires an API call to resolve download URLs.
    if purl.type == "pypi":
        if download_url := PyPIFetcher.get_download_url(url, preferred_type="sdist"):
            return fetch_http(download_url, to=to)

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

    # The git:// protocol is not encrypted, and its URLs cannot be checked against
    # internal addresses by ``is_safe_url``, which only supports HTTP.
    if url.startswith("git://"):
        error_msg = "Unencrypted git:// URLs are not supported. Use https:// instead."
        raise ValueError(error_msg)

    if url.rstrip("/").endswith(".git"):
        # Git also clones a local path or a file:// URL, that is any repository of
        # the server, so only the HTTP URLs are cloned.
        if not url.startswith(("http://", "https://")):
            raise ValueError("Only http:// and https:// Git URLs are supported.")
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


def fetch_url(url, to=None):
    """Fetch provided `url` and return the result as a `Download` object."""
    fetcher = get_fetcher(url)
    logger.info(f'Fetching "{url}" using {fetcher.__name__}')
    downloaded = fetcher(url, to=to)
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
    Mitigates SSRF by ensuring the target host resolves only to public IPs, unless
    it is listed in the ``ALLOWED_PRIVATE_HOSTS`` setting.
    """
    # Reject characters that can make `urlparse` and the urllib3-based HTTP
    # client disagree on the host part of the same URL.
    if UNSAFE_URL_CHARS_RE.search(url):
        return False

    # Use urllib3's own URL parser, the one `requests` relies on to pick a
    # connection host, so this check and the actual request always agree on
    # which host is being contacted.
    try:
        parsed_url = urllib3.util.parse_url(url)
    except urllib3.exceptions.LocationParseError:
        return False

    if parsed_url.scheme not in ("http", "https") or not parsed_url.host:
        return False

    if is_allowed_private_host(parsed_url.host, get_url_port(parsed_url)):
        return True

    # Resolve the hostname to catch internal addresses hidden behind DNS.
    return bool(get_public_ip_addresses(parsed_url.host))


def validate_safe_url(url):
    """Raise a ValidationError if ``url`` is not safe, see ``is_safe_url``."""
    if not is_safe_url(url):
        raise ValidationError(
            "Enter an http:// or https:// URL whose host resolves to public "
            "addresses only. Private hosts must be listed in the "
            "SCANCODEIO_ALLOWED_PRIVATE_HOSTS setting."
        )


def send_safe_request(url, method_name, include_credentials=True, **request_kwargs):
    """
    Send a single ``method_name`` request to ``url``, connecting only to public
    addresses or allowed private hosts.
    Raise `requests.RequestException` if the URL is unsafe.
    """
    if not is_safe_url(url):
        raise requests.RequestException(f"Unsafe URL: {url}")

    with get_request_session(url, include_credentials) as request_session:
        session_method = getattr(request_session, method_name)
        # A redirect could lead the request from the target to an internal service.
        return session_method(url, allow_redirects=False, **request_kwargs)


def _request_with_safe_redirects(url, method_name):
    """
    Perform an HTTP request for `url` using the session `method_name`
    ("get" or "head"), re-validating each redirect target with `is_safe_url`
    before following it.
    Raise `requests.RequestException` if the URL, or any redirect target, is
    unsafe or if too many redirects are followed.
    """
    has_used_https = False

    for _ in range(MAX_REDIRECT_HOPS + 1):
        is_https = urlparse(url).scheme == "https"
        # The credentials are those of each hop host, and are not sent over HTTP
        # once a hop used HTTPS.
        is_downgrade = has_used_https and not is_https
        has_used_https = has_used_https or is_https

        response = send_safe_request(
            url,
            method_name,
            include_credentials=not is_downgrade,
            timeout=HTTP_REQUEST_TIMEOUT,
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

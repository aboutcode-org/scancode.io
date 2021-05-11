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
import logging
import tempfile
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlparse

import requests
from commoncode.hash import multi_checksums

from scanpipe import pipes

logger = logging.getLogger("scanpipe.pipes")


Download = namedtuple("Download", "uri directory filename path size sha1 md5")


def download(uri, to=None):
    """
    Downloads the given `uri` in a temporary directory and returns that directory path.
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


def fetch_docker_image(uri, to=None):
    """
    Fetch a docker image from the provided image `name`.
    Requires the docker engine to be installed on the machine.
    """
    name = pipes.remove_prefix(uri, "docker://")

    exitcode, output = pipes.run_command(f"docker pull {name}")
    logger.info(output)
    if exitcode != 0:
        raise FetchDockerImageError(output)

    download_directory = to or tempfile.mkdtemp()
    filename = f"{name}.tar"
    output_file = Path(download_directory, filename)

    exitcode, output = pipes.run_command(f"docker save {name} --output {output_file}")
    logger.info(output)
    if exitcode != 0:
        raise FetchDockerImageError(output)

    checksums = multi_checksums(output_file, ("md5", "sha1"))

    return Download(
        uri=uri,
        directory=download_directory,
        filename=filename,
        path=output_file,
        size=output_file.stat().st_size,
        sha1=checksums["sha1"],
        md5=checksums["md5"],
    )


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
        fetcher = fetch_docker_image if url.startswith("docker://") else downloads
        logger.info(f'Fetching "{url}" using {fetcher.__name__}')
        try:
            downloaded = fetcher(url)
        except Exception:
            errors.append(url)
        else:
            downloads.append(downloaded)

    return downloads, errors

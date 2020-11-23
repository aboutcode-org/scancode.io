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
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlparse

from django.apps import apps
from django.utils import timezone

import requests
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from commoncode.hash import multi_checksums
from scancode_config import __version__ as scancode_version
from textcode.analysis import numbered_text_lines

tasks_logger = get_task_logger(__name__)
app_config = apps.get_app_config("scanner")

SCAN_PROCESSES = 3
SCAN_MAX_IN_MEMORY = 100_000
DOWNLOAD_SIZE_THRESHOLD = 26_214_400  # 25MB


def log_info(message, scan_pk):
    tasks_logger.info(f"Scan[{scan_pk}] {message}")


def get_bin_executable(filename):
    return str(Path(sys.executable).parent / filename)


def run_command(cmd):
    """
    Return (exitcode, output) of executing `cmd` in a shell.
    `cmd` can be provided as a string or as a list of arguments.
    """
    if isinstance(cmd, list):
        cmd = " ".join(cmd)

    exitcode, output = subprocess.getstatusoutput(cmd)
    return exitcode, output


Download = namedtuple("Download", "directory filename size sha1 md5")


def download(uri):
    """
    Downloads the given `uri` in a temporary directory and returns that
    directory path.
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
        filename = os.path.basename(urlparse(response.url).path)

    download_directory = tempfile.mkdtemp()
    download_file = Path(download_directory, filename)

    file_content = response.content
    with open(download_file, "wb") as f:
        f.write(file_content)

    checksums = multi_checksums(download_file, ("md5", "sha1"))

    return Download(
        directory=download_directory,
        filename=filename,
        size=len(file_content),
        sha1=checksums["sha1"],
        md5=checksums["md5"],
    )


def get_scan_input_location(download_location):
    """
    Return the input location for the ScanCode process, based on the
    given `download_location` directory content.

    If the `download_location` contains only a single downloaded file,
    the given `download_location` is returned.

    If the`download_location` contains the downloaded file and its related
    "-extract" directory, that directory is returned as the scan input location.

    Any other cases will return False.
    """
    path = Path(download_location)
    if not path.is_dir():
        return False

    directory_content_len = len(list(path.iterdir()))
    extract_directory = list(path.glob("*-extract"))

    if directory_content_len == 1:
        return download_location

    elif directory_content_len == 2 and extract_directory:
        return extract_directory[0]

    return False


def get_scancode_compatible_content(location):
    """
    Return the content of the file at `location` using the ScanCode functions
    to ensure compatibility and consistency between outputs.
    """
    return "".join(line for _, line in numbered_text_lines(location))


def dump_key_files_data(key_files, source_directory, output_location):
    """
    Collect and inject the content of each key files and dump the data in
    the `output_location` file.
    """
    if not key_files:
        return

    for key_file in key_files:
        path = key_file.get("path")

        # Single file in the download directory
        if source_directory.endswith(path.split("/")[0]):
            path = key_file.get("name")

        full_path = Path(source_directory, path)
        if full_path.is_file():
            key_file["content"] = get_scancode_compatible_content(str(full_path))

    with open(output_location, "w") as f:
        f.write(json.dumps(key_files))


def run_scancode(download_location, output_file):
    """
    Run the scanning task where `location` is the path containing the archive.
    """
    extractcode_args = [
        get_bin_executable("extractcode"),
        shlex.quote(str(download_location)),
    ]
    extract_exitcode, extract_output = run_command(extractcode_args)

    scan_input = get_scan_input_location(download_location)
    if not scan_input:
        return 1, "Scan input could not be determined."

    scancode_args = [
        get_bin_executable("scancode"),
        shlex.quote(str(scan_input)),
        "--classify",
        "--consolidate",
        "--copyright",
        "--email",
        "--info",
        "--is-license-text",
        "--license",
        "--license-clarity-score",
        "--license-text",
        "--package",
        "--summary",
        "--summary-key-files",
        "--url",
        f"--processes {SCAN_PROCESSES}",
        f"--max-in-memory {SCAN_MAX_IN_MEMORY}",
        f"--json-pp {output_file}",
    ]
    scan_exitcode, scan_output = run_command(scancode_args)

    exitcode = extract_exitcode + scan_exitcode
    output = "\n".join([extract_output, scan_output])
    return exitcode, output


@shared_task(bind=True)
def download_and_scan(self, scan_pk, run_subscriptions=True):
    task_id = self.request.id
    log_info(f"Enter tasks.download_and_scan Task.id={task_id}", scan_pk)

    scan_model = apps.get_model("scanner", "Scan")
    scan = scan_model.objects.get(pk=scan_pk)
    scan.reset_values()
    scan.scancode_version = scancode_version
    scan.set_task_started(task_id)

    log_info(f"Download {scan.uri}", scan_pk)
    try:
        downloaded = download(scan.uri)
    except Exception as e:
        log_info(f"Download error: {e}", scan_pk)
        scan.task_exitcode = 404
        scan.task_output = str(e) or "Not found"
        scan.task_end_date = timezone.now()
        scan.save()
        return

    scan.filename = downloaded.filename
    scan.sha1 = downloaded.sha1
    scan.md5 = downloaded.md5
    scan.size = downloaded.size
    scan.save()

    queue = "default"
    if downloaded.size > DOWNLOAD_SIZE_THRESHOLD:
        queue = "priority.low"
        log_info(
            f"Download size > {DOWNLOAD_SIZE_THRESHOLD}, sending to {queue} queue",
            scan_pk,
        )

    scan_task.apply_async(
        args=[scan_pk, downloaded.directory, run_subscriptions],
        queue=queue,
    )


@shared_task(bind=True)
def scan_task(self, scan_pk, directory, run_subscriptions):
    task_id = self.request.id
    log_info(f"Scan {directory} Task.id={task_id}", scan_pk)

    scan_model = apps.get_model("scanner", "Scan")
    scan = scan_model.objects.get(pk=scan_pk)
    scan.output_file = str(scan.work_path / f"scan_{scancode_version}.json")
    # Update the task_id but keep the task_start_date from previous task
    scan.task_id = task_id
    scan.save()

    try:
        exitcode, output = run_scancode(directory, scan.output_file)
        key_files_data = scan.get_key_files_data()
        dump_key_files_data(key_files_data, directory, scan.key_files_output_file)
        scan.summary = scan.get_summary_from_output()
    except SoftTimeLimitExceeded:
        log_info(f"SoftTimeLimitExceeded", scan_pk)
        exitcode, output = 4, "SoftTimeLimitExceeded"
    except Exception as e:
        log_info(f"Scan error: {e}", scan_pk)
        exitcode, output = 3, str(e)
    finally:
        log_info("Remove temporary files", scan_pk)
        # Always cleanup the temporary files even if an exception if raised
        shutil.rmtree(directory, ignore_errors=True)

    log_info("Update Scan instance with exitcode, output, and end_date", scan_pk)
    # Do not refresh the scan instance since `scan.summary` is not saved yet
    scan.set_task_ended(exitcode, output, refresh_first=False)

    if run_subscriptions and exitcode < 3 and scan.has_subscriptions():
        log_info("Run subscriptions", scan_pk)
        scan.run_subscriptions()

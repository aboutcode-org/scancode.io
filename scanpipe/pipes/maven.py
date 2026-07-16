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
import logging
from urllib.parse import urlparse

import requests
from packageurl import PackageURL
from packageurl.contrib import purl2url

from scanpipe.pipes import fetch
from scanpipe.pipes import scancode

logger = logging.getLogger(__name__)


def check_input_and_return_purl(project):
    """Validate the input and return a maven PURL."""
    input_sources = project.inputsources.all()
    if len(input_sources) != 1:
        error_msg = "Only 1 maven purl is accepted."
        raise ValueError(error_msg)
    project_input = str(input_sources[0])
    input_purl = PackageURL.from_string(project_input)

    if input_purl.type != "maven":
        error_msg = "Only maven purl is supported."
        raise ValueError(error_msg)
    # Should we hande all available versions if no version is provided?
    # Making the version as required for now
    if not input_purl.version:
        error_msg = "Version is required."
        raise ValueError(error_msg)

    purl = PackageURL(
        type=input_purl.type,
        namespace=input_purl.namespace,
        name=input_purl.name,
        version=input_purl.version,
    )

    return purl


def fetch_inputs(purl):
    """Fetch the binary and source for the given input purl"""
    purl_str = PackageURL.to_string(purl)

    purl_bin_path = fetch_path(purl_str, "binary")
    purl_src_path = fetch_path(f"{purl_str}?classifier=sources", "source")

    if not purl_bin_path and not purl_src_path:
        err_msg = f"No source or binary could be resolved for {purl}."
        raise ValueError(err_msg)

    return [purl_src_path], [purl_bin_path]


def fetch_path(url, package_type):
    """Fetch the url and return the location of the fetched tarball"""
    try:
        return fetch.fetch_url(url=url).path
    except Exception as e:
        logger.info("Failed to fetch %s package: %s", package_type, e)
        return None


def fetch_and_scan_remote_pom(input_purl, scan_output_location):
    """Fetch the .pom file from from maven.org if not present in codebase."""
    with open(scan_output_location) as file:
        data = json.load(file)
        # Return and do nothing if data has pom.xml
        for file in data["files"]:
            if "pom.xml" in file["path"]:
                return []
    packages = data.get("packages", [])

    pom_url = get_pom_url(input_purl)
    if not pom_url:
        return ["Failed to resolve POM URL."]
    pom_file = download_pom_file(pom_url)
    if not pom_file:
        return ["Failed to download the POM file."]
    scanning_errors = scan_pom_file(pom_file)

    scanned_pom_packages, scanned_dependencies = update_datafile_paths(pom_file)

    updated_packages = packages + scanned_pom_packages
    # Replace/Update the package and dependencies section
    data["packages"] = updated_packages
    data["dependencies"] = scanned_dependencies
    with open(scan_output_location, "w") as file:
        json.dump(data, file, indent=2)
    return scanning_errors


def get_pom_url(input_purl):
    """Construct a Maven POM URL from the input purl."""
    purl_str = PackageURL.to_string(input_purl)
    input_source_url = purl2url.get_download_url(purl_str)
    if not input_source_url:
        return ""

    parsed_url = urlparse(input_source_url)
    maven_hosts = {
        "repo1.maven.org",
        "repo.maven.apache.org",
        "maven.google.com",
    }
    pom_url = ""
    if parsed_url.netloc in maven_hosts:
        base_url = input_source_url.rsplit("/", 1)[0]
        pom_url = f"{base_url}/{input_purl.name}-{input_purl.version}.pom"
    return pom_url


def download_pom_file(pom_url):
    """Fetch the pom file from the input pom_url"""
    # PO: Could we use fetchcode to fetch instead? Yes, we could, but
    # the issue is do we want to. Following is the code if we switch to
    # fetchcode which seems making things complicated, OR we can move
    # the "fetch_http" to fetchcode and use it.
    """
    import os
    import fetchcode
    downloaded_pom = fetchcode.fetch(pom_url)
    location = str(downloaded_pom.location)
    path = location + ".pom"
    # The fetch function from fetchcode save the file as /tmp/name
    # without an extension. We need to add the ".pom" extension so that
    # the package scan can work properly for this file.
    os.rename(location, path)
    """
    try:
        downloaded_pom = fetch.fetch_http(pom_url)
    except requests.RequestException:
        # Return an empty dictionary
        return {}
    path = str(downloaded_pom.path)
    pom_file_dict = {}
    pom_file_dict["pom_file_path"] = path
    pom_file_dict["output_path"] = path + "-output.json"
    pom_file_dict["pom_url"] = pom_url
    return pom_file_dict


def scan_pom_file(pom_file_dict):
    """Fetch and scan the pom file from the input pom_urls"""
    scan_errors = []
    pom_file_path = pom_file_dict.get("pom_file_path", "")
    scanned_pom_output_path = pom_file_dict.get("output_path", "")

    # Run a package scan on the fetched pom.xml
    scanning_errors = scancode.run_scan(
        location=pom_file_path,
        output_file=scanned_pom_output_path,
        run_scan_args={
            "package": True,
        },
    )
    if scanning_errors:
        scan_errors.append(scanning_errors)
    return scan_errors


def update_datafile_paths(pom_file_dict):
    """Update datafile_paths in scanned packages and dependencies."""
    scanned_pom_packages = []
    scanned_pom_deps = []

    scanned_pom_output_path = pom_file_dict.get("output_path", "")
    pom_url = pom_file_dict.get("pom_url", "")

    with open(scanned_pom_output_path) as scanned_pom_file:
        scanned_pom_data = json.load(scanned_pom_file)
        scanned_packages = scanned_pom_data.get("packages", [])
        scanned_dependencies = scanned_pom_data.get("dependencies", [])
        if scanned_packages:
            for scanned_package in scanned_packages:
                # Replace the 'datafile_path' with the pom_url
                scanned_package["datafile_paths"] = [pom_url]
                scanned_pom_packages.append(scanned_package)
        if scanned_dependencies:
            for scanned_dep in scanned_dependencies:
                # Replace the 'datafile_path' with empty string
                # See https://github.com/aboutcode-org/scancode.io/issues/1763#issuecomment-3525165830
                scanned_dep["datafile_path"] = ""
                scanned_pom_deps.append(scanned_dep)
    return scanned_pom_packages, scanned_pom_deps


def update_package_license_from_resource_if_missing(project):
    """Populate missing licenses to packages based on resource data."""
    from license_expression import Licensing

    for package in project.discoveredpackages.all():
        if not package.get_declared_license_expression():
            package_uid = package.package_uid
            detected_lics = []
            for resource in project.codebaseresources.has_license_expression():
                for for_package in resource.for_packages:
                    if for_package == package_uid:
                        detected_lic_exp = resource.detected_license_expression
                        if detected_lic_exp not in detected_lics:
                            detected_lics.append(detected_lic_exp)
            if detected_lics:
                lic_exp = " AND ".join(detected_lics)
                declared_lic_exp = str(Licensing().dedup(lic_exp))
                package.declared_license_expression = declared_lic_exp
                package.save()

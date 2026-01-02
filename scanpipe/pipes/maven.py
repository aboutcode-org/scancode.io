import json
import re

import requests

from scanpipe.pipes import fetch
from scanpipe.pipes import flag
from scanpipe.pipes import scancode


def fetch_and_scan_remote_pom(project, scan_output_location):
    """Fetch the .pom file from from maven.org if not present in codebase."""
    with open(scan_output_location) as file:
        data = json.load(file)
        # Return and do nothing if data has pom.xml
        for file in data["files"]:
            if "pom.xml" in file["path"]:
                return
        packages = data.get("packages", [])

    pom_url_list = get_pom_url_list(project.input_sources[0], packages)
    pom_file_list = download_pom_files(pom_url_list)
    scanning_errors = scan_pom_files(pom_file_list)

    scanned_pom_packages, scanned_dependencies = update_datafile_paths(pom_file_list)

    updated_packages = packages + scanned_pom_packages
    # Replace/Update the package and dependencies section
    data["packages"] = updated_packages
    data["dependencies"] = scanned_dependencies
    with open(scan_output_location, "w") as file:
        json.dump(data, file, indent=2)
    return scanning_errors


def parse_maven_filename(filename):
    """Parse a Maven's jar filename to extract artifactId and version."""
    # Remove the .jar extension
    base = filename.rsplit(".", 1)[0]

    # Common classifiers pattern
    common_classifiers = {
        "sources",
        "javadoc",
        "tests",
        "test",
        "test-sources",
        "src",
        "bin",
        "docs",
        "javadocs",
        "client",
        "server",
        "linux",
        "windows",
        "macos",
        "linux-x86_64",
        "windows-x86_64",
    }

    # Remove known classifier if present
    for classifier in common_classifiers:
        if base.endswith(f"-{classifier}"):
            base = base[: -(len(classifier) + 1)]
            break

    # Match artifactId and version
    match = re.match(r"^(.*?)-((\d[\w.\-]*))$", base)

    if match:
        artifact_id = match.group(1)
        version = match.group(2)
        return artifact_id, version
    else:
        return None, None


def get_pom_url_list(input_source, packages):
    """Generate Maven POM URLs from package metadata or input source."""
    pom_url_list = []
    if packages:
        for package in packages:
            if package.get("type") == "maven":
                package_ns = package.get("namespace", "")
                package_name = package.get("name", "")
                package_version = package.get("version", "")
                pom_url = (
                    f"https://repo1.maven.org/maven2/{package_ns.replace('.', '/')}/"
                    f"{package_name}/{package_version}/"
                    f"{package_name}-{package_version}.pom".lower()
                )
                pom_url_list.append(pom_url)
    if not pom_url_list:
        from urllib.parse import urlparse

        # Check what's the input source
        input_source_url = input_source.get("download_url", "")

        parsed_url = urlparse(input_source_url)
        maven_hosts = {
            "repo1.maven.org",
            "repo.maven.apache.org",
            "maven.google.com",
        }
        if input_source_url and parsed_url.netloc in maven_hosts:
            base_url = input_source_url.rsplit("/", 1)[0]
            pom_url = (
                base_url + "/" + "-".join(base_url.rstrip("/").split("/")[-2:]) + ".pom"
            )
            pom_url_list.append(pom_url)
        else:
            # Construct a pom_url from filename
            input_filename = input_source.get("filename", "")
            if input_filename.endswith(".jar") or input_filename.endswith(".aar"):
                artifact_id, version = parse_maven_filename(input_filename)
                if not artifact_id or not version:
                    return []
                pom_url_list = construct_pom_url_from_filename(artifact_id, version)
            else:
                # Only work with input that's a .jar or .aar file
                return []

    return pom_url_list


def construct_pom_url_from_filename(artifact_id, version):
    """Construct a pom.xml URL from the given Maven filename."""
    # Search Maven Central for the artifact to get its groupId
    url = f"https://search.maven.org/solrsearch/select?q=a:{artifact_id}&wt=json"
    pom_url_list = []
    group_ids = []
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        # Extract all 'g' fields from the docs array that represent
        # groupIds
        group_ids = [doc["g"] for doc in data["response"]["docs"]]
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return []
    except KeyError as e:
        print(f"Error parsing JSON: {e}")
        return []

    for group_id in group_ids:
        pom_url = (
            f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/"
            f"{artifact_id}/{version}/{artifact_id}-{version}.pom".lower()
        )
        if is_maven_pom_url(pom_url):
            pom_url_list.append(pom_url)
    if len(pom_url_list) > 1:
        # If multiple valid POM URLs are found, it means the same
        # artifactId and version exist under different groupIds. Since we
        # can't confidently determine the correct groupId, we return an
        # empty list to avoid fetching the wrong POM.
        return []

    return pom_url_list


def is_maven_pom_url(url):
    """Return True if the url is a accessible, False otherwise"""
    # Maven Central has a fallback mechanism that serves a generic/error
    # page instead of returning a proper 404.
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return False
        # Check content-type
        content_type = response.headers.get("content-type", "").lower()
        is_xml = "xml" in content_type or "text/xml" in content_type

        # Check content
        content = response.text.strip()
        is_pom = content.startswith("<?xml") and "<project" in content

        if is_xml and is_pom:
            return True
        else:
            # It's probably the Maven Central error page
            return False
    except requests.RequestException:
        return False


def download_pom_files(pom_url_list):
    """Fetch the pom file from the input pom_url_list"""
    pom_file_list = []
    for pom_url in pom_url_list:
        pom_file_dict = {}
        try:
            downloaded_pom = fetch.fetch_http(pom_url)
            pom_file_dict["pom_file_path"] = str(downloaded_pom.path)
            pom_file_dict["output_path"] = str(downloaded_pom.path) + "-output.json"
            pom_file_dict["pom_url"] = pom_url
            pom_file_list.append(pom_file_dict)
        except requests.RequestException:
            # Keep the process going if one pom_url fails
            continue
    return pom_file_list


def scan_pom_files(pom_file_list):
    """Fetch and scan the pom file from the input pom_url_list"""
    scan_errors = []
    for pom_file_dict in pom_file_list:
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
            scan_errors.extend(scanning_errors)
    return scan_errors


def update_datafile_paths(pom_file_list):
    """Update datafile_paths in scanned packages and dependencies."""
    scanned_pom_packages = []
    scanned_pom_deps = []
    for pom_file_dict in pom_file_list:
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


def validate_package_license_integrity(project):
    """Validate the correctness of the package license."""
    from license_expression import Licensing

    for package in project.discoveredpackages.all():
        package_lic = package.get_declared_license_expression()
        if package_lic:
            package_uid = package.package_uid
            package_uid_found = False
            detected_lic_list = []
            for resource in project.codebaseresources.has_license_expression():
                for for_package in resource.for_packages:
                    if for_package == package_uid:
                        package_uid_found = True
                        detected_lic_exp = resource.detected_license_expression
                        # Ignore all the 'unknown' detected licenses
                        if detected_lic_exp != "unknown" and detected_lic_exp:
                            if detected_lic_exp not in detected_lic_list:
                                detected_lic_list.append(detected_lic_exp)
            if not package_uid_found:
                # The package data is fetched remotely.
                for resource in project.codebaseresources.has_license_expression():
                    detected_lic_exp = resource.detected_license_expression
                    # Ignore all the 'unknown' detected licenses
                    if detected_lic_exp != "unknown" and detected_lic_exp:
                        if detected_lic_exp not in detected_lic_list:
                            detected_lic_list.append(detected_lic_exp)
            if detected_lic_list:
                lic_exp = " AND ".join(detected_lic_list)
                detected_lic_exp = str(Licensing().dedup(lic_exp))
                # The package license is not in sync with detected license(s)
                if detected_lic_exp != package_lic:
                    package.update_extra_data({"issue": "License Mismatch", "declared_license": package_lic, "detecte_codebase_license": detected_lic_exp})
                    for datafile_path in package.datafile_paths:
                        if not datafile_path.startswith("https://"):
                            data_path = project.codebaseresources.get(
                                path=datafile_path
                            )
                            data_path.update(status=flag.LICENSE_ISSUE)
                            data_path.update_extra_data({"declared_license": package_lic, "detecte_codebase_license": detected_lic_exp})


def update_package_license_from_resource_if_missing(project):
    """Populate missing licenses to packages based on resource data."""
    from license_expression import Licensing

    for package in project.discoveredpackages.all():
        if not package.get_declared_license_expression():
            package_uid = package.package_uid
            detected_lic_list = []
            for resource in project.codebaseresources.has_license_expression():
                for for_package in resource.for_packages:
                    if for_package == package_uid:
                        detected_lic_exp = resource.detected_license_expression
                        if detected_lic_exp not in detected_lic_list:
                            detected_lic_list.append(detected_lic_exp)
            if detected_lic_list:
                lic_exp = " AND ".join(detected_lic_list)
                declared_lic_exp = str(Licensing().dedup(lic_exp))
                package.declared_license_expression = declared_lic_exp
                package.save()

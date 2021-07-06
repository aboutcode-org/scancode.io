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

import json
from os.path import isfile

from commoncode.resource import get_path
from LicenseClassifier.classifier import LicenseClassifier

from scanpipe.models import CodebaseResource


def scan_file(location):
    """
    Run a license and copyright scan on provided `location`,
    using golicense-classifier.
    """
    classifier = LicenseClassifier()
    result = classifier.scanFile(location)
    return result


def run_glc(location, output_file):
    """
    Scan `location` content and write results into `output_file`.
    """
    classifier = LicenseClassifier()
    _ = classifier.analyze(location, output=output_file)


def to_dict(location):
    """
    Return scan data loaded from `location`, which is a path string
    """
    try:
        with open(location, "rb") as f:
            scan_data = json.load(f)
        return scan_data

    except IOError:
        # Raise Some Error perhaps
        raise ValueError


def create_codebase_resources(project, scan_data):
    """
    Populate CodebaseResource model with scan data from golicense_classifier
    """
    resource_data = {}
    root = scan_data["headers"][0]["input"]
    for scanned_resource in scan_data["files"]:
        for field in CodebaseResource._meta.fields:

            if field.name == "path":
                continue

            elif field.name == "copyrights":
                value = [
                    {"value": record.pop("expression", None), **record}
                    for record in scanned_resource.get("copyrights", [])
                ]

            elif field.name == "holders":
                value = [
                    {
                        "value": record.pop("holder", None),
                        "start_index": record.pop("start_index", None),
                        "end_index": record.pop("end_index", None),
                    }
                    for record in scanned_resource.get("copyrights", [])
                ]

            else:
                value = scanned_resource.get(field.name, None)

            if value is not None:
                resource_data[field.name] = value

        resource_type = "FILE" if isfile(scanned_resource["path"]) else "DIRECTORY"
        resource_data["type"] = CodebaseResource.Type[resource_type]
        resource_path = get_path(root, scanned_resource["path"], strip_root=True)

        CodebaseResource.objects.get_or_create(
            project=project,
            path=resource_path,
            defaults=resource_data,
        )

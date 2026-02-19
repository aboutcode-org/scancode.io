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

import os
import uuid
import warnings
from datetime import datetime
from functools import wraps
from unittest import mock

from django.apps import apps

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.models import ProjectMessage
from scanpipe.tests.pipelines.do_nothing import DoNothing
from scanpipe.tests.pipelines.download_inputs import DownloadInput
from scanpipe.tests.pipelines.profile_step import ProfileStep
from scanpipe.tests.pipelines.raise_exception import RaiseException

scanpipe_app = apps.get_app_config("scanpipe")

scanpipe_app.register_pipeline("do_nothing", DoNothing)
scanpipe_app.register_pipeline("download_inputs", DownloadInput)
scanpipe_app.register_pipeline("profile_step", ProfileStep)
scanpipe_app.register_pipeline("raise_exception", RaiseException)

FIXTURES_REGEN = os.environ.get("SCANCODEIO_TEST_FIXTURES_REGEN", False)
mocked_now = mock.Mock(now=lambda: datetime(2010, 10, 10, 10, 10, 10))


def filter_warnings(action, category, module=None):
    """Apply a warning filter to a function."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            original_filters = warnings.filters[:]
            try:
                warnings.filterwarnings(action, category=category, module=module)
                return func(*args, **kwargs)
            finally:
                warnings.filters = original_filters

        return wrapper

    return decorator


def make_string(length):
    return str(uuid.uuid4())[:length]


def make_project(name=None, **data):
    """
    Create and return a Project instance.
    Labels can be provided using the labels=["labels1", "labels2"] argument.
    """
    name = name or make_string(8)
    pipelines = data.pop("pipelines", [])
    labels = data.pop("labels", [])

    project = Project.objects.create(name=name, **data)

    for pipeline in pipelines:
        project.add_pipeline(pipeline)

    if labels:
        project.labels.add(*labels)

    return project


def make_resource(project, path, **data):
    return CodebaseResource.objects.create(
        project=project,
        path=path,
        name=path.split("/")[-1],
        tag=path.split("/")[0],
        **data,
    )


def make_resource_file(project, path=None, **data):
    if path is None:  # Empty string is allowed as path
        path = make_string(5)

    return make_resource(
        project=project,
        path=path,
        extension="." + path.split(".")[-1],
        type=CodebaseResource.Type.FILE,
        is_text=True,
        **data,
    )


def make_resource_directory(project, path, **data):
    return make_resource(
        project=project,
        path=path,
        type=CodebaseResource.Type.DIRECTORY,
        **data,
    )


def make_package(project, package_url, **data):
    package = DiscoveredPackage(project=project, **data)
    package.set_package_url(package_url)
    package.save()
    return package


def make_dependency(project, **data):
    return DiscoveredDependency.objects.create(project=project, **data)


def make_message(project, **data):
    if "model" not in data:
        data["model"] = make_string(8)

    if "severity" not in data:
        data["severity"] = ProjectMessage.Severity.ERROR

    return ProjectMessage.objects.create(
        project=project,
        **data,
    )


def make_mock_response(url, content=b"\x00", status_code=200, headers=None):
    """Return a mock HTTP response object for testing purposes."""
    response = mock.Mock()
    response.url = url
    response.content = content
    response.status_code = status_code
    response.headers = headers or {}
    return response


resource_data1 = {
    "path": "notice.NOTICE",
    "type": "file",
    "name": "notice.NOTICE",
    "status": "",
    "tag": "",
    "extension": ".NOTICE",
    "size": 1178,
    "md5": "90cd416fd24df31f608249b77bae80f1",
    "sha1": "4bd631df28995c332bf69d9d4f0f74d7ee089598",
    "sha256": "b323607418a36b5bd700fcf52ae9ca49f82ec6359bc4b89b1b2d73cf75321757",
    "sha512": "",
    "mime_type": "text/plain",
    "file_type": "ASCII text",
    "programming_language": "",
    "is_binary": False,
    "is_text": True,
    "is_archive": False,
    "is_media": False,
    "is_legal": False,
    "is_manifest": False,
    "is_readme": False,
    "is_top_level": False,
    "is_key_file": False,
    "license_detections": [],
    "detected_license_expression": "",
    "compliance_alert": "",
    "copyrights": [],
    "holders": [],
    "authors": [],
    "package_data": [],
    "for_packages": [],
    "emails": [],
    "urls": [],
    "extra_data": {},
}

parties_data1 = [
    {
        "name": "AboutCode and others",
        "role": "author",
        "type": "person",
        "email": "info@aboutcode.org",
        "url": None,
    },
    # Duplicate on purpose
    {
        "name": "AboutCode and others",
        "role": "author",
        "type": "person",
        "email": "info@aboutcode.org",
        "url": None,
    },
    {
        "name": "Debian X Strike Force",
        "role": "maintainer",
        "email": "debian-x@lists.debian.org",
    },
    {
        "name": "JBoss.org Community",
        "role": "developer",
        "type": "person",
        "email": None,
    },
    {
        "url": "http://www.apache.org/",
        "name": "The Apache Software Foundation",
        "role": "owner",
        "type": "organization",
        "email": None,
    },
]

package_data1 = {
    "type": "deb",
    "namespace": "debian",
    "name": "adduser",
    "version": "3.118",
    "qualifiers": {"arch": "all"},
    "subpath": None,
    "primary_language": "bash",
    "description": "add and remove users and groups",
    "release_date": "1999-10-10",
    "parties": [
        {
            "type": None,
            "role": "maintainer",
            "name": "Debian Adduser Developers <adduser@packages.debian.org>",
            "email": None,
            "url": None,
        }
    ],
    "keywords": ["admin"],
    "homepage_url": "https://packages.debian.org",
    "download_url": "https://download.url/package.zip",
    "filename": "package.zip",
    "size": "849",
    "sha1": None,
    "md5": "76cf50f29e47676962645632737365a7",
    "sha256": None,
    "sha512": None,
    "bug_tracking_url": None,
    "code_view_url": None,
    "vcs_url": "https://packages.vcs.url",
    "copyright": (
        "Copyright (c) 2000 Roland Bauerschmidt <rb@debian.org>\n"
        "Copyright (c) 1997, 1998, 1999 Guy Maor <maor@debian.org>\n"
        "Copyright (c) 1995 Ted Hajek <tedhajek@boombox.micro.umn.edu>\n"
        "portions Copyright (c) 1994 Debian Association, Inc."
    ),
    "declared_license_expression": "gpl-2.0 AND gpl-2.0-plus",
    "declared_license_expression_spdx": "GPL-2.0-only AND GPL-2.0-or-later",
    "other_license_expression": "apache-2.0 AND (mpl-1.1 OR gpl-2.0)",
    "other_license_expression_spdx": "Apache-2.0 AND (MPL-1.1 OR GPL-2.0)",
    "extracted_license_statement": "",
    "notice_text": "Notice\nText",
    "root_path": None,
    "dependencies": [],
    "source_packages": [],
    "purl": "pkg:deb/debian/adduser@3.118?arch=all",
    "repository_homepage_url": None,
    "repository_download_url": None,
    "api_data_url": None,
    "package_uid": "pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b",
}

package_data2 = {
    "type": "deb",
    "namespace": "debian",
    "name": "adduser",
    "version": "3.119",
}

for_package_uid = "pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b"

dependency_data1 = {
    "purl": "pkg:pypi/dask",
    "package_type": "pypi",
    "extracted_requirement": "dask<2023.0.0,>=2022.6.0",
    "scope": "install",
    "is_runtime": True,
    "is_optional": False,
    "is_pinned": False,
    "dependency_uid": "pkg:pypi/dask?uuid=e656b571-7d3f-46d1-b95b-8f037aef9692",
    "for_package_uid": for_package_uid,
    "datafile_path": "daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
    "datasource_id": "pypi_sdist_pkginfo",
}

dependency_data2 = {
    "purl": "pkg:gem/appraisal@2.2.0",
    "package_type": "gem",
    "extracted_requirement": "",
    "scope": "dependencies",
    "is_runtime": True,
    "is_optional": False,
    "is_pinned": True,
    "dependency_uid": (
        "pkg:gem/appraisal@2.2.0?uuid=1907f061-911b-4980-a2d4-ae1a9ed871a9"
    ),
    "for_package_uid": for_package_uid,
    "datafile_path": "data.tar.gz-extract/Gemfile.lock",
    "datasource_id": "gemfile_lock",
}

dependency_data3 = {
    "purl": "pkg:pypi/dask",
    "package_type": "pypi",
    "extracted_requirement": ">= 1.0",
    "scope": "install",
    "is_runtime": True,
    "is_optional": False,
    "is_pinned": False,
    "dependency_uid": "pkg:pypi/dask?uuid=e656b571-7d3f-46d1-b95b-8f037aef9692",
    "for_package_uid": for_package_uid,
    "datafile_path": "daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
    "datasource_id": "pypi_sdist_pkginfo",
}

dependency_data4 = {
    "purl": "pkg:npm/wrap-ansi-cjs",
    "package_type": "npm",
    "extracted_requirement": "npm:wrap-ansi@^7.0.0",
    "scope": "devDependencies",
    "is_runtime": False,
    "is_optional": True,
    "is_pinned": False,
    "is_direct": True,
    "dependency_uid": "pkg:npm/wrap-ansi-cjs?uuid=e656b571-7d3f-46d1-b95b-8f037aef9692",
    "for_package_uid": "",
    "datafile_path": "",
    "datasource_id": "npm_package_lock_json",
}

license_policies = [
    {
        "license_key": "apache-2.0",
        "label": "Approved License",
        "compliance_alert": "",
    },
    {
        "license_key": "mpl-2.0",
        "label": "Restricted License",
        "compliance_alert": "warning",
    },
    {
        "license_key": "gpl-3.0",
        "label": "Prohibited License",
        "compliance_alert": "error",
    },
    {
        "license_key": "gpl-2.0-plus",
        "compliance_alert": "warning",
    },
    {
        "license_key": "font-exception-gpl",
        "compliance_alert": "warning",
    },
    {
        "license_key": "OFL-1.1",
        "compliance_alert": "warning",
    },
    {
        "license_key": "LicenseRef-scancode-public-domain",
        "compliance_alert": "ok",
    },
    {
        "license_key": "LicenseRef-scancode-unknown-license-reference",
        "compliance_alert": "error",
    },
]


global_policies = {
    "license_policies": license_policies,
}

license_policies_index = {
    "apache-2.0": {
        "license_key": "apache-2.0",
        "label": "Approved License",
        "compliance_alert": "",
    },
    "mpl-2.0": {
        "license_key": "mpl-2.0",
        "label": "Restricted License",
        "compliance_alert": "warning",
    },
    "gpl-3.0": {
        "license_key": "gpl-3.0",
        "label": "Prohibited License",
        "compliance_alert": "error",
    },
    "gpl-2.0-plus": {
        "license_key": "gpl-2.0-plus",
        "compliance_alert": "warning",
    },
    "font-exception-gpl": {
        "license_key": "font-exception-gpl",
        "compliance_alert": "warning",
    },
    "OFL-1.1": {
        "license_key": "OFL-1.1",
        "compliance_alert": "warning",
    },
    "LicenseRef-scancode-public-domain": {
        "license_key": "LicenseRef-scancode-public-domain",
        "compliance_alert": "ok",
    },
    "LicenseRef-scancode-unknown-license-reference": {
        "license_key": "LicenseRef-scancode-unknown-license-reference",
        "compliance_alert": "error",
    },
}

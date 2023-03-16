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
from datetime import datetime
from unittest import mock

from django.apps import apps

from scanpipe.tests.pipelines.do_nothing import DoNothing
from scanpipe.tests.pipelines.profile_step import ProfileStep
from scanpipe.tests.pipelines.raise_exception import RaiseException

scanpipe_app = apps.get_app_config("scanpipe")

scanpipe_app.register_pipeline("do_nothing", DoNothing)
scanpipe_app.register_pipeline("profile_step", ProfileStep)
scanpipe_app.register_pipeline("raise_exception", RaiseException)

FIXTURES_REGEN = os.environ.get("SCANCODEIO_TEST_FIXTURES_REGEN", False)
mocked_now = mock.Mock(now=lambda: datetime(2010, 10, 10, 10, 10, 10))

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
    "is_key_file": False,
    "licenses": [],
    "license_expressions": [],
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
    "license_expression": "gpl-2.0 AND gpl-2.0-plus AND unknown",
    "declared_license": "",
    "notice_text": None,
    "root_path": None,
    "dependencies": [],
    "contains_source_code": None,
    "source_packages": [],
    "purl": "pkg:deb/debian/adduser@3.118?arch=all",
    "repository_homepage_url": None,
    "repository_download_url": None,
    "api_data_url": None,
    "package_uid": "pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b",
}

for_package_uid = "pkg:deb/debian/adduser@3.118?uuid=610bed29-ce39-40e7-92d6-fd8b"

dependency_data1 = {
    "purl": "pkg:pypi/dask",
    "package_type": "pypi",
    "extracted_requirement": "dask<2023.0.0,>=2022.6.0",
    "scope": "install",
    "is_runtime": True,
    "is_optional": False,
    "is_resolved": False,
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
    "is_resolved": True,
    "dependency_uid": (
        "pkg:gem/appraisal@2.2.0?uuid=1907f061-911b-4980-a2d4-ae1a9ed871a9"
    ),
    "for_package_uid": for_package_uid,
    "datafile_path": "data.tar.gz-extract/Gemfile.lock",
    "datasource_id": "gemfile_lock",
}

license_policies = [
    {
        "license_key": "apache-2.0",
        "label": "Approved License",
        "color_code": "#008000",
        "compliance_alert": "",
    },
    {
        "license_key": "mpl-2.0",
        "label": "Restricted License",
        "color_code": "#ffcc33",
        "compliance_alert": "warning",
    },
    {
        "license_key": "gpl-3.0",
        "label": "Prohibited License",
        "color_code": "#c83025",
        "compliance_alert": "error",
    },
]

license_policies_index = {
    "gpl-3.0": {
        "color_code": "#c83025",
        "compliance_alert": "error",
        "label": "Prohibited License",
        "license_key": "gpl-3.0",
    },
    "apache-2.0": {
        "color_code": "#008000",
        "compliance_alert": "",
        "label": "Approved License",
        "license_key": "apache-2.0",
    },
    "mpl-2.0": {
        "color_code": "#ffcc33",
        "compliance_alert": "warning",
        "label": "Restricted License",
        "license_key": "mpl-2.0",
    },
}

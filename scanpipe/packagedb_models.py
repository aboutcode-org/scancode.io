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

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from packageurl.contrib.django.models import PackageURLMixin


class AbstractPackage(PackageURLMixin, models.Model):
    uuid = models.UUIDField(
        verbose_name=_("UUID"), default=uuid.uuid4, unique=True, editable=False
    )

    last_modified_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Timestamp set when a Package is created or modified"),
    )

    filename = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text=_(
            "File name of a Resource sometimes part of the URI proper"
            "and sometimes only available through an HTTP header."
        ),
    )

    primary_language = models.CharField(
        max_length=50, blank=True, help_text=_("Primary programming language")
    )

    description = models.TextField(
        blank=True,
        help_text=_(
            "Description for this package. "
            "By convention the first line should be a summary when available."
        ),
    )

    release_date = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        help_text=_(
            "The date that the package file was created, or when "
            "it was posted to its original download source."
        ),
    )

    homepage_url = models.CharField(
        max_length=1024,
        blank=True,
        help_text=_("URL to the homepage for this package."),
    )

    download_url = models.CharField(
        max_length=2048, blank=True, help_text=_("A direct download URL.")
    )

    size = models.BigIntegerField(
        blank=True, null=True, db_index=True, help_text=_("Size in bytes.")
    )

    sha1 = models.CharField(
        verbose_name=_("download SHA1"),
        max_length=40,
        blank=True,
        db_index=True,
        help_text=_("SHA1 checksum hex-encoded, as in sha1sum."),
    )

    md5 = models.CharField(
        verbose_name=_("download MD5"),
        max_length=32,
        blank=True,
        db_index=True,
        help_text=_("MD5 checksum hex-encoded, as in md5sum."),
    )

    bug_tracking_url = models.CharField(
        max_length=1024,
        blank=True,
        help_text=_("URL to the issue or bug tracker for this package"),
    )

    code_view_url = models.CharField(
        max_length=1024,
        blank=True,
        help_text=_("a URL where the code can be browsed online"),
    )

    vcs_url = models.CharField(
        max_length=1024,
        blank=True,
        help_text=_(
            "a URL to the VCS repository in the SPDX form of: "
            '"git", "svn", "hg", "bzr", "cvs", '
            "https://github.com/nexb/scancode-toolkit.git@405aaa4b3 "
            'See SPDX specification "Package Download Location" '
            "at https://spdx.org/spdx-specification-21-web-version#h.49x2ik5 "
        ),
    )

    copyright = models.TextField(
        blank=True,
        help_text=_("Copyright statements for this package. Typically one per line."),
    )

    license_expression = models.TextField(
        blank=True,
        help_text=_(
            "The normalized license expression for this package as derived "
            "from its declared license."
        ),
    )

    declared_license = models.TextField(
        blank=True,
        help_text=_(
            "The declared license mention or tag or text as found in a "
            "package manifest."
        ),
    )

    notice_text = models.TextField(
        blank=True, help_text=_("A notice text for this package.")
    )

    manifest_path = models.CharField(
        max_length=1024,
        blank=True,
        help_text=_(
            "A relative path to the manifest file if any, such as a "
            "Maven .pom or a npm package.json."
        ),
    )

    contains_source_code = models.BooleanField(null=True, blank=True)

    class Meta:
        abstract = True


class AbstractResource(models.Model):
    """
    These model fields should be kept in line with scancode.resource.Resource
    """

    path = models.CharField(
        max_length=2000,
        help_text=_(
            "The full path value of a resource (file or directory) in the "
            "archive it is from."
        ),
    )

    size = models.BigIntegerField(blank=True, null=True, help_text=_("Size in bytes."))

    sha1 = models.CharField(
        max_length=40,
        blank=True,
        help_text=_("SHA1 checksum hex-encoded, as in sha1sum."),
    )

    md5 = models.CharField(
        max_length=32,
        blank=True,
        help_text=_("MD5 checksum hex-encoded, as in md5sum."),
    )

    sha256 = models.CharField(
        max_length=64,
        blank=True,
        help_text=_("SHA256 checksum hex-encoded, as in sha256sum."),
    )

    sha512 = models.CharField(
        max_length=128,
        blank=True,
        help_text=_("SHA512 checksum hex-encoded, as in sha512sum."),
    )

    def __str__(self):
        return self.path

    class Meta:
        abstract = True

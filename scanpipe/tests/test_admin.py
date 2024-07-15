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

import sys
from importlib import reload
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import TestCase
from django.test import override_settings
from django.urls import clear_url_caches
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from scanpipe.models import Project
from scanpipe.tests import make_dependency
from scanpipe.tests import make_package
from scanpipe.tests import make_resource_file

scanpipe_app = apps.get_app_config("scanpipe")


def refresh_url_cache():
    """
    Clear the URLs cache and reloading the URLs module.
    Useful when changing the value of a settings trigger different URLs availability.
    """
    clear_url_caches()
    if settings.ROOT_URLCONF in sys.modules:
        reload(sys.modules[settings.ROOT_URLCONF])


@override_settings(SCANCODEIO_ENABLE_ADMIN_SITE=True)
class ScanPipeAdminTest(TestCase):
    data = Path(__file__).parent / "data"

    def setUp(self):
        refresh_url_cache()
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_admin_site_is_enabled_setting(self):
        self.assertEqual("/admin/", reverse("admin:index"))
        self.assertEqual(
            "/admin/scanpipe/project/", reverse("admin:scanpipe_project_changelist")
        )
        self.assertEqual(
            f"/admin/scanpipe/project/{self.project1.uuid}/change/",
            reverse("admin:scanpipe_project_change", args=[self.project1.pk]),
        )

        with override_settings(SCANCODEIO_ENABLE_ADMIN_SITE=False):
            refresh_url_cache()
            with self.assertRaises(NoReverseMatch):
                reverse("admin:index")

    def test_scanpipe_admin_models_get_admin_url(self):
        resource = make_resource_file(self.project1, "path")
        self.assertEqual(
            f"/admin/scanpipe/codebaseresource/{resource.id}/change/",
            resource.get_admin_url(),
        )
        package = make_package(self.project1, "pkg:type/a")
        self.assertEqual(
            f"/admin/scanpipe/discoveredpackage/{package.id}/change/",
            package.get_admin_url(),
        )
        dependency = make_dependency(self.project1, for_package=package)
        self.assertEqual(
            f"/admin/scanpipe/discovereddependency/{dependency.id}/change/",
            dependency.get_admin_url(),
        )

        with override_settings(SCANCODEIO_ENABLE_ADMIN_SITE=False):
            refresh_url_cache()
            self.assertIsNone(resource.get_admin_url())
            self.assertIsNone(package.get_admin_url())
            self.assertIsNone(dependency.get_admin_url())

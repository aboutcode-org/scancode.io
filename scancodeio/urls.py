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

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import include
from django.urls import path
from django.views.generic import RedirectView

from rest_framework.routers import DefaultRouter

from scanpipe.admin import admin_site
from scanpipe.api.views import ProjectViewSet
from scanpipe.api.views import RunViewSet
from scanpipe.views import AccountProfileView

api_router = DefaultRouter()
api_router.register(r"projects", ProjectViewSet)
api_router.register(r"runs", RunViewSet)

auth_urlpatterns = [
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    path("accounts/profile/", AccountProfileView.as_view(), name="account_profile"),
]


urlpatterns = auth_urlpatterns + [
    path("api/", include(api_router.urls)),
    path("", include("scanpipe.urls")),
    path("", RedirectView.as_view(url="project/")),
]


if settings.SCANCODEIO_ENABLE_ADMIN_SITE:
    urlpatterns.append(path("admin/", admin_site.urls))


if settings.DEBUG and settings.DEBUG_TOOLBAR:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))

#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import include
from django.urls import path
from django.views.generic import RedirectView

from rest_framework.routers import DefaultRouter

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

if settings.DEBUG and settings.DEBUG_TOOLBAR:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))

#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin


def is_authenticated_when_required(user):
    """
    Return True if the `user` is authenticated when the
    `SCANCODEIO_REQUIRE_AUTHENTICATION` setting is enabled.

    Always True when the Authentication is not enabled.
    """
    if not settings.SCANCODEIO_REQUIRE_AUTHENTICATION:
        return True

    if user.is_authenticated:
        return True

    return False


def conditional_login_required(function=None):
    """
    Decorate views that checks that the current user is authenticated when
    authentication is enabled.
    """
    actual_decorator = user_passes_test(is_authenticated_when_required)
    if function:
        return actual_decorator(function)
    return actual_decorator


class ConditionalLoginRequired(UserPassesTestMixin):
    """
    CBV mixin for views that checks that the current user is authenticated when
    authentication is enabled.
    """

    def test_func(self):
        return is_authenticated_when_required(self.request.user)

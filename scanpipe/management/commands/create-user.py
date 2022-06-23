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

from django.contrib.auth import get_user_model
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = "Create a user and generate an API key for authentication."
    requires_migrations_checks = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = get_user_model()
        self.username_field = self.UserModel._meta.get_field(
            self.UserModel.USERNAME_FIELD
        )

    def add_arguments(self, parser):
        parser.add_argument("username", help="Specifies the username for the user.")

    def handle(self, *args, **options):
        username = options["username"]

        error_msg = self._validate_username(username)
        if error_msg:
            raise CommandError(error_msg)

        user = self.UserModel._default_manager.create_user(username=username)
        token, _ = Token._default_manager.get_or_create(user=user)

        if options["verbosity"] >= 1:
            msg = f"User {username} created with API key: {token.key}"
            self.stdout.write(self.style.SUCCESS(msg))

    def _validate_username(self, username):
        """
        Validate username. If invalid, return a string error message.
        """
        if self.username_field.unique:
            try:
                self.UserModel._default_manager.get_by_natural_key(username)
            except self.UserModel.DoesNotExist:
                pass
            else:
                return "Error: That username is already taken."

        try:
            self.username_field.clean(username, None)
        except exceptions.ValidationError as e:
            return "; ".join(e.messages)

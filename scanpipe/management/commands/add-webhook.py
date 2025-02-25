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


from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.core.validators import URLValidator

from scanpipe.management.commands import ProjectCommand


class Command(ProjectCommand):
    help = "Add a webhook subscription to a project."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "target_url",
            help="The target URL to which the webhook should send POST requests.",
        )
        parser.add_argument(
            "--trigger-on-each-run",
            action="store_true",
            help="Trigger the webhook after each individual pipeline run.",
        )
        parser.add_argument(
            "--include-summary",
            action="store_true",
            help="Include summary data in the payload.",
        )
        parser.add_argument(
            "--include-results",
            action="store_true",
            help="Include results data in the payload.",
        )
        parser.add_argument(
            "--inactive",
            action="store_true",
            help="Create the webhook but set it as inactive.",
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)

        target_url = options["target_url"]
        is_active = not options["inactive"]

        # Validate the URL using Django's URLValidator
        validate_url = URLValidator()
        try:
            validate_url(target_url)
        except ValidationError:
            raise CommandError(f"Invalid URL: {target_url}")

        self.project.add_webhook_subscription(
            target_url=target_url,
            is_active=is_active,
            trigger_on_each_run=options["trigger_on_each_run"],
            include_summary=options["include_summary"],
            include_results=options["include_results"],
        )

        if self.verbosity > 0:
            status = "active" if is_active else "inactive"
            self.stdout.write(
                f"Webhook successfully added to project '{self.project}' ({status}). ",
                self.style.SUCCESS,
            )

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


from django.apps import apps
from django.core.management.base import BaseCommand

scanpipe_app = apps.get_app_config("scanpipe")


class Command(BaseCommand):
    help = (
        "Displays a list of available pipelines. "
        "Use --verbosity=2 to include details of each pipeline's steps."
    )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]

        for module_name, pipeline_class in scanpipe_app.pipelines.items():
            msg = self.style.HTTP_INFO(module_name)
            if pipeline_class.is_addon:
                msg += " (addon)"
            self.stdout.write(msg)
            pipeline_info = pipeline_class.get_info()
            if verbosity >= 1:
                self.stdout.write(pipeline_info["summary"])

            if verbosity >= 2:
                steps = pipeline_info["steps"]
                for step_info in steps:
                    step_name = step_info["name"]
                    step_doc = step_info["doc"].replace("\n", "\n   ")
                    step_groups = step_info["groups"]
                    self.stdout.write(f" > [{step_name}]: {step_doc}")
                    if step_groups:
                        self.stdout.write(f"   {{Group}}: {','.join(step_groups)}")

            if verbosity >= 1:
                self.stdout.write("\n")

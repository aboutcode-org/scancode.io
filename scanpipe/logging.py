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

import functools
import re
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import cached_property

from scancodeio import WORKSPACE_LOCATION


def extra_logging(func, extra_logger):
    """
    Decorator to add logging customization the default Metaflow logger.
    This is used as a workaround since Metaflow does not provide any API to customize
    the logging of Flow/Pipeline execution.
    """

    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        value = func(*args, **kwargs)
        extra_logger.log(*args, **kwargs)
        return value

    return wrapper_decorator


class RunLogger:
    """
    Log messages from Pipeline execution on the Run instance `log` field.
    If the `run_id` is not available in the message, the message is logged to the
    `log_file`.

    One caveat to this approach is that the `run_id` is set on the Run instance during
    the "start" step of a Pipeline, making the "Task is starting." message for that
    initial step not logged in the `Run.log` field.
    """

    log_file = Path(WORKSPACE_LOCATION) / "scanpipe.log"

    @cached_property
    def run_model(self):
        return apps.get_model("scanpipe", "Run")

    @staticmethod
    def get_run_id(head):
        run_id_pattern = re.compile(r"\[(?P<run_id>[0-9]{16})/")
        match = run_id_pattern.search(head)
        if match:
            return match.group("run_id")

    def get_run(self, run_id):
        if not run_id:
            return
        with suppress(ObjectDoesNotExist, MultipleObjectsReturned):
            return self.run_model.objects.get(run_id=run_id)

    def log(self, body="", head="", **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = f"{timestamp} {head}{body}"

        run_id = self.get_run_id(head)
        run = self.get_run(run_id)
        if run:
            self.log_to_run_instance(run, message)
        else:
            self.log_to_file(message)

    @staticmethod
    def log_to_run_instance(run, message):
        run.append_to_log(message)
        run.save()

    def log_to_file(self, message):
        with open(self.log_file, "a+") as f:
            f.write(message + "\n")

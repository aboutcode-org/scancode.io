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

import logging
import traceback
from datetime import datetime
from datetime import timezone
from pydoc import getdoc
from pydoc import splitdoc
from timeit import default_timer as timer

logger = logging.getLogger(__name__)


def group(*groups):
    """Mark a function as part of a particular group."""

    def decorator(obj):
        if hasattr(obj, "groups"):
            obj.groups = obj.groups.union(groups)
        else:
            setattr(obj, "groups", set(groups))
        return obj

    return decorator


def humanize_time(seconds):
    """Convert the provided ``seconds`` number into human-readable time."""
    message = f"{seconds:.0f} seconds"

    if seconds > 86400:
        message += f" ({seconds / 86400:.1f} days)"
    if seconds > 3600:
        message += f" ({seconds / 3600:.1f} hours)"
    elif seconds > 60:
        message += f" ({seconds / 60:.1f} minutes)"

    return message


class BasePipeline:
    """Base class for all pipeline implementations."""

    # Flag indicating if the Pipeline is an add-on, meaning it cannot be run first.
    is_addon = False

    def __init__(self, run):
        """Load the Run and Project instances."""
        self.run = run
        self.project = run.project
        self.pipeline_name = run.pipeline_name
        self.env = self.project.get_env()

    @classmethod
    def steps(cls):
        raise NotImplementedError

    @classmethod
    def get_steps(cls, groups=None):
        """
        Return the list of steps defined in the ``steps`` class method.

        If the optional ``groups`` parameter is provided, only include steps labeled
        with groups that intersect with the provided list. If a step has no groups or
        if ``groups`` is not specified, include the step in the result.
        """
        if not callable(cls.steps):
            raise TypeError("Use a ``steps(cls)`` classmethod to declare the steps.")

        steps = cls.steps()

        if groups is not None:
            steps = tuple(
                step
                for step in steps
                if not getattr(step, "groups", [])
                or set(getattr(step, "groups")).intersection(groups)
            )

        return steps

    @classmethod
    def get_initial_steps(cls):
        """
        Return a tuple of extra initial steps to be run at the start of the pipeline
        execution.
        """
        return

    @classmethod
    def get_doc(cls):
        """Get the doc string of this pipeline."""
        return getdoc(cls)

    @classmethod
    def get_graph(cls):
        """Return a graph of steps."""
        return [
            {
                "name": step.__name__,
                "doc": getdoc(step),
                "groups": getattr(step, "groups", []),
            }
            for step in cls.get_steps()
        ]

    @classmethod
    def get_info(cls):
        """Get a dictionary of combined information data about this pipeline."""
        summary, description = splitdoc(cls.get_doc())
        steps = cls.get_graph()

        return {
            "summary": summary,
            "description": description,
            "steps": steps,
            "available_groups": cls.get_available_groups(),
        }

    @classmethod
    def get_summary(cls):
        """Get the doc string summary."""
        return cls.get_info()["summary"]

    @classmethod
    def get_available_groups(cls):
        return sorted(
            set(
                group_name
                for step in cls.get_steps()
                for group_name in getattr(step, "groups", [])
            )
        )

    def log(self, message):
        """Log the given `message` to the current module logger and Run instance."""
        now_local = datetime.now(timezone.utc).astimezone()
        timestamp = now_local.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = f"{timestamp} {message}"
        logger.info(message)
        self.run.append_to_log(message)

    @staticmethod
    def output_from_exception(exception):
        """Return a formatted error message including the traceback."""
        output = f"{exception}\n\n"

        if exception.__cause__ and str(exception.__cause__) != str(exception):
            output += f"Cause: {exception.__cause__}\n\n"

        traceback_formatted = "".join(traceback.format_tb(exception.__traceback__))
        output += f"Traceback:\n{traceback_formatted}"

        return output

    def execute(self):
        """Execute each steps in the order defined on this pipeline class."""
        self.log(f"Pipeline [{self.pipeline_name}] starting")

        steps = self.get_steps(groups=self.run.selected_groups)
        selected_steps = self.run.selected_steps

        if initial_steps := self.get_initial_steps():
            steps = initial_steps + steps

        steps_count = len(steps)
        pipeline_start_time = timer()

        for current_index, step in enumerate(steps, start=1):
            step_name = step.__name__

            if selected_steps and step_name not in selected_steps:
                self.log(f"Step [{step_name}] skipped")
                continue

            self.run.set_current_step(f"{current_index}/{steps_count} {step_name}")
            self.log(f"Step [{step_name}] starting")
            step_start_time = timer()

            try:
                step(self)
            except Exception as exception:
                self.log("Pipeline failed")
                return 1, self.output_from_exception(exception)

            step_run_time = timer() - step_start_time
            self.log(f"Step [{step_name}] completed in {humanize_time(step_run_time)}")

        self.run.set_current_step("")  # Reset the `current_step` field on completion
        pipeline_run_time = timer() - pipeline_start_time
        self.log(f"Pipeline completed in {humanize_time(pipeline_run_time)}")

        return 0, ""

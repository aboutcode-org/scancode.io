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

import logging
import traceback
import warnings
from datetime import datetime
from datetime import timezone
from pydoc import getdoc
from pydoc import splitdoc
from timeit import default_timer as timer

module_logger = logging.getLogger(__name__)

__version__ = "0.2.1"


class PipelineDefinition:
    """
    Encapsulate the code related to a Pipeline definition:
    - Steps
    - Attributes
    - Documentation
    """

    # Flag indicating if the Pipeline is an add-on, meaning it cannot be run first.
    is_addon = False

    @classmethod
    def steps(cls):
        raise NotImplementedError

    @classmethod
    def get_steps(cls, groups=None):
        """
        Return the list of steps defined in the ``steps`` class method.

        By default, all steps decorated with ``optional_step`` are not included.
        A list of optional steps can be included using the ``groups`` parameter.
        """
        if not callable(cls.steps):
            raise TypeError("Use a ``steps(cls)`` classmethod to declare the steps.")

        steps = cls.steps()
        groups = groups or []

        if initial_steps := cls.get_initial_steps():
            steps = (*initial_steps, *steps)

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
            for step in cls.get_steps(groups=cls.get_available_groups())
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
                for step in cls.steps()
                for group_name in getattr(step, "groups", [])
            )
        )


class PipelineRun:
    """
    Encapsulate the code related to a Pipeline run (execution):
    - Execution context: groups, steps
    - Execution logic
    - Logging
    - Results
    """

    def __init__(self, selected_groups=None, selected_steps=None):
        """Load the Pipeline class."""
        self.pipeline_class = self.__class__
        self.pipeline_name = self.__class__.__name__

        self.selected_groups = selected_groups
        self.selected_steps = selected_steps or []

        self.execution_log = []
        self.current_step = ""

    def append_to_log(self, message):
        self.execution_log.append(message)

    def set_current_step(self, message):
        self.current_step = message

    def log(self, message):
        """Log the given `message` to the current module logger and execution_log."""
        now_local = datetime.now(timezone.utc).astimezone()
        timestamp = now_local.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = f"{timestamp} {message}"
        module_logger.info(message)
        self.append_to_log(message)

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

        steps = self.pipeline_class.get_steps(groups=self.selected_groups)
        steps_count = len(steps)
        pipeline_start_time = timer()

        for current_index, step in enumerate(steps, start=1):
            step_name = step.__name__

            if self.selected_steps and step_name not in self.selected_steps:
                self.log(f"Step [{step_name}] skipped")
                continue

            self.set_current_step(f"{current_index}/{steps_count} {step_name}")
            self.log(f"Step [{step_name}] starting")
            step_start_time = timer()

            try:
                step(self)
            except Exception as exception:
                self.log("Pipeline failed")
                return 1, self.output_from_exception(exception)

            step_run_time = timer() - step_start_time
            self.log(f"Step [{step_name}] completed in {humanize_time(step_run_time)}")

        # Reset the `current_step` field on completion
        self.set_current_step("")
        pipeline_run_time = timer() - pipeline_start_time
        self.log(f"Pipeline completed in {humanize_time(pipeline_run_time)}")

        return 0, ""


class BasePipeline(PipelineDefinition, PipelineRun):
    """
    Base class for all pipeline implementations.
    It combines the pipeline definition and execution logics.
    """


def optional_step(*groups):
    """Mark a step function as optional and part of a group."""

    def decorator(obj):
        if hasattr(obj, "groups"):
            obj.groups = obj.groups.union(groups)
        else:
            setattr(obj, "groups", set(groups))
        return obj

    return decorator


def group(*groups):
    """Backward compatibility."""
    warnings.warn(
        "The `group` decorator is deprecated and will be "
        "removed in a future release. Use `optional_step` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return optional_step(*groups)


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


class LoopProgress:
    """
    A context manager for logging progress in loops.

    Usage::
        total_iterations = 100
        logger = print  # Replace with your actual logger function

        progress = LoopProgress(total_iterations, logger, progress_step=10)
        for item in progress.iter(iterator):
            "Your processing logic here"

        # As a context manager
        with LoopProgress(total_iterations, logger, progress_step=10) as progress:
            for item in progress.iter(iterator):
                "Your processing logic here"
    """

    def __init__(self, total_iterations, logger, progress_step=10):
        self.total_iterations = total_iterations
        self.logger = logger
        self.progress_step = progress_step
        self.start_time = timer()
        self.last_logged_progress = 0
        self.current_iteration = 0

    def get_eta(self, current_progress):
        run_time = timer() - self.start_time
        return round(run_time / current_progress * (100 - current_progress))

    @property
    def current_progress(self):
        return int((self.current_iteration / self.total_iterations) * 100)

    @property
    def eta(self):
        run_time = timer() - self.start_time
        return round(run_time / self.current_progress * (100 - self.current_progress))

    def log_progress(self):
        reasons_to_skip = [
            not self.logger,
            not self.current_iteration > 0,
            self.total_iterations <= self.progress_step,
        ]
        if any(reasons_to_skip):
            return

        if self.current_progress >= self.last_logged_progress + self.progress_step:
            msg = (
                f"Progress: {self.current_progress}% "
                f"({self.current_iteration}/{self.total_iterations})"
            )
            if eta := self.eta:
                msg += f" ETA: {humanize_time(eta)}"

            self.logger(msg)
            self.last_logged_progress = self.current_progress

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def iter(self, iterator):
        for item in iterator:
            self.current_iteration += 1
            self.log_progress()
            yield item

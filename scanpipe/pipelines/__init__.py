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

import inspect
import logging
import timeit
import traceback
import warnings
from contextlib import contextmanager
from functools import wraps
from pydoc import getdoc
from pydoc import splitdoc

from django.utils import timezone

from pyinstrument import Profiler

logger = logging.getLogger(__name__)


class Pipeline:
    """Base class for all pipelines."""

    def __init__(self, run):
        """Load the Run and Project instances."""
        self.run = run
        self.project = run.project
        self.pipeline_name = run.pipeline_name

    @classmethod
    def steps(cls):
        raise NotImplementedError

    @classmethod
    def get_steps(cls):
        """
        Raise a deprecation warning when the steps are defined as a tuple instead of
        a classmethod.
        """
        if callable(cls.steps):
            return cls.steps()

        warnings.warn(
            f"Defining ``steps`` as a tuple is deprecated in {cls} "
            f"Use a ``steps(cls)`` classmethod instead."
        )
        return cls.steps

    @classmethod
    def get_doc(cls):
        """Get the doc string of this pipeline."""
        return getdoc(cls)

    @classmethod
    def get_graph(cls):
        """Return a graph of steps."""
        return [
            {"name": step.__name__, "doc": getdoc(step)} for step in cls.get_steps()
        ]

    @classmethod
    def get_info(cls):
        """Get a dictionary of combined information data about this pipeline."""
        summary, description = splitdoc(cls.get_doc())
        return {
            "summary": summary,
            "description": description,
            "steps": cls.get_graph(),
        }

    @classmethod
    def get_summary(cls):
        """Get the doc string summary."""
        return cls.get_info()["summary"]

    def log(self, message):
        """Log the given `message` to the current module logger and Run instance."""
        now_as_localtime = timezone.localtime(timezone.now())
        timestamp = now_as_localtime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
        message = f"{timestamp} {message}"
        logger.info(message)
        self.run.append_to_log(message, save=True)

    def execute(self):
        """Execute each steps in the order defined on this pipeline class."""
        self.log(f"Pipeline [{self.pipeline_name}] starting")
        steps = self.get_steps()
        steps_count = len(steps)

        for current_index, step in enumerate(steps, start=1):
            step_name = step.__name__

            # The `current_step` value is saved in the DB during the `self.log` call.
            self.run.current_step = f"{current_index}/{steps_count} {step_name}"[:256]

            self.log(f"Step [{step_name}] starting")
            start_time = timeit.default_timer()

            try:
                step(self)
            except Exception as e:
                self.log("Pipeline failed")
                tb = "".join(traceback.format_tb(e.__traceback__))
                return 1, f"{e}\n\nTraceback:\n{tb}"

            run_time = timeit.default_timer() - start_time
            self.log(f"Step [{step.__name__}] completed in {run_time:.2f} seconds")

        self.run.current_step = ""
        self.log("Pipeline completed")

        return 0, ""

    def add_error(self, error):
        """Create a `ProjectError` record on the current `project`."""
        self.project.add_error(error, model=self.pipeline_name)

    @contextmanager
    def save_errors(self, *exceptions):
        """
        Context manager to save specified exceptions as `ProjectError` in the database.

        Example in a Pipeline step:

        with self.save_errors(rootfs.DistroNotFound):
            rootfs.scan_rootfs_for_system_packages(self.project, rfs)
        """
        try:
            yield
        except exceptions as error:
            self.add_error(error)


def is_pipeline(obj):
    """
    Return True if the `obj` is a subclass of `Pipeline` except for the
    `Pipeline` class itself.
    """
    return inspect.isclass(obj) and issubclass(obj, Pipeline) and obj is not Pipeline


def profile(step):
    """
    Profile a Pipeline step and save the results as HTML file in the project output
    directory.

    Usage:
        @profile
        def step(self):
            pass
    """

    @wraps(step)
    def wrapper(*arg, **kwargs):
        pipeline_instance = arg[0]
        project = pipeline_instance.project

        with Profiler() as profiler:
            result = step(*arg, **kwargs)

        output_file = project.get_output_file_path("profile", "html")
        output_file.write_text(profiler.output_html())

        pipeline_instance.log(f"Profiling results at {output_file.resolve()}")

        return result

    return wrapper

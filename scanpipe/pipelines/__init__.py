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

import ast
import importlib
import inspect
import subprocess
import sys
from contextlib import contextmanager

from metaflow import FlowSpec
from metaflow import Parameter
from metaflow import step
from metaflow.graph import FlowGraph
from metaflow.graph import StepVisitor


class Pipeline(FlowSpec):
    """
    Base class for all Pipelines.
    """

    project_name = Parameter("project", help="Project name.", required=True)

    @staticmethod
    def get_project(name):
        """
        Return the project instance from the database.
        """
        from scanpipe.models import Project

        return Project.objects.get(name=name)

    @contextmanager
    def save_errors(self, *exceptions):
        """
        Context manager to save specified exceptions as `ProjectError` in the database.

        Example in a Pipeline step:

        with self.save_errors(ScancodeError):
            run_scancode()
        """
        try:
            yield
        except exceptions as error:
            self.project.add_error(error, model=self.__class__.__name__)


class PipelineGraph(FlowGraph):
    """
    Add ability to load a Graph directly from the Pipeline class without the
    `__main__` wrapping.
    """

    def _create_nodes(self, pipeline):
        """
        Using `importlib.import_module` in place of `__import__` to get the
        proper module.
        """
        module = importlib.import_module(pipeline.__module__)
        tree = ast.parse(inspect.getsource(module)).body
        class_defs = [
            n for n in tree if isinstance(n, ast.ClassDef) and n.name == self.name
        ]
        root = class_defs[0]
        nodes = {}
        StepVisitor(nodes, pipeline).visit(root)
        return nodes

    def output_dot(self, direction="TB", simplify=False):
        """
        Add the ability to customize the dot output.
        """
        output = super().output_dot()

        if direction:
            output = output.replace("rankdir=LR;", f"rankdir={direction};")

        if simplify:
            output = output.replace(' | <font point-size="10">linear</font>', "")
            output = output.replace(' | <font point-size="10">end</font>', "")

        return output


def is_pipeline_subclass(obj):
    """
    Return True if the `obj` is a subclass of `Pipeline` except for the
    `Pipeline` class itself.
    """
    return inspect.isclass(obj) and issubclass(obj, Pipeline) and obj is not Pipeline


def get_pipeline_class(pipeline_location):
    """
    Return the Pipeline subclass of the provided `pipeline_location`.
    """
    module_name = pipeline_location.replace(".py", "").replace("/", ".")
    module = importlib.import_module(module_name)
    module_classes = inspect.getmembers(module, is_pipeline_subclass)
    _, pipeline_class = [cls for cls in module_classes][0]

    return pipeline_class


def get_pipeline_doc(pipeline_location):
    """
    Return the provided `pipeline_location` documentation from the docstrings.
    """
    pipeline_class = get_pipeline_class(pipeline_location)
    pipeline_graph = PipelineGraph(pipeline_class)
    return pipeline_graph.doc


def get_pipeline_description(pipeline_location):
    """
    Return the structure of the flow, as returned by the `show` command.
    """
    cmd = f"{sys.executable} {pipeline_location} show"
    description = subprocess.getoutput(cmd)
    return description

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

"""
Support for JVM-specific file formats such as
.class and .java, .scala and .kotlin files.
"""

import re
from pathlib import Path
from re import Pattern

from scanpipe.pipes import scancode


class JvmLanguage:
    # Name of the JVM language like java, kotlin or scala, just as an FYI
    name: str = None
    # Tuple of source file extensions
    source_extensions: tuple = tuple()
    # Tuple of binary file extensions
    binary_extensions: tuple = (".class",)
    # Like java_package, kotlin_package, scala_package, used as an attribute in resource
    source_package_attribute_name: str = None
    # A regex pattern to extract a package from a source file
    package_regex: Pattern = None
    # Type of relation for a binary file to its source file
    binary_map_type: str = None

    @classmethod
    def get_source_package(cls, location, **kwargs):
        """
        Read the source file at ``location`` and return a source package for this
        language as a mapping with a single key using the value of
        ``source_package_attribute_name`` as a key name or None.

        Note: this is the same API as a ScanCode Toolkit API scanner function by
        design.
        """
        if not location:
            return

        if not isinstance(location, Path):
            location = Path(location)

        if location.suffix not in cls.source_extensions:
            return

        with open(location) as lines:
            return cls.find_source_package(lines)

    @classmethod
    def find_source_package(cls, lines):
        package = find_expression(lines=lines, regex=cls.package_regex)
        if package:
            return {cls.source_package_attribute_name: package}

    @classmethod
    def scan_for_source_package(cls, location, with_threading=True):
        """
        Run a Jvm source package scan on the file at ``location``.

        Return a mapping of scan ``results`` and a list of ``errors``.
        """
        scanners = [
            scancode.Scanner(
                name=f"{cls.source_package_attribute_name}",
                function=cls.get_source_package,
            )
        ]
        return scancode._scan_resource(
            location=location, scanners=scanners, with_threading=with_threading
        )

    @classmethod
    def get_indexable_qualified_paths(cls, from_resources_dot_java):
        """
        Yield tuples of (resource id, fully-qualified class name) for indexable
        classes from the "from/" side of the project codebase using the
        "java_package" Resource.extra_data.
        """
        resource_values = from_resources_dot_java.values_list(
            "id", "name", "extra_data"
        )
        return cls.get_indexable_qualified_paths_from_values(resource_values)

    @classmethod
    def get_indexable_qualified_paths_from_values(cls, resource_values):
        """
        Yield tuples of (resource id, fully-qualified path) for indexable
        classes from a list of ``resource_data`` tuples of "from/" side of the
        project codebase.

        These ``resource_data`` input tuples are in the form:
            (resource.id, resource.name, resource.extra_data)

        And the output tuples look like this example::
            (123, "org/apache/commons/LoggerImpl.java")
        """
        for resource_id, resource_name, resource_extra_data in resource_values:
            fully_qualified = get_fully_qualified_path(
                jvm_package=resource_extra_data.get(cls.source_package_attribute_name),
                filename=resource_name,
            )
            yield resource_id, fully_qualified

    @classmethod
    def get_normalized_path(cls, path, extension):
        """
        Return a normalized JVM file path for ``path`` .class file path string.
        Account for inner classes in that their file name is the name of their
        outer class.
        """
        if not path.endswith(cls.binary_extensions):
            raise ValueError(
                f"Only path ending with {cls.binary_extensions} are supported."
            )
        path = Path(path.strip("/"))
        class_name = path.name
        if "$" in class_name:  # inner class
            class_name, _, _ = class_name.partition("$")
        else:
            class_name, _, _ = class_name.partition(".")  # plain .class
        return str(path.parent / f"{class_name}{extension}")


def find_expression(lines, regex):
    """
    Return a value found using ``regex`` in the first 500 ``lines`` or ``None``.
    For example::

        >>> lines = ["   package    foo.back ;  # dsasdasdasdasdasda.asdasdasd"]
        >>> regex = java_package_re
        >>> assert find_expression(lines, regex) == "foo.back"
    """
    for ln, line in enumerate(lines):
        # only look at the first 500 lines
        if ln > 500:
            return
        for value in regex.findall(line):
            if value:
                return value


class JavaLanguage(JvmLanguage):
    name = "java"
    source_extensions = (".java",)
    binary_extensions = (".class",)
    source_package_attribute_name = "java_package"
    package_regex = re.compile(r"^\s*package\s+([\w\.]+)\s*;")
    binary_map_type = "java_to_class"


class ScalaLanguage(JvmLanguage):
    name = "scala"
    source_extensions = (".scala",)
    binary_extensions = (".class",)
    source_package_attribute_name = "scala_package"
    package_regex = re.compile(r"^\s*package\s+([\w\.]+)\s*;?")
    binary_map_type = "scala_to_class"


class KotlinLanguage(JvmLanguage):
    name = "kotlin"
    source_extensions = (".kt", ".kts")
    binary_extensions = (".class",)
    source_package_attribute_name = "kotlin_package"
    package_regex = re.compile(r"^\s*package\s+([\w\.]+)\s*;?")
    binary_map_type = "kotlin_to_class"

    @classmethod
    def get_normalized_path(cls, path, extension):
        """
        Return a normalized JVM file path for ``path`` .class file path string.
        Account for inner classes in that their file name is the name of their
        outer class.
        """
        if not path.endswith(cls.binary_extensions):
            raise ValueError(
                f"Only path ending with {cls.binary_extensions} are supported."
            )
        path = Path(path.strip("/"))
        class_name = path.name
        if "$" in class_name:  # inner class
            class_name, _, _ = class_name.partition("$")
        else:
            class_name, _, _ = class_name.partition(".")  # plain .class
        class_name = class_name.removesuffix("Kt")
        return str(path.parent / f"{class_name}{extension}")


def get_fully_qualified_path(jvm_package, filename):
    """
    Return a fully qualified path of a ``filename`` in a
    string.
    Note that we use "/" as path separators.

    For example::

        >>> get_fully_qualified_path("org.common" , "Bar.java")
        'org/common/Bar.java'
    """
    jvm_package = jvm_package.replace(".", "/")
    return f"{jvm_package}/{filename}"

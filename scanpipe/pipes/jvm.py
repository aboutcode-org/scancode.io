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

"""Support for JVM-specific file formats such as .class and .java files."""

import re
from pathlib import Path

java_package_re = re.compile(r"^\s*package\s+([\w\.]+)\s*;")


def get_java_package(location, java_extensions=(".java",), **kwargs):
    """
    Return a Java package as a mapping with a single "java_package" key, or ``None``
    from the .java source code file at ``location``.

    Only look at files with an extension in the ``java_extensions`` tuple.

    Note: this is the same API as a ScanCode Toolkit API scanner function by
    design.
    """
    if not location:
        return

    if not isinstance(location, Path):
        location = Path(location)

    if location.suffix not in java_extensions:
        return

    with open(location) as lines:
        return find_java_package(lines)


def find_java_package(lines):
    """
    Return a mapping of ``{'java_package': <value>}`` or ``None`` from an iterable or
    text ``lines``.

    For example::

        >>> lines = ["   package    foo.back ;  # dsasdasdasdasdasda.asdasdasd"]
        >>> assert find_java_package(lines) == {"java_package": "foo.back"}
    """
    package = _find_java_package(lines)
    if package:
        return {"java_package": package}


def _find_java_package(lines):
    """
    Return a Java package or ``None`` from an iterable or text ``lines``.

    For example::

        >>> lines = ["   package    foo.back ;  # dsasdasdasdasdasda.asdasdasd"]
        >>> assert _find_java_package(lines) == "foo.back", _find_java_package(lines)
    """
    for ln, line in enumerate(lines):
        # only look at the first 500 lines
        if ln > 500:
            return
        for package in java_package_re.findall(line):
            if package:
                return package


def get_normalized_java_path(path):
    """
    Return a normalized .java file path for ``path`` .class file path string.
    Account for inner classes in that their .java file name is the name of their
    outer class.

    For example::

        >>> get_normalized_java_path("foo/org/common/Bar$inner.class")
        'foo/org/common/Bar.java'
        >>> get_normalized_java_path("foo/org/common/Bar.class")
        'foo/org/common/Bar.java'
    """
    if not path.endswith(".class"):
        raise ValueError("Only path ending with .class are supported.")
    path = Path(path.strip("/"))
    class_name = path.name
    if "$" in class_name:  # inner class
        class_name, _, _ = class_name.partition("$")
    else:
        class_name, _, _ = class_name.partition(".")  # plain .class
    return str(path.parent / f"{class_name}.java")


def get_fully_qualified_java_path(java_package, filename):
    """
    Return a fully qualified java path of a .java ``filename`` in a
    ``java_package`` string.
    Note that we use "/" as path separators.

    For example::

        >>> get_fully_qualified_java_path("org.common" , "Bar.java")
        'org/common/Bar.java'
    """
    java_package = java_package.replace(".", "/")
    return f"{java_package}/{filename}"

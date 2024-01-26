#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

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

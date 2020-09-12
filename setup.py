#!/usr/bin/env python
# -*- encoding: utf-8 -*-

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

from setuptools import find_packages
from setuptools import setup

__version__ = "1.0.1"

requirement_files = ["etc/requirements/base.txt"]

all_requirements = [
    r.strip()
    for req_file in requirement_files
    for r in open(req_file).readlines()
    if r.strip() and not r.strip().startswith("#")
]

setup(
    name="scancodeio",
    version=__version__,
    license="Apache-2.0",
    description="ScanCode.io",
    long_description="ScanCode.io",
    author="nexB Inc.",
    author_email="info@scancode.io",
    url="https://github.com/nexB/scancode.io",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[],
    keywords=["scancode"],
    install_requires=all_requirements,
)

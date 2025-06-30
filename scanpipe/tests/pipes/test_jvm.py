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

from pathlib import Path
from unittest import TestCase

from scanpipe.pipes import jvm

java_code = """
/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache license, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the license for the specific language governing permissions and
 * limitations under the license.
 */
package org.apache.logging.log4j.core;

import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
"""

java_package_too_far_down = ("\n" * 501) + "package org.apache.logging.log4j.core;"


class ScanPipeJvmTest(TestCase):
    data = Path(__file__).parent.parent / "data"

    def test_scanpipe_pipes_jvm_find_java_package(self):
        package = jvm.find_java_package(java_code.splitlines())
        self.assertEqual({"java_package": "org.apache.logging.log4j.core"}, package)

    def test_scanpipe_pipes_jvm_find_java_package_with_spaces(self):
        lines = ["   package    foo.back ;  # dsasdasdasdasdasda.asdasdasd"]
        package = jvm.find_java_package(lines)
        self.assertEqual({"java_package": "foo.back"}, package)

    def test_scanpipe_pipes_jvm_find_java_package_return_None(self):
        package = jvm.find_java_package(java_package_too_far_down.splitlines())
        self.assertIsNone(package)

    def test_scanpipe_pipes_jvm_get_java_package(self):
        input_location = self.data / "jvm" / "common.java"
        package = jvm.get_java_package(input_location)
        self.assertEqual({"java_package": "org.apache.logging.log4j.core"}, package)

    def test_scanpipe_pipes_jvm_get_java_package_with_string(self):
        input_location = self.data / "jvm" / "common.java"
        package = jvm.get_java_package(str(input_location))
        self.assertEqual({"java_package": "org.apache.logging.log4j.core"}, package)

    def test_scanpipe_pipes_jvm_get_java_package_too_far_down(self):
        input_location = self.data / "jvm" / "no-package.java"
        package = jvm.get_java_package(input_location)
        self.assertIsNone(package)

    def test_scanpipe_pipes_jvm_get_normalized_java_path(self):
        njp = jvm.get_normalized_java_path("foo/org/common/Bar.class")
        self.assertEqual("foo/org/common/Bar.java", njp)

    def test_scanpipe_pipes_jvm_get_normalized_java_path_with_inner_class(self):
        njp = jvm.get_normalized_java_path("foo/org/common/Bar$inner.class")
        self.assertEqual("foo/org/common/Bar.java", njp)

    def test_scanpipe_pipes_jvm_get_fully_qualified_java_path(self):
        fqjp = jvm.get_fully_qualified_java_path("org.common", "Bar.java")
        self.assertEqual("org/common/Bar.java", fqjp)

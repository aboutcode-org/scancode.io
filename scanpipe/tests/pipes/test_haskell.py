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

from django.test import TestCase

from scanpipe.pipes import haskell


class HaskellTest(TestCase):
    def test_strip_extension_picks_longest_match(self):
        self.assertEqual(
            "Foo",
            haskell.strip_extension("Foo.p_hi", (".p_hi", ".hi")),
        )
        self.assertEqual(
            "Foo",
            haskell.strip_extension("Foo.hi", (".p_hi", ".hi")),
        )
        self.assertEqual(
            "Foo",
            haskell.strip_extension("Foo.o-boot", (".o-boot", ".o")),
        )
        self.assertEqual(
            "Foo.o",
            haskell.strip_extension("Foo.o", (".o-boot",)),
        )

    def test_get_module_path_from_source(self):
        self.assertEqual(
            "from/Database/TxtSushi/CommandLineArgument",
            haskell.get_module_path_from_source(
                "from/Database/TxtSushi/CommandLineArgument.hs"
            ),
        )
        self.assertEqual(
            "from/Foo",
            haskell.get_module_path_from_source("from/Foo.lhs"),
        )
        self.assertEqual(
            "from/Bar",
            haskell.get_module_path_from_source("from/Bar.hs-boot"),
        )

    def test_get_module_path_from_path_artifact(self):
        for extension in haskell.PATH_MAPPING_EXTENSIONS:
            self.assertEqual(
                "to/Database/TxtSushi/CommandLineArgument",
                haskell.get_module_path_from_path_artifact(
                    f"to/Database/TxtSushi/CommandLineArgument{extension}"
                ),
                f"failed for {extension}",
            )

    def test_get_basename_from_basename_artifact(self):
        for extension in haskell.BASENAME_MAPPING_EXTENSIONS:
            self.assertEqual(
                "CommandLineArgument",
                haskell.get_basename_from_basename_artifact(
                    f"to/out/libHSfoo.a-extract/CommandLineArgument{extension}"
                ),
                f"failed for {extension}",
            )

    def test_get_indexable_module_paths(self):
        resource_values = [
            (1, "from/Database/TxtSushi/CommandLineArgument.hs"),
            (2, "from/Foo.lhs"),
            (3, "from/Bar.hs-boot"),
        ]
        expected = [
            (1, "from/Database/TxtSushi/CommandLineArgument"),
            (2, "from/Foo"),
            (3, "from/Bar"),
        ]
        results = list(haskell.get_indexable_module_paths(resource_values))
        self.assertEqual(expected, results)

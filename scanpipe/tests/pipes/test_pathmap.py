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

from typing import NamedTuple

from django.test import TestCase

from scanpipe.pipes import pathmap
from scanpipe.pipes.pathmap import Match


def convert_ids_to_paths(match, paths_by_id):
    """
    Replace the Match ``match`` list of resource_ids by tuples of (id, path)
    given a mapping of ``paths_by_id`` as {id: path string}. Return the match.
    Used to ease reviewing and debugging tests.
    """
    rids = match.resource_ids
    for i, rid in enumerate(
        rids,
    ):
        rids[i] = (rid, paths_by_id[rid])
    return match


class IndexEntry(NamedTuple):
    indexed_path: str
    match: Match


class ScanPipePathmapPipesTest(TestCase):
    maxDiff = None

    def test_scanpipe_pipes_pathmap_build_index(self):
        resource_id_and_paths = (
            (1, "RouterStub.java"),
            (2, "samples/screenshot.png"),
            (3, "samples/JGroups/src/RouterStub.java"),
            (4, "src/screenshot.png"),
            (5, "samples/file.class"),
            (6, "samples/json"),
        )
        paths_by_id = dict(resource_id_and_paths)
        index = pathmap.build_index(resource_id_and_paths)
        index_entries = []
        for indexed_path, (matched_path_length, resource_ids) in index.items():
            match = Match(matched_path_length, resource_ids)
            convert_ids_to_paths(match, paths_by_id)
            entry = IndexEntry(indexed_path=indexed_path, match=match)
            index_entries.append(entry)

        expected = [
            IndexEntry(
                indexed_path="/json/",
                match=Match(matched_path_length=1, resource_ids=[(6, "samples/json")]),
            ),
            IndexEntry(
                indexed_path="/json/samples/",
                match=Match(matched_path_length=2, resource_ids=[(6, "samples/json")]),
            ),
            IndexEntry(
                indexed_path="/file.class/",
                match=Match(
                    matched_path_length=1, resource_ids=[(5, "samples/file.class")]
                ),
            ),
            IndexEntry(
                indexed_path="/file.class/samples/",
                match=Match(
                    matched_path_length=2, resource_ids=[(5, "samples/file.class")]
                ),
            ),
            IndexEntry(
                indexed_path="/screenshot.png/",
                match=Match(
                    matched_path_length=1,
                    resource_ids=[
                        (2, "samples/screenshot.png"),
                        (4, "src/screenshot.png"),
                    ],
                ),
            ),
            IndexEntry(
                indexed_path="/screenshot.png/src/",
                match=Match(
                    matched_path_length=2, resource_ids=[(4, "src/screenshot.png")]
                ),
            ),
            IndexEntry(
                indexed_path="/screenshot.png/samples/",
                match=Match(
                    matched_path_length=2, resource_ids=[(2, "samples/screenshot.png")]
                ),
            ),
            IndexEntry(
                indexed_path="/RouterStub.java/",
                match=Match(
                    matched_path_length=1,
                    resource_ids=[
                        (1, "RouterStub.java"),
                        (3, "samples/JGroups/src/RouterStub.java"),
                    ],
                ),
            ),
            IndexEntry(
                indexed_path="/RouterStub.java/src/",
                match=Match(
                    matched_path_length=2,
                    resource_ids=[(3, "samples/JGroups/src/RouterStub.java")],
                ),
            ),
            IndexEntry(
                indexed_path="/RouterStub.java/src/JGroups/",
                match=Match(
                    matched_path_length=3,
                    resource_ids=[(3, "samples/JGroups/src/RouterStub.java")],
                ),
            ),
            IndexEntry(
                indexed_path="/RouterStub.java/src/JGroups/samples/",
                match=Match(
                    matched_path_length=4,
                    resource_ids=[(3, "samples/JGroups/src/RouterStub.java")],
                ),
            ),
        ]
        self.assertEqual(expected, index_entries)

    def test_scanpipe_pipes_pathmap_find_paths(self):
        resource_id_and_paths = (
            (1, "RouterStub.java"),
            (2, "samples/screenshot.png"),
            (3, "samples/JGroups/src/RouterStub.java"),
            (4, "src/screenshot.png"),
            (5, "samples/file.class"),
            (6, "samples/json"),
        )

        index = pathmap.build_index(resource_id_and_paths)

        lookup_path = "src/RouterStub.java"
        match = pathmap.find_paths(lookup_path, index)
        expected = Match(matched_path_length=2, resource_ids=[3])
        self.assertEqual(expected, match)

    def test_scanpipe_pipes_pathmap_find_paths_without_subpath_index(self):
        resource_id_and_paths = (
            (1, "RouterStub.java"),
            (2, "samples/screenshot.png"),
            (3, "samples/JGroups/src/RouterStub.java"),
            (4, "src/screenshot.png"),
            (5, "samples/file.class"),
            (6, "samples/json"),
        )

        index = pathmap.build_index(resource_id_and_paths, with_subpaths=False)

        lookup_path = "other/src/RouterStub.java"
        match = pathmap.find_paths(lookup_path, index)
        expected = Match(matched_path_length=1, resource_ids=[1])
        self.assertEqual(expected, match)

        lookup_path = "RouterStub.java"
        match = pathmap.find_paths(lookup_path, index)
        expected = Match(matched_path_length=1, resource_ids=[1])
        self.assertEqual(expected, match)

    def test_scanpipe_pipes_pathmap_find_paths_whole_path_without_subpath_index(self):
        resource_id_and_paths = (
            (1, "org/apache/commons/RouterStub.java"),
            (2, "org/apache/commons/Food.java"),
            (3, "org/apache/jakarta/Food.java"),
            (4, "com/company/foo/Foo.java"),
            (5, "org/apache/commons/bar/Food.java"),
        )
        index = pathmap.build_index(resource_id_and_paths, with_subpaths=False)

        lookup_path = "org/apache/commons/Food.java"
        match = pathmap.find_paths(lookup_path, index)
        expected = Match(matched_path_length=4, resource_ids=[2])
        self.assertEqual(expected, match)

        lookup_path = "apache/commons/Food.java"
        match = pathmap.find_paths(lookup_path, index)
        self.assertIsNone(match)

    def test_scanpipe_pipes_pathmap_find_paths_with_subpath_index(self):
        resource_id_and_paths = (
            (1, "RouterStub.java"),
            (2, "samples/screenshot.png"),
            (3, "samples/JGroups/src/RouterStub.java"),
            (4, "src/screenshot.png"),
            (5, "samples/file.class"),
            (6, "samples/json"),
        )

        index = pathmap.build_index(resource_id_and_paths, with_subpaths=True)

        lookup_path = "other/src/RouterStub.java"
        match = pathmap.find_paths(lookup_path, index)
        expected = Match(matched_path_length=2, resource_ids=[3])
        self.assertEqual(expected, match)

        lookup_path = "RouterStub.java"
        match = pathmap.find_paths(lookup_path, index)
        expected = Match(matched_path_length=1, resource_ids=[1, 3])
        self.assertEqual(expected, match)

    def test_scanpipe_pipes_pathmap_find_paths_does_not_return_false_matches1(self):
        resource_id_and_paths = (
            (1, "RouterStub.java"),
            (2, "samples/screenshot.png"),
            (3, "samples/JGroups/src/RouterStub.java"),
            (4, "src/screenshot.png"),
            (5, "samples/file.class"),
            (6, "samples/json"),
        )

        index = pathmap.build_index(resource_id_and_paths)

        lookup_path = "samples/JGroups/src/File.ext"
        match = pathmap.find_paths(lookup_path, index)
        self.assertIsNone(match)

    def test_scanpipe_pipes_pathmap_find_paths_no_false_matches_without_subpath(self):
        resource_id_and_paths = (
            (1, "RouterStub.java"),
            (2, "samples/screenshot.png"),
            (3, "samples/JGroups/src/RouterStub.java"),
            (4, "src/screenshot.png"),
            (5, "samples/file.class"),
            (6, "samples/json"),
        )

        index = pathmap.build_index(resource_id_and_paths, with_subpaths=False)

        lookup_path = "json/subpath/file.class"
        match = pathmap.find_paths(lookup_path, index)
        self.assertIsNone(match)

    def test_scanpipe_pipes_pathmap_find_paths_matches_with_subpaths(self):
        resource_id_and_paths = (
            (1, "RouterStub.java"),
            (2, "samples/screenshot.png"),
            (3, "samples/JGroups/src/RouterStub.java"),
            (4, "src/screenshot.png"),
            (5, "samples/file.class"),
            (6, "samples/json"),
        )

        index = pathmap.build_index(resource_id_and_paths, with_subpaths=True)

        lookup_path = "json/subpath/file.class"
        match = pathmap.find_paths(lookup_path, index)
        expected = Match(matched_path_length=1, resource_ids=[5])
        self.assertEqual(expected, match)

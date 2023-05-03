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

import ahocorasick

"""
Path matching using Aho-Corasick automatons. The approach is to create a trie of
all reversed path suffixes aka. subpath each mapped to a tuple of:
    (subpath length, [list of path ids]).

For instance with this list of paths, prefixed with a path id:

    1    RouterStub.java
    2    samples/screenshot.png
    3    samples/JGroups/src/RouterStub.java
    4    src/screenshot.png

We will create this list of subpaths:

    (RouterStub.java)
    (screenshot.png)
    (screenshot.png, samples)
    (RouterStub.java, JGroups, src, samples)
    (RouterStub.java, JGroups, src)
    (RouterStub.java, JGroups)
    (RouterStub.java)
    (screenshot.png)
    (screenshot.png, src)

And we will have this index style:

    (tuple of path segments) -> (number of segments, [list of path ids])
    (RouterStub.java) -> (1, [1, 3])
    (screenshot.png) -> (1, [2, 4])
    (screenshot.png, samples) -> (2, [2])
    (RouterStub.java, JGroups, src, samples) -> (4, [3])
    (RouterStub.java, JGroups, src) -> (3, [3])
    (RouterStub.java, JGroups) -> (3, [3])
    (screenshot.png, src) -> (2, [4])

Note that internally we first assign an integer if to each unique path segment
and work on sequence of integers rather than sequence of words.
"""


def get_matched_paths(path, index, id_by_segment):
    """
    Yield tuples of the longest paths matched in the ``automaton`` for a
    POSIX ``path`` string.
    """
    segment_ids = convert_path_to_segment_ids(path, id_by_segment)
    # note: we use iter_long() to get the longess match only.
    # use iter() to get all matches
    for _, matched_paths in index.iter_long(segment_ids):
        yield matched_paths


def build_index(paths_database):
    """
    Return an index as a tuple of (automaton, id_by_segment) built from a
    ``paths_database`` mapping of {path: path_id}
    """
    # create a new empty automaton.
    automaton = ahocorasick.Automaton(ahocorasick.STORE_ANY, ahocorasick.KEY_SEQUENCE)

    # assign and keep track of a int if for each unique path segment
    id_by_segment = build_segment_id_by_segment(paths_database)

    for path, path_id in paths_database.items():
        # we need int ids for our automaton
        segment_ids = convert_path_to_segment_ids(path, id_by_segment)
        for idx, _ in enumerate(segment_ids, 1):
            subpath = tuple(segment_ids[:idx])

            existing = automaton.get(subpath, None)
            if existing:
                # ensure that for identical sequence of segments (e.g., a path suffix)
                # added several times, all path_id(s) are added to the value list
                _len, path_ids = existing
                path_ids.append(path_id)
            else:
                automaton.add_word(subpath, (len(subpath), [path_id]))

    # "finalize" automaton
    automaton.make_automaton()
    return automaton, id_by_segment


def build_segment_id_by_segment(paths_database):
    """
    Return a mapping of {path_segment: int id} assigning a unique id to each
    unique path segment from a ``paths_database``.
    """
    unique_segments = set()
    for path in paths_database:
        segments = path.strip("/").split("/")
        unique_segments.update(segments)

    unique_segments = sorted(unique_segments)
    return {seg: sid for sid, seg in enumerate(unique_segments, 1)}


def get_reversed_segments(path):
    """Return a sequence of reversed path segments given a POSIX ``path`` string."""
    # [::-1] does the list reversing
    return path.strip("/").split("/")[::-1]


def convert_path_to_segment_ids(path, id_by_segment):
    """
    Return a sequence of reversed path segment int ids given a POSIX ``path``
    string. Use the ``id_by_segment`` mapping to convert segment strings to int
    ids.
    """
    try:
        return tuple(id_by_segment[seg] for seg in get_reversed_segments(path))
    except KeyError:
        return ()

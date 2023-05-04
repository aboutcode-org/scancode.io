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
Path matching using Aho-Corasick automatons.

The approach is to create a trie of all reversed path suffixes aka. subpath each
mapped to a tuple of:
    (subpath length, [list of path ids]).

And then search this using Aho-Corasick search.

For instance with this list of paths, prefixed with a path id:

    1    RouterStub.java
    23   samples/screenshot.png
    3    samples/JGroups/src/RouterStub.java
    42   src/screenshot.png

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

And we will have this index:

    (tuple of path segments) -> (number of segments, [list of path ids])
    (RouterStub.java) -> (1, [1, 3])
    (screenshot.png) -> (1, [23, 42])
    (screenshot.png, samples) -> (2, [23])
    (RouterStub.java, JGroups, src, samples) -> (4, [3])
    (RouterStub.java, JGroups, src) -> (3, [3])
    (RouterStub.java, JGroups) -> (3, [3])
    (screenshot.png, src) -> (2, [42])
"""


def find_paths(path, index):
    """
    Yield tuples of the longest paths matched in the ``automaton`` for a POSIX
    ``path`` string.

    Each tuple is (number of matched path segments, [list of resource ids])

    For example::
    >>> resource_id_and_paths = [
    ...     (1,  "RouterStub.java"),
    ...     (23, "samples/screenshot.png"),
    ...     (3,  "samples/JGroups/src/RouterStub.java"),
    ...     (42, "src/screenshot.png"),
    ... ]

    >>> index = build_index(resource_id_and_paths)

    >>> expected = [(3, [3])]
    >>> results = list(find_paths("JGroups/src/RouterStub.java", index))
    >>> assert results == expected, results

    >>> expected = [(1, [23, 42])]
    >>> results = list(find_paths("screenshot.png", index))
    >>> assert results == expected, results
    """
    segments = get_reversed_path_segments(path)
    reversed_path = convert_segments_to_path(segments)
    # We use iter_long() to get the longest match only. Use iter() to get all matches.
    for _, matched_len_and_paths in index.iter_long(reversed_path):
        yield matched_len_and_paths


def build_index(resource_id_and_paths):
    """
    Return an index (an automaton) built from a ``resource_id_and_paths``
    iterable of tuples of (resource_id int, resource_path string).
    """
    # create a new empty automaton.
    automaton = ahocorasick.Automaton(ahocorasick.STORE_ANY, ahocorasick.KEY_STRING)

    for resource_id, resource_path in resource_id_and_paths:
        segments = get_reversed_path_segments(resource_path)
        segments_count = len(segments)
        for segments_count in range(segments_count):
            subpath_segments_count = segments_count + 1
            subpath_segments = segments[:subpath_segments_count]
            subpath = convert_segments_to_path(subpath_segments)
            existing = automaton.get(subpath, None)
            if existing:
                # For multiple identical path suffixes, append to the list of
                # resource_ids
                _seg_count, resource_ids = existing
                resource_ids.append(resource_id)
            else:
                # We store this value mapped to a subpath as a tuple of
                # (segments count, [list of resource ids])
                value = subpath_segments_count, [resource_id]
                automaton.add_word(subpath, value)

    automaton.make_automaton()
    return automaton


def get_reversed_path_segments(path):
    """
    Return reversed segments list given a POSIX ``path`` string. We reverse
    based on path segments separated by a "/".

    Note that the inputh ``path`` is assumed to be normalized, not relative and
    not containing double slash.

    For example::
    >>> assert get_reversed_path_segments("a/b/c.js") == ["c.js", "b", "a"]
    """
    # [::-1] does the list reversing
    reversed_segments = path.strip("/").split("/")[::-1]
    return reversed_segments


def convert_segments_to_path(segments):
    """
    Return a path string is suitable for indexing or matching given a
    ``segments`` sequence of path segment strings.
    The resulting reversed path is prefixed and suffixed by a "/" irrespective
    of whether the original path is a file or directory and had such prefix or
    suffix.

    For example::
    >>> assert convert_segments_to_path(["c.js", "b", "a"]) == "/c.js/b/a/"
    """
    return "/" + "/".join(segments) + "/"

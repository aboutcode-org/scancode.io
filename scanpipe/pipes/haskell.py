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

SOURCE_EXTENSIONS = (
    ".hs",
    ".lhs",
    ".hs-boot",
    ".lhs-boot",
    ".hsig",
    ".lhsig",
)

# Extensions of Haskell artifacts in the deployed tree that keep the module
# path.
PATH_MAPPING_EXTENSIONS = (
    ".hi",
    ".p_hi",
    ".dyn_hi",
    ".hie",
    ".hi-boot",
    ".hie-boot",
    ".hc",
)

# Extensions of Haskell artifacts in the deployed tree whose paths
# are flattened by .a archives, leaving only the base filename.
BASENAME_MAPPING_EXTENSIONS = (
    ".o",
    ".p_o",
    ".dyn_o",
    ".debug_o",
    ".t_o",
    ".o-boot",
)

binary_map_type = "haskell_to_object"


def strip_extension(path, extensions):
    """
    Strip and return the longest matching extension from `path`.
    Returns `path` unchanged if no extension matches.

    Sorting by length first guarantees that `.p_hi` is stripped before
    `.hi`, and `.o-boot` before `.o`.
    """
    for extension in sorted(extensions, key=len, reverse=True):
        if path.endswith(extension):
            return path[: -len(extension)]
    return path


def get_module_path_from_source(path):
    """Return the module path of a Haskell source file."""
    return strip_extension(path, SOURCE_EXTENSIONS)


def get_module_path_from_path_artifact(path):
    """Return the module path recovered from a path-preserving artifact."""
    return strip_extension(path, PATH_MAPPING_EXTENSIONS)


def get_basename_from_basename_artifact(path):
    """Return the basename of an object artifact."""
    base_name = strip_extension(path, BASENAME_MAPPING_EXTENSIONS)
    return base_name.rsplit("/", 1)[-1]


def get_indexable_module_paths(resource_values):
    """
    Yield `(resource_id, module_path)` from ``(id, path)`` pairs with
    the source extension stripped.
    """
    for resource_id, path in resource_values:
        yield resource_id, get_module_path_from_source(path)

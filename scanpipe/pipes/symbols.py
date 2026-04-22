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

import os
import tempfile

from django.db.models import Q

from source_inspector import symbols_ctags
from source_inspector import symbols_pygments
from source_inspector import symbols_tree_sitter

from aboutcode.pipeline import LoopProgress
from scanpipe.pipes.fetch import fetch_http
from scanpipe.pipes.pathmap import build_index
from scanpipe.pipes.pathmap import find_paths
from scanpipe.pipes.symbolmap import MATCHING_RATIO_JAVASCRIPT
from scanpipe.pipes.symbolmap import MATCHING_RATIO_JAVASCRIPT_SMALL_FILE
from scanpipe.pipes.symbolmap import SMALL_FILE_SYMBOLS_THRESHOLD_JAVASCRIPT
from scanpipe.pipes.symbolmap import get_similarity_between_source_and_deployed_symbols


class UniversalCtagsNotFound(Exception):
    pass


def collect_and_store_resource_symbols_ctags(project, logger=None):
    """
    Collect symbols from codebase files using Ctags and store
    them in the extra data field.
    """
    from source_inspector import symbols_ctags

    if not symbols_ctags.is_ctags_installed():
        raise UniversalCtagsNotFound(
            "``Universal Ctags`` not found."
            "Install ``Universal Ctags`` to use this pipeline."
        )

    project_files = project.codebaseresources.files()

    resources = project_files.filter(
        is_binary=False,
        is_archive=False,
        is_media=False,
    )

    resources_count = resources.count()

    resource_iterator = resources.iterator(chunk_size=2000)
    progress = LoopProgress(resources_count, logger)

    for resource in progress.iter(resource_iterator):
        _collect_and_store_resource_symbols_ctags(resource)


def _collect_and_store_resource_symbols_ctags(resource):
    """
    Collect symbols from a resource using Ctags and store
    them in the extra data field.
    """
    from source_inspector import symbols_ctags

    symbols = symbols_ctags.collect_symbols(resource.location)
    tags = [symbol["name"] for symbol in symbols if "name" in symbol]
    resource.update_extra_data({"source_symbols": tags})


def collect_and_store_pygments_symbols_and_strings(project, logger=None):
    """
    Collect symbols, strings and comments from codebase files using pygments and store
    them in the extra data field.
    """
    project_files = project.codebaseresources.files()

    resources = project_files.filter(
        is_binary=False,
        is_archive=False,
        is_media=False,
    )

    resources_count = resources.count()

    resource_iterator = resources.iterator(chunk_size=2000)
    progress = LoopProgress(resources_count, logger)

    for resource in progress.iter(resource_iterator):
        _collect_and_store_pygments_symbols_and_strings(resource)


def _collect_and_store_pygments_symbols_and_strings(resource):
    """
    Collect symbols, strings and comments from a resource using pygments and store
    them in the extra data field.
    """
    from source_inspector import symbols_pygments

    result = symbols_pygments.get_pygments_symbols(resource.location)
    resource.update_extra_data(
        {
            "source_symbols": result.get("source_symbols"),
            "source_strings": result.get("source_strings"),
            "source_comments": result.get("source_comments"),
        }
    )


def collect_and_store_tree_sitter_symbols_and_strings(
    project, logger=None, project_files=None
):
    """
    Collect symbols from codebase files using tree-sitter and store
    them in the extra data field.

    Collect from `project_files` instead of all codebase files if specified.
    """
    from source_inspector import symbols_tree_sitter

    if not project_files:
        project_files = project.codebaseresources.files()

    language_qs = Q()

    for language in symbols_tree_sitter.TS_LANGUAGE_WHEELS.keys():
        language_qs |= Q(programming_language__iexact=language)

    resources = project_files.filter(
        is_binary=False,
        is_archive=False,
        is_media=False,
    ).filter(language_qs)

    resources_count = resources.count()
    if logger:
        logger(
            f"Getting source symbols and strings from {resources_count:,d}"
            " resources using tree-sitter."
        )

    resource_iterator = resources.iterator(chunk_size=2000)
    progress = LoopProgress(resources_count, logger)

    for resource in progress.iter(resource_iterator):
        try:
            _collect_and_store_tree_sitter_symbols_and_strings(resource)
        except Exception as e:
            project.add_error(
                description=f"Cannot collect strings from resource at {resource.path}",
                exception=e,
                model="collect_and_store_tree_sitter_symbols_and_strings",
                details={"resource_path": resource.path},
            )


def _collect_and_store_tree_sitter_symbols_and_strings(resource):
    """
    Collect symbols and string from a resource using tree-sitter and store
    them in the extra data field.
    """
    from source_inspector import symbols_tree_sitter

    result = symbols_tree_sitter.get_treesitter_symbols(resource.location)
    resource.update_extra_data(
        {
            "source_symbols": result.get("source_symbols"),
            "source_strings": result.get("source_strings"),
        }
    )


SYMBOLS_TYPE_SUPPORTED = {
    "ctags": symbols_ctags.get_symbols,
    "tree_sitter": symbols_tree_sitter.get_treesitter_symbols,
    "pygments": symbols_pygments.get_pygments_symbols,
}

DOC_EXTENSIONS = {
    ".md",
    ".rst",
    ".txt",
    ".html",
    ".pdf",
    ".wiki",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


def get_vulnerability_patch_text(vuln):
    # TODO this is a mock, we should delete this function once we migrate to v2 api vulnerablecode
    # https://files.pythonhosted.org/packages/99/ab/eedb921f26adf7057ade1291f9c1bfa35a506d64894f58546457ef658772/Flask-1.0.tar.gz

    patch_urls = [
        # VCID-z6fe-2j8a-aaak
        # "https://github.com/pallets/flask/commit/70f906c51ce49c485f1d355703e9cc3386b1cc2b.patch",
        # "https://github.com/pallets/flask/commit/afd63b16170b7c047f5758eb910c416511e9c965.patch",
        # VCID-e8hf-2zj4-1qhv
        "https://github.com/pallets/flask/commit/089cb86dd22bff589a4eafb7ab8e42dc357623b4.patch"
    ]

    for patch_url in patch_urls:
        file_path = fetch_http(patch_url).path
        with open(file_path) as f:
            patch_text = f.read()
            yield patch_text


def parse_patch_symbols(raw_code: str, path: str, symbols_type="tree_sitter") -> dict:
    if not raw_code or not raw_code.strip():
        return {}

    _, file_suffix = os.path.splitext(path)

    with tempfile.NamedTemporaryFile(mode="w+", suffix=file_suffix, delete=False) as f:
        f.write(raw_code)
        f.flush()
        temp_name = f.name

    try:
        parser_func = SYMBOLS_TYPE_SUPPORTED.get(symbols_type, lambda f: {})
        return parser_func(temp_name) or {}
    finally:
        os.remove(temp_name)


def get_patch_symbols(vulnerable_files: dict, fixed_files: dict, symbol_type) -> dict:
    symbols_results = {}
    all_file_paths = set(vulnerable_files.keys()) | set(fixed_files.keys())

    for file_path in all_file_paths:
        vuln_code = vulnerable_files.get(file_path, "")
        fixed_code = fixed_files.get(file_path, "")
        vuln_parsed = parse_patch_symbols(vuln_code, file_path, symbol_type)
        fixed_parsed = parse_patch_symbols(fixed_code, file_path, symbol_type)

        symbols_results[file_path] = {
            "vulnerable_symbols": vuln_parsed.get("source_symbols", []),
            "vulnerable_strings": vuln_parsed.get("source_strings", []),
            "fixed_symbols": fixed_parsed.get("source_symbols", []),
            "fixed_strings": fixed_parsed.get("source_strings", []),
        }
    return symbols_results


def _should_skip(file_path: str):
    file_name = os.path.basename(file_path)
    _, ext = os.path.splitext(file_name)

    if ext.lower() in DOC_EXTENSIONS:
        return True

    lower_name = file_name.lower()
    if (
        lower_name.startswith("test_")
        or lower_name.startswith("test")
        or "_test." in lower_name
    ):
        return True

    lower_path = file_path.lower()
    if "test/" in lower_path or "tests/" in lower_path or "/testdata/" in lower_path:
        return True

    return False


def extract_patch_details(patch_text: str):
    from unidiff import PatchSet

    patch = PatchSet(patch_text)
    vulnerable_files = {}
    fixed_files = {}

    for patched_file in patch:
        if _should_skip(patched_file.path):
            continue

        vuln_lines = []
        fixed_lines = []
        for hunk in patched_file:
            for line in hunk:
                if line.is_removed:
                    vuln_lines.append(line.value)
                elif line.is_added:
                    fixed_lines.append(line.value)

        if vuln_lines:
            vulnerable_files[patched_file.path] = "".join(vuln_lines)
        if fixed_lines:
            fixed_files[patched_file.path] = "".join(fixed_lines)

    return vulnerable_files, fixed_files


def collect_and_store_patch_symbols(project, symbol_type, logger=None):
    packages = project.discoveredpackages.all()
    packages_count = packages.count()

    if logger:
        logger(
            f"Collecting patch symbols for {packages_count:,d} discovered packages "
            "and computing reachability."
        )

    progress = LoopProgress(packages_count, logger)
    for package in progress.iter(packages.iterator(chunk_size=2000)):
        try:
            _collect_and_store_patch_symbols(project, package, symbol_type)
        except Exception as e:
            project.add_error(
                description=f"Cannot collect patch symbols for package {package.name}",
                exception=e,
                model="collect_and_store_patch_symbols",
                details={"package_uuid": str(package.uuid)},
            )


def calculate_reachability(source_symbols, vulnerable_symbols, fixed_symbols):
    is_vulnerable, vulnerable_similarity = (
        get_similarity_between_source_and_deployed_symbols(
            source_symbols=source_symbols,
            deployed_symbols=vulnerable_symbols,
            matching_ratio=MATCHING_RATIO_JAVASCRIPT,
            matching_ratio_small_file=MATCHING_RATIO_JAVASCRIPT_SMALL_FILE,
            small_file_threshold=SMALL_FILE_SYMBOLS_THRESHOLD_JAVASCRIPT,
        )
    )

    is_fixed, fixed_similarity = get_similarity_between_source_and_deployed_symbols(
        source_symbols=source_symbols,
        deployed_symbols=fixed_symbols,
        matching_ratio=MATCHING_RATIO_JAVASCRIPT,
        matching_ratio_small_file=MATCHING_RATIO_JAVASCRIPT_SMALL_FILE,
        small_file_threshold=SMALL_FILE_SYMBOLS_THRESHOLD_JAVASCRIPT,
    )

    return {
        "is_vulnerable_matched": is_vulnerable,
        "vulnerable_similarity": vulnerable_similarity,
        "is_fixed_matched": is_fixed,
        "fixed_similarity": fixed_similarity,
        "is_reachable": vulnerable_similarity >= fixed_similarity,
    }


def _collect_and_store_patch_symbols(project, package, symbol_type):
    vulnerabilities = package.affected_by_vulnerabilities

    resource_data = project.codebaseresources.values_list("id", "path")
    path_index = build_index(resource_data, with_subpaths=True)

    for vuln in vulnerabilities:
        # TODO fix this to after done with vulnerablecode migration to advisories and merge patch API
        for patch_text in get_vulnerability_patch_text(vuln):
            if not patch_text or not patch_text.strip():
                continue

            vulnerable_files, fixed_files = extract_patch_details(patch_text)
            patch_symbols_data = get_patch_symbols(
                vulnerable_files, fixed_files, symbol_type
            )
            for file_path, patch_symbols in patch_symbols_data.items():
                match = find_paths(file_path, path_index)
                matched_resources = project.codebaseresources.filter(
                    id__in=match.resource_ids
                )
                if not matched_resources:
                    print(f"Failed to get the code base resources: {file_path}")
                    continue

                for resource in matched_resources:
                    resource_symbols = resource.extra_data.get("source_symbols", [])
                    vulnerable_symbols = patch_symbols.get("vulnerable_symbols", [])
                    fixed_symbols = patch_symbols.get("fixed_symbols", [])

                    reachability_percentage = calculate_reachability(
                        resource_symbols, vulnerable_symbols, fixed_symbols
                    )
                    resource.update_extra_data(
                        {
                            "vulnerable_symbols": vulnerable_symbols,
                            "fixed_symbols": fixed_symbols,
                            "reachability": reachability_percentage,
                        }
                    )

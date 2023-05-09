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

import difflib
import hashlib
import json
from pathlib import Path
from timeit import default_timer as timer

from django.db.models import Q

from scanpipe import pipes
from scanpipe.models import CodebaseRelation
from scanpipe.pipes import flag
from scanpipe.pipes import jvm
from scanpipe.pipes import pathmap
from scanpipe.pipes import purldb
from scanpipe.pipes import scancode

FROM = "from/"
TO = "to/"

IGNORED_FILENAMES = ("packageinfo", "package-info.java", "package-info.class")
IGNORED_EXTENSIONS = ()
IGNORED_PATHS = ("gradleTest/",)

"""
`PROSPECTIVE_JAVASCRIPT_MAP` maps source file extensions to a list of dict
that specifies extension of transformed files. The `to_minified_ext` key in
each dict specifies the file extension of the transformed minified file, and
the `to_related` key specifies the related file extensions that are generated
alongside the transformed file (inclusive of minified file extension).
For example, the `.scss` key maps to a list of two dict. The first dict
specifies that `.scss` file is transformed into minified `.css` files along
with `.css.map` and `_rtl.css`, and the second dict specifies that `.scss`
is also transformed into minified `.scss.js` file along with `.scss.js.map`.
"""
PROSPECTIVE_JAVASCRIPT_MAP = {
    ".scss": [
        {
            "to_minified_ext": ".css",
            "to_related": [".css", ".css.map", "_rtl.css"],
        },
        {
            "to_minified_ext": ".scss.js",
            "to_related": [".scss.js", ".scss.js.map"],
        },
    ],
    ".js": [
        {
            "to_minified_ext": ".js",
            "to_related": [".js", ".js.map"],
        },
    ],
    ".jsx": [
        {
            "to_minified_ext": ".js",
            "to_related": [".jsx", ".js", ".js.map"],
        },
    ],
    ".ts": [
        {
            "to_minified_ext": ".js",
            "to_related": [".ts", ".js", ".js.map"],
        },
    ],
    ".d.ts": [
        {
            "to_minified_ext": None,
            "to_related": [".ts"],
        },
    ],
}


def get_inputs(project):
    """Locate the `from` and `to` archives in project inputs directory."""
    from_file = list(project.inputs("from*"))
    to_file = list(project.inputs("to*"))

    if len(from_file) != 1:
        raise FileNotFoundError("from* archive not found.")

    if len(to_file) != 1:
        raise FileNotFoundError("to* archive not found.")

    return from_file[0], to_file[0]


def get_resource_codebase_root(project, resource_path):
    """Return "to" or "from" depending on the resource location in the codebase."""
    relative_path = Path(resource_path).relative_to(project.codebase_path)
    first_part = relative_path.parts[0]
    if first_part in ["to", "from"]:
        return first_part
    return ""


def collect_and_create_codebase_resources(project):
    """
    Collect and create codebase resources including the "to/" and "from/" context using
    the resource tag field.
    """
    for resource_path in project.walk_codebase_path():
        pipes.make_codebase_resource(
            project=project,
            location=resource_path,
            tag=get_resource_codebase_root(project, resource_path),
        )


def get_extracted_path(resource):
    """Return the `-extract/` extracted path of provided `resource`."""
    return resource.path + "-extract/"


def get_extracted_subpath(path):
    """Return the path segments located after the last `-extract/` segment."""
    return path.split("-extract/")[-1]


def get_best_path_matches(to_resource, matches):
    """Return the best `matches` for the provided `to_resource`."""
    path_parts = Path(to_resource.path.lstrip("/")).parts

    for path_parts_index in range(1, len(path_parts)):
        subpath = "/".join(path_parts[path_parts_index:])
        subpath_matches = [
            from_resource
            for from_resource in matches
            if from_resource.path.endswith(subpath)
        ]
        if subpath_matches:
            return subpath_matches

    return matches


def _map_checksum_resource(to_resource, from_resources, checksum_field):
    checksum_value = getattr(to_resource, checksum_field)
    matches = from_resources.filter(**{checksum_field: checksum_value})
    for match in get_best_path_matches(to_resource, matches):
        pipes.make_relation(
            from_resource=match,
            to_resource=to_resource,
            map_type=checksum_field,
        )


def map_checksum(project, checksum_field, logger=None):
    """Map using checksum."""
    project_files = project.codebaseresources.files().no_status()
    from_resources = project_files.from_codebase().has_value(checksum_field)
    to_resources = (
        project_files.to_codebase().has_value(checksum_field).has_no_relation()
    )
    resource_count = to_resources.count()

    if logger:
        logger(
            f"Mapping {resource_count:,d} to/ resources using {checksum_field} "
            f"against from/ codebase"
        )

    resource_iterator = to_resources.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, to_resource in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            resource_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        _map_checksum_resource(to_resource, from_resources, checksum_field)


def _map_java_to_class_resource(to_resource, from_resources, from_classes_index):
    """
    Map the ``to_resource`` .class file Resource with a Resource in
    ``from_resources`` .java files, using the ``from_classes_index`` index of
    from/ fully qualified Java class names.
    """
    normalized_java_path = jvm.get_normalized_java_path(to_resource.path)
    match = pathmap.find_paths(path=normalized_java_path, index=from_classes_index)
    if not match:
        return

    for resource_id in match.resource_ids:
        from_resource = from_resources.get(id=resource_id)
        # compute the root of the packages on the source side
        from_source_root_parts = from_resource.path.strip("/").split("/")
        from_source_root = "/".join(
            from_source_root_parts[: -match.matched_path_length]
        )
        pipes.make_relation(
            from_resource=from_resource,
            to_resource=to_resource,
            map_type="java_to_class",
            extra_data={"from_source_root": f"{from_source_root}/"},
        )


def map_java_to_class(project, logger=None):
    """
    Map to/ compiled Java .class(es) to from/ .java source using Java fully
    qualified paths and indexing from/ .java files.
    """
    project_files = project.codebaseresources.files().no_status()
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase().has_no_relation()

    to_resources_dot_class = to_resources.filter(extension=".class")
    resource_count = to_resources_dot_class.count()
    if logger:
        logger(f"Mapping {resource_count:,d} .class resources to .java")

    from_resources_dot_java = from_resources.filter(extension=".java")

    # build an index using from-side Java fully qualified class file names
    # built from the "java_package" and file name
    indexables = get_indexable_qualified_java_paths(from_resources_dot_java)

    # we do not index subpath since we want to match only fully qualified names
    from_classes_index = pathmap.build_index(indexables, with_subpaths=False)

    resource_iterator = to_resources_dot_class.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, to_resource in enumerate(resource_iterator):
        if logger:
            last_percent = pipes.log_progress(
                logger,
                resource_index,
                resource_count,
                last_percent,
                increment_percent=10,
                start_time=start_time,
            )
        _map_java_to_class_resource(to_resource, from_resources, from_classes_index)

    # Flag not mapped .class in to/ codebase
    to_resources_dot_class = to_resources.filter(extension=".class")
    to_resources_dot_class.update(status=flag.NO_JAVA_SOURCE)


def get_indexable_qualified_java_paths_from_values(resource_values):
    """
    Yield tuples of (resource id, fully-qualified Java path) for indexable
    classes from a list of ``resource_data`` tuples of "from/" side of the
    project codebase.

    These ``resource_data`` input tuples are in the form:
        (resource.id, resource.name, resource.extra_data)

    And the output tuples look like this example::
        (123, "org/apache/commons/LoggerImpl.java")
    """
    for resource_id, resource_name, resource_extra_data in resource_values:
        java_package = resource_extra_data and resource_extra_data.get("java_package")
        if not java_package:
            continue
        fully_qualified = jvm.get_fully_qualified_java_path(
            java_package,
            filename=resource_name,
        )
        yield resource_id, fully_qualified


def get_indexable_qualified_java_paths(from_resources_dot_java):
    """
    Yield tuples of (resource id, fully-qualified Java class name) for indexable
    classes from the "from/" side of the project codebase using the
    "java_package" Resource.extra_data.
    """
    resource_values = from_resources_dot_java.values_list("id", "name", "extra_data")
    return get_indexable_qualified_java_paths_from_values(resource_values)


def find_java_packages(project, logger=None):
    """
    Collect the Java packages of Java source files for a `project`.

    Multiprocessing is enabled by default on this pipe, the number of processes
    can be controlled through the SCANCODEIO_PROCESSES setting.

    Note: we use the same API as the ScanCode scans by design
    """
    from_java_resources = (
        project.codebaseresources.files()
        .no_status()
        .from_codebase()
        .has_no_relation()
        .filter(extension=".java")
    )

    if logger:
        logger(
            f"Finding Java package for {from_java_resources.count():,d} "
            ".java resources."
        )

    scancode._scan_and_save(
        resource_qs=from_java_resources,
        scan_func=scan_for_java_package,
        save_func=save_java_package_scan_results,
    )


def scan_for_java_package(location, with_threading=True):
    """
    Run a Java package scan on provided ``location``.

    Return a dict of scan `results` and a list of `errors`.
    """
    scanners = [scancode.Scanner("java_package", jvm.get_java_package)]
    return scancode._scan_resource(location, scanners, with_threading=with_threading)


def save_java_package_scan_results(codebase_resource, scan_results, scan_errors):
    """
    Save the resource Java package scan results in the database as Resource.extra_data.
    Create project errors if any occurred during the scan.
    """
    # note: we do not set a status on resources if we collected this correctly
    if scan_errors:
        codebase_resource.add_errors(scan_errors)
        codebase_resource.status = flag.SCANNED_WITH_ERROR
    else:
        codebase_resource.extra_data.update(scan_results)
    codebase_resource.save()


def _map_jar_to_source_resource(jar_resource, to_resources, from_resources):
    jar_extracted_path = get_extracted_path(jar_resource)
    jar_extracted_dot_class_files = list(
        to_resources.filter(
            extension=".class", path__startswith=jar_extracted_path
        ).values("id", "status")
    )

    # Rely on the status flag to avoid triggering extra SQL queries.
    not_mapped_dot_class = [
        dot_class_file
        for dot_class_file in jar_extracted_dot_class_files
        if dot_class_file.get("status") == flag.NO_JAVA_SOURCE
    ]
    # Do not continue if any .class files couldn't be mapped.
    if any(not_mapped_dot_class):
        return

    # Using ids from already evaluated QuerySet to avoid triggering an expensive
    # SQL subquery in the following CodebaseRelation QuerySet.
    dot_class_file_ids = [
        dot_class_file.get("id") for dot_class_file in jar_extracted_dot_class_files
    ]
    java_to_class_extra_data_list = CodebaseRelation.objects.filter(
        to_resource__in=dot_class_file_ids, map_type="java_to_class"
    ).values_list("extra_data", flat=True)

    from_source_roots = [
        extra_data.get("from_source_root", "")
        for extra_data in java_to_class_extra_data_list
    ]
    if len(set(from_source_roots)) != 1:
        # Could not determine a common root directory for the java_to_class files
        return

    common_source_root = from_source_roots[0].rstrip("/")
    if common_from_resource := from_resources.get_or_none(path=common_source_root):
        pipes.make_relation(
            from_resource=common_from_resource,
            to_resource=jar_resource,
            map_type="jar_to_source",
        )


def map_jar_to_source(project, logger=None):
    project_files = project.codebaseresources.files()
    # Include the directories to map on the common source
    from_resources = project.codebaseresources.from_codebase()
    to_resources = project_files.to_codebase()
    to_jars = to_resources.filter(extension=".jar")

    to_jars_count = to_jars.count()
    if logger:
        logger(
            f"Mapping {to_jars_count:,d} .jar resources using map_jar_to_source "
            f"against from/ codebase"
        )

    resource_iterator = to_jars.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, jar_resource in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            to_jars_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        _map_jar_to_source_resource(jar_resource, to_resources, from_resources)


def flag_to_meta_inf_files(project):
    """Flag all ``META-INF/*`` file of the ``to/`` directory as ignored."""
    to_resources = project.codebaseresources.files().to_codebase()
    meta_inf_files = to_resources.filter(path__contains="META-INF/")
    meta_inf_files.no_status().update(status=flag.IGNORED_META_INF)


def get_diff_ratio(to_resource, from_resource):
    """
    Return a similarity ratio as a float between 0 and 1 by comparing the
    text content of the ``to_resource`` and ``from_resource``.

    Return None if any of the two resources are not text files or if files
    are not readable.
    """
    if not (to_resource.is_text and from_resource.is_text):
        return

    try:
        to_lines = to_resource.location_path.read_text().splitlines()
        from_lines = from_resource.location_path.read_text().splitlines()
    except Exception:
        return

    matcher = difflib.SequenceMatcher(a=from_lines, b=to_lines)
    return matcher.quick_ratio()


def _map_path_resource(
    to_resource, from_resources, from_resources_index, diff_ratio_threshold=0.7
):
    match = pathmap.find_paths(to_resource.path, from_resources_index)
    if not match:
        return

    # Only create relations when the number of matches if inferior or equal to
    # the current number of path segment matched.
    if len(match.resource_ids) > match.matched_path_length:
        to_resource.status = flag.TOO_MANY_MAPS
        to_resource.save()
        return

    for resource_id in match.resource_ids:
        from_resource = from_resources.get(id=resource_id)
        diff_ratio = get_diff_ratio(
            to_resource=to_resource, from_resource=from_resource
        )
        if diff_ratio is not None and diff_ratio < diff_ratio_threshold:
            continue

        # Do not count the "to/" segment as it is not "matchable"
        to_path_length = len(to_resource.path.split("/")) - 1
        extra_data = {
            "path_score": f"{match.matched_path_length}/{to_path_length}",
        }
        if diff_ratio:
            extra_data["diff_ratio"] = f"{diff_ratio:.1%}"

        pipes.make_relation(
            from_resource=from_resource,
            to_resource=to_resource,
            map_type="path",
            extra_data=extra_data,
        )


def map_path(project, logger=None):
    """Map using path suffix similarities."""
    project_files = project.codebaseresources.files().no_status()
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase().has_no_relation()
    resource_count = to_resources.count()

    if logger:
        logger(
            f"Mapping {resource_count:,d} to/ resources using path map "
            f"against from/ codebase"
        )

    from_resources_index = pathmap.build_index(
        from_resources.values_list("id", "path"), with_subpaths=True
    )

    resource_iterator = to_resources.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, to_resource in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            resource_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        _map_path_resource(to_resource, from_resources, from_resources_index)


def _match_purldb_resource(project, resource):
    if results := purldb.match_by_sha1(sha1=resource.sha1):
        package_data = results[0].copy()
        # Do not re-use uuid from PurlDB as DiscoveredPackage.uuid is unique and a
        # PurlDB match can be found in different projects.
        package_data.pop("uuid", None)
        package_data.pop("dependencies", None)
        extracted_resources = project.codebaseresources.to_codebase().filter(
            path__startswith=resource.path
        )
        pipes.update_or_create_package(
            project=project,
            package_data=package_data,
            codebase_resources=extracted_resources,
        )
        # Override the status as "purldb match" as we can rely on the codebase relation
        # for the mapping information.
        extracted_resources.update(status=flag.MATCHED_TO_PURLDB)


def match_purldb(project, extensions, logger=None):
    """
    Match against PurlDB selecting codebase resources using provided `extensions`.
    Resources with existing status as not excluded.
    """
    to_resources = (
        project.codebaseresources.files()
        .to_codebase()
        .no_status()
        .has_value("sha1")
        .filter(extension__in=extensions)
    )
    resource_count = to_resources.count()

    if logger:
        extensions_str = ", ".join(extensions)
        logger(
            f"Matching {resource_count:,d} {extensions_str} resources against PurlDB"
        )

    resource_iterator = to_resources.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, to_resource in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            resource_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        _match_purldb_resource(project, to_resource)


def map_javascript(project, logger=None):
    """Map a packed or minified JavaScript, TypeScript, CSS and SCSS to its source."""
    project_files = project.codebaseresources.files().only("path")
    query = Q(
        *[Q(extension=extension) for extension in PROSPECTIVE_JAVASCRIPT_MAP.keys()],
        _connector=Q.OR,
    )

    from_resources = project_files.from_codebase().filter(query)
    to_resources = project_files.to_codebase()
    resource_count = from_resources.count()

    if logger:
        logger(
            f"Mapping {resource_count:,d} from/ resources using javascript map "
            f"against to/ codebase"
        )

    resource_iterator = from_resources.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, from_resource in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            resource_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        _map_javascript_resource(from_resource, to_resources)


def _map_javascript_resource(from_resource, to_resources):
    path = Path(from_resource.path.lstrip("/"))
    # Skip any dot files.
    if path.name.startswith("."):
        return

    basename, from_extension = _get_basename_and_extension(path.name)
    path_parts = (path.parent / basename).parts
    path_parts_len = len(path_parts)

    for index in range(1, path_parts_len - 1):
        current_parts = path_parts[index:]
        current_path = "/".join(current_parts)

        any_map = False

        for candidate in PROSPECTIVE_JAVASCRIPT_MAP.get(from_extension, []):
            query = Q(
                *[
                    Q(path__endswith=f"{current_path}{extension}")
                    for extension in candidate["to_related"]
                ],
                _connector=Q.OR,
            )

            matches = to_resources.filter(query)

            if not matches:
                continue

            # Only create relations when the number of matches if inferior or
            # equal to the sum of current number of path segment matched and
            # number of related files.
            if len(matches) > len(current_parts) + len(candidate["to_related"]):
                continue

            map_type = "path"
            if _is_minified_and_map_compiled_from_source(
                matches,
                from_resource,
                minified_extension=candidate["to_minified_ext"],
            ):
                map_type = "js_compiled"

            _relate_js_files(
                matches,
                from_resource,
                map_type,
                path_score=f"{len(current_parts)}/{path_parts_len-1}",
            )
            any_map = True

        if any_map:
            break


def _relate_js_files(matches, from_resource, map_type, path_score):
    for match in matches:
        relation = CodebaseRelation.objects.filter(
            from_resource=from_resource,
            to_resource=match,
            map_type=map_type,
        )
        if not relation.exists():
            pipes.make_relation(
                from_resource=from_resource,
                to_resource=match,
                map_type=map_type,
                extra_data={
                    "path_score": path_score,
                },
            )


def _is_minified_and_map_compiled_from_source(
    to_resources, from_source, minified_extension
):
    """Return True if a minified file and its map were compiled from a source file."""
    if not minified_extension:
        return False
    path = Path(from_source.path.lstrip("/"))
    basename, extension = _get_basename_and_extension(path.name)
    minified_file, minified_map_file = None, None

    source_file_name = path.name
    source_mapping = f"sourceMappingURL={basename}{minified_extension}.map"

    for resource in to_resources:
        if resource.path.endswith(minified_extension):
            minified_file = resource
        elif resource.path.endswith(f"{minified_extension}.map"):
            minified_map_file = resource

    if minified_file and minified_map_file:
        # Check minified_file contains reference to the source file.
        if _source_mapping_in_minified(minified_file, source_mapping):
            # Check source file's content is in the map file or if the
            # source file path is in the map file.
            if _source_content_in_map(minified_map_file, from_source) or _source_in_map(
                minified_map_file, source_file_name
            ):
                return True

    return False


def _source_mapping_in_minified(resource, source_mapping):
    """Return True if a string contains a specific string in its last 5 lines."""
    lines = resource.file_content.split("\n")
    total_lines = len(lines)
    # Get the last 5 lines.
    tail = 5 if total_lines > 5 else total_lines
    return any(source_mapping in line for line in reversed(lines[-tail:]))


def _source_in_map(map_file, source_name):
    """
    Return True if the given source file name exists in the sources list of the
    specified map file.
    """
    try:
        with open(map_file.location) as f:
            data = json.load(f)
            sources = data.get("sources", [])
            return any(source.endswith(source_name) for source in sources)
    except json.JSONDecodeError:
        return False


def _sha1(content):
    """Calculate the SHA-1 hash of a string."""
    hash_object = hashlib.sha1(content.encode())
    return hash_object.hexdigest()


def _source_content_in_map(map_file, source_file):
    """Return True if the given source content is in specified map file."""
    origin_sha1 = source_file.sha1
    try:
        with open(map_file.location) as f:
            data = json.load(f)
            contents = data.get("sourcesContent", [])
            return any(origin_sha1 == _sha1(content) for content in contents)
    except json.JSONDecodeError:
        return False


def _get_basename_and_extension(filename):
    """Return the basename and extension of a JavaScript/TypeScript related file."""
    # The order of extensions in the list matters since
    # `.d.ts` should be tested first before `.ts`.
    js_extensions = [".d.ts", ".ts", ".js", ".jsx", ".scss"]
    for ext in js_extensions:
        if filename.endswith(ext):
            extension = ext
            break
    else:
        raise ValueError(f"{filename} has an invalid extension")
    basename = filename[: -len(extension)]
    return basename, extension

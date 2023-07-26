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

from itertools import islice
from pathlib import Path
from timeit import default_timer as timer

from django.db.models import Q

from scanpipe import pipes
from scanpipe.models import CodebaseRelation
from scanpipe.models import CodebaseResource
from scanpipe.pipes import flag
from scanpipe.pipes import get_resource_diff_ratio
from scanpipe.pipes import js
from scanpipe.pipes import jvm
from scanpipe.pipes import pathmap
from scanpipe.pipes import purldb
from scanpipe.pipes import resolve
from scanpipe.pipes import scancode

FROM = "from/"
TO = "to/"


def get_inputs(project):
    """Locate the ``from`` and ``to`` input files in project inputs/ directory."""
    from_files = list(project.inputs("from*"))
    to_files = list(project.inputs("to*"))

    if len(from_files) < 1:
        raise FileNotFoundError("from* input files not found.")

    if len(to_files) < 1:
        raise FileNotFoundError("to* input files not found.")

    return from_files, to_files


def get_resource_codebase_root(project, resource_path):
    """Return "to" or "from" depending on the resource location in the codebase."""
    relative_path = Path(resource_path).relative_to(project.codebase_path)
    first_part = relative_path.parts[0]
    if first_part in ["to", "from"]:
        return first_part
    return ""


def yield_resources_from_codebase(project):
    """
    Yield CodebaseResource instances, including their ``info`` data, ready to be
    inserted in the database using ``save()`` or ``bulk_create()``.
    """
    for resource_path in project.walk_codebase_path():
        yield pipes.make_codebase_resource(
            project=project,
            location=resource_path,
            save=False,
            tag=get_resource_codebase_root(project, resource_path),
        )


def collect_and_create_codebase_resources(project, batch_size=5000):
    """
    Collect and create codebase resources including the "to/" and "from/" context using
    the resource tag field.

    The default ``batch_size`` can be overriden, although the benefits of a value
    greater than 5000 objects are usually not significant.
    """
    model_class = CodebaseResource
    objs = yield_resources_from_codebase(project)

    while True:
        batch = list(islice(objs, batch_size))
        if not batch:
            break
        model_class.objects.bulk_create(batch, batch_size)


def get_extracted_path(resource):
    """Return the ``-extract/`` extracted path of provided ``resource``."""
    return resource.path + "-extract/"


def get_extracted_subpath(path):
    """Return the path segments located after the last ``-extract/`` segment."""
    return path.split("-extract/")[-1]


def get_best_path_matches(to_resource, matches):
    """Return the best ``matches`` for the provided ``to_resource``."""
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
    Collect the Java packages of Java source files for a ``project``.

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

    Return a dict of scan ``results`` and a list of ``errors``.
    """
    scanners = [scancode.Scanner("java_package", jvm.get_java_package)]
    return scancode._scan_resource(location, scanners, with_threading=with_threading)


def save_java_package_scan_results(codebase_resource, scan_results, scan_errors):
    """
    Save the resource Java package scan results in the database as Resource.extra_data.
    Create project errors if any occurred during the scan.
    """
    # The status is only updated in case of errors.
    if scan_errors:
        codebase_resource.add_errors(scan_errors)
        codebase_resource.update(status=flag.SCANNED_WITH_ERROR)
    else:
        codebase_resource.update_extra_data(scan_results)


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
    """Map .jar files to their related source directory."""
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


def _map_path_resource(
    to_resource, from_resources, from_resources_index, diff_ratio_threshold=0.7
):
    match = pathmap.find_paths(to_resource.path, from_resources_index)
    if not match:
        return

    # Only create relations when the number of matches if inferior or equal to
    # the current number of path segment matched.
    if len(match.resource_ids) > match.matched_path_length:
        to_resource.update(status=flag.TOO_MANY_MAPS)
        return

    for resource_id in match.resource_ids:
        from_resource = from_resources.get(id=resource_id)
        diff_ratio = get_resource_diff_ratio(to_resource, from_resource)
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


def create_package_from_purldb_data(project, resource, package_data):
    """Create a DiscoveredPackage instance from PurlDB ``package_data``."""
    package_data = package_data.copy()
    # Do not re-use uuid from PurlDB as DiscoveredPackage.uuid is unique and a
    # PurlDB match can be found in different projects.
    package_data.pop("uuid", None)
    package_data.pop("dependencies", None)
    extracted_resources = project.codebaseresources.to_codebase().filter(
        path__startswith=resource.path
    )
    package = pipes.update_or_create_package(
        project=project,
        package_data=package_data,
        codebase_resources=extracted_resources,
    )
    # Override the status as "purldb match" as we can rely on the codebase relation
    # for the mapping information.
    extracted_resources.update(status=flag.MATCHED_TO_PURLDB)
    return package


def match_purldb_package(project, resource):
    """Match an archive type resource in the PurlDB."""
    if results := purldb.match_package(sha1=resource.sha1):
        package_data = results[0]
        return create_package_from_purldb_data(project, resource, package_data)


def match_purldb_resource(project, resource):
    """Match a single file resource in the PurlDB."""
    sha1_list = [resource.sha1]
    if resource.path.endswith(".map"):
        sha1_list.extend(js.source_content_sha1_list(resource))

    if results := purldb.match_resource(sha1_list=sha1_list):
        package_url = results[0]["package"]
        if package_data := purldb.request_get(url=package_url):
            return create_package_from_purldb_data(project, resource, package_data)


def match_purldb(project, extensions, matcher_func, logger=None):
    """
    Match against PurlDB selecting codebase resources using provided
    ``package_extensions`` for archive type files, and ``resource_extensions`` for
    single resource files.
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
        logger(f"Matching {resource_count:,d} {extensions_str} resources in PurlDB")

    resource_iterator = to_resources.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    matched_count = 0

    for resource_index, to_resource in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            resource_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        matched_package = matcher_func(project, to_resource)
        if matched_package:
            matched_count += 1

    logger(f"{matched_count:,d} resource(s) matched in PurlDB")


def map_javascript(project, logger=None):
    """Map a packed or minified JavaScript, TypeScript, CSS and SCSS to its source."""
    project_files = project.codebaseresources.files()

    to_resources = project_files.to_codebase().exclude(name__startswith=".")
    to_resources_dot_map = to_resources.filter(extension=".map")
    to_resources_minified = to_resources.filter(extension__in=[".css", ".js"])

    to_resources_dot_map_count = to_resources_dot_map.count()
    if logger:
        logger(
            f"Mapping {to_resources_dot_map_count:,d} .map resources using javascript "
            f"map against from/ codebase"
        )

    from_resources = project_files.from_codebase()
    from_resources_index = pathmap.build_index(
        from_resources.values_list("id", "path"), with_subpaths=True
    )

    resource_iterator = to_resources_dot_map.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, to_dot_map in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            to_resources_dot_map_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        _map_javascript_resource(
            to_dot_map, to_resources_minified, from_resources_index, from_resources
        )


def _map_javascript_resource(
    to_map, to_resources_minified, from_resources_index, from_resources
):
    matches = js.get_matches_by_sha1(to_map, from_resources)

    # Use diff_ratio if no sha1 match is found.
    if not matches:
        matches = js.get_matches_by_ratio(to_map, from_resources_index, from_resources)

    transpiled = [to_map]
    if minified_resource := js.get_minified_resource(
        map_resource=to_map,
        minified_resources=to_resources_minified,
    ):
        transpiled.append(minified_resource)

    for resource in transpiled:
        for match, extra_data in matches:
            pipes.make_relation(
                from_resource=match,
                to_resource=resource,
                map_type="js_compiled",
                extra_data=extra_data,
            )
            resource.update(status=flag.MAPPED)


def _map_about_file_resource(project, about_file_resource, to_resources):
    about_file_location = str(about_file_resource.location_path)
    package_data = resolve.resolve_about_package(about_file_location)
    if not package_data:
        return

    filename = package_data.get("filename")
    if not filename:
        # Cannot map anything without the about_resource value.
        return

    ignored_resources = []
    if extra_data := package_data.get("extra_data"):
        ignored_resources = extra_data.get("ignored_resources")

    # Fetch all resources that are covered by the .ABOUT file.
    codebase_resources = to_resources.filter(path__contains=f"/{filename.lstrip('/')}")
    if not codebase_resources:
        # If there's nothing to map on the ``to/`` do not create the package.
        return

    # Ignore resources for paths in `ignored_resources` attribute
    if ignored_resources:
        lookups = Q()
        for resource_path in ignored_resources:
            lookups |= Q(**{"path__contains": resource_path})
        codebase_resources = codebase_resources.filter(~lookups)

    # Create the Package using .ABOUT data and assigned related codebase_resources
    pipes.update_or_create_package(project, package_data, codebase_resources)

    # Map the .ABOUT file resource to all related resources in the ``to/`` side.
    for to_resource in codebase_resources:
        pipes.make_relation(
            from_resource=about_file_resource,
            to_resource=to_resource,
            map_type="about_file",
        )

    codebase_resources.update(status=flag.MAPPED)
    about_file_resource.update(status=flag.MAPPED)


def map_about_files(project, logger=None):
    """Map ``from/`` .ABOUT files to their related ``to/`` resources."""
    project_resources = project.codebaseresources
    from_files = project_resources.files().from_codebase()
    from_about_files = from_files.filter(extension=".ABOUT")
    to_resources = project_resources.to_codebase()

    if logger:
        logger(
            f"Mapping {from_about_files.count():,d} .ABOUT files found in the from/ "
            f"codebase."
        )

    for about_file_resource in from_about_files:
        _map_about_file_resource(project, about_file_resource, to_resources)


def map_javascript_post_purldb_match(project, logger=None):
    """Map minified javascript file based on existing PurlDB match."""
    project_files = project.codebaseresources.files()

    to_resources = project_files.to_codebase()

    to_resources_dot_map = to_resources.filter(status="matched-to-purldb").filter(
        extension=".map"
    )

    to_resources_minified = to_resources.no_status().filter(
        extension__in=[".css", ".js"]
    )

    to_resources_minified_count = to_resources_minified.count()

    if not to_resources_dot_map:
        logger("No PurlDB matched .map file is available. Skipping.")
        return

    if logger:
        logger(
            f"Mapping {to_resources_minified_count:,d} minified .js and .css "
            f"resources based on existing PurlDB match"
        )

    to_resources_dot_map_index = pathmap.build_index(
        to_resources_dot_map.values_list("id", "path"), with_subpaths=True
    )

    resource_iterator = to_resources_minified.iterator(chunk_size=2000)
    last_percent = 0
    start_time = timer()
    for resource_index, to_minified in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger,
            resource_index,
            to_resources_minified_count,
            last_percent,
            increment_percent=10,
            start_time=start_time,
        )
        _map_javascript_post_purldb_match_resource(
            to_minified, to_resources_dot_map, to_resources_dot_map_index
        )


def _map_javascript_post_purldb_match_resource(
    to_minified, to_resources_dot_map, to_resources_dot_map_index
):
    path = Path(to_minified.path.lstrip("/"))
    map_file_name = f"{path.name}.map"
    map_file_path = path.parent / map_file_name

    if not js.is_source_mapping_in_minified(to_minified, map_file_name):
        return

    prospect = pathmap.find_paths(str(map_file_path), to_resources_dot_map_index)
    if not prospect:
        return

    # Only create relations when the number of matches is inferior or equal to
    # the current number of path segment matched.
    too_many_prospects = len(prospect.resource_ids) > prospect.matched_path_length
    if too_many_prospects:
        return

    map_file = to_resources_dot_map.get(id=prospect.resource_ids[0])

    if package := map_file.discovered_packages.first():
        package.add_resources([to_minified])
        to_minified.update(status=flag.MAPPED)


def map_javascript_path(project, logger=None):
    """Map javascript file based on path."""
    project_files = project.codebaseresources.files().only("path")

    to_resources_key = (
        project_files.to_codebase()
        .no_status()
        .filter(extension__in=[".map", ".ts"])
        .exclude(name__startswith=".")
    )

    to_resources = project_files.to_codebase().no_status().exclude(name__startswith=".")

    from_resources = project_files.from_codebase()
    resource_count = to_resources_key.count()

    if logger:
        logger(
            f"Mapping {resource_count:,d} to/ resources using javascript map "
            f"against from/ codebase"
        )

    from_resources_index = pathmap.build_index(
        from_resources.values_list("id", "path"), with_subpaths=True
    )

    resource_iterator = to_resources_key.iterator(chunk_size=2000)
    last_percent = 0
    map_count = 0
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
        map_count += _map_javascript_path_resource(
            to_resource, to_resources, from_resources_index, from_resources
        )

    logger(f"{map_count:,d} resource(s) mapped")


def _map_javascript_path_resource(
    to_resource, to_resources, from_resources_index, from_resources
):
    """
    Map JavaScript deployed files using their .map files.
    Return the number of mapped files.
    """
    path = Path(to_resource.path.lstrip("/"))

    basename_and_extension = js.get_js_map_basename_and_extension(path.name)
    if not basename_and_extension:
        return 0

    basename, extension = basename_and_extension
    path_parts = (path.parent / basename).parts
    path_parts_len = len(path_parts)

    base_path = path.parent / basename

    prospect = js.PROSPECTIVE_JAVASCRIPT_MAP.get(extension, {})

    max_matched_path = 0
    from_resource = None
    for source_ext in prospect.get("sources", []):
        match = pathmap.find_paths(f"{base_path}{source_ext}", from_resources_index)

        # Only create relations when the number of matches if inferior or equal to
        # the current number of path segment matched.
        if not match or len(match.resource_ids) > match.matched_path_length:
            continue

        if match.matched_path_length > max_matched_path:
            max_matched_path = match.matched_path_length
            from_resource = from_resources.get(id=match.resource_ids[0])
            extra_data = {"path_score": f"{match.matched_path_length}/{path_parts_len}"}

    if not from_resource:
        return 0

    transpiled = [to_resource]
    for related_ext in prospect.get("related", []):
        try:
            transpiled.append(to_resources.get(path=f"{base_path}{related_ext}"))
        except CodebaseResource.DoesNotExist:
            pass

    for match in transpiled:
        pipes.make_relation(
            from_resource=from_resource,
            to_resource=match,
            map_type="js_path",
            extra_data=extra_data,
        )
    return len(transpiled)

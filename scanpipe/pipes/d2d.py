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
from pathlib import Path
from timeit import default_timer as timer

from django.core.exceptions import ObjectDoesNotExist

from scanpipe import pipes
from scanpipe.models import CodebaseRelation
from scanpipe.pipes import flag
from scanpipe.pipes import pathmap
from scanpipe.pipes import purldb

FROM = "from/"
TO = "to/"

IGNORE_FILENAMES = ("packageinfo",)
IGNORE_EXTENSIONS = ()
IGNORE_PATHS = ("gradleTest/",)


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


def _resource_checksum_map(to_resource, from_resources, checksum_field):
    checksum_value = getattr(to_resource, checksum_field)
    matches = from_resources.filter(**{checksum_field: checksum_value})
    for match in get_best_path_matches(to_resource, matches):
        pipes.make_relation(
            from_resource=match,
            to_resource=to_resource,
            map_type=checksum_field,
        )


def checksum_map(project, checksum_field, logger=None):
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
        _resource_checksum_map(to_resource, from_resources, checksum_field)


def get_indexable_to_java_class_paths(to_resources_dot_class):
    """
    Yield tuples of (resource id, fully-qualified Java name) for indexable
    classes from the "to/" side of the project codebase.
    """

    for to_resource in to_resources_dot_class:
        qualified_class = get_extracted_subpath(to_resource.path).strip("/")
        path = Path(qualified_class)
        parts_without_name = list(path.parts)[:-1]
        if "$" in to_resource.name:
            # an inner class: we keep only the outer class name
            to_name = to_resource.name.split("$")[0]
        else:
            to_name = path.stem
        # we append a .java extension so that we can map to the From side that is
        # suypposed to contain the corresponding Java source code
        fully_qualified_java_name = "/".join(parts_without_name + [f"{to_name}.java"])
        yield to_resource.id, fully_qualified_java_name


def java_to_class_map(project, logger=None):
    """
    Map From the .java source To its compiled .class(es) using Java fully
    qualified names mapping.
    """
    project_files = project.codebaseresources.files().no_status()
    to_resources = project_files.to_codebase().has_no_relation()
    to_resources_dot_classes = to_resources.filter(name__endswith=".class")

    # build an index using to-side Java fully qualified class names
    indexables = get_indexable_to_java_class_paths(to_resources_dot_classes)

    # we do not index subpath since we want to match only fully qualified names
    to_java_fqn_index = pathmap.build_index(indexables, with_subpaths=False)

    from_resources = project_files.from_codebase().filter(name__endswith=".java")
    resource_count = from_resources.count()
    if logger:
        logger(f"Indexing {resource_count:,d} 'From' .java resources")

    # iterate on the from "sources" resources and find a corresponding "to"
    # deployed Java
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
        map_from_resource_java_to_class(from_resource, to_resources, to_java_fqn_index)

    # Flag not mapped .class in to/ codebase
    to_resources = project_files.to_codebase().has_no_relation()
    to_resources_dot_class = to_resources.filter(name__endswith=".class")
    to_resources_dot_class.update(status=flag.NO_JAVA_SOURCE)


def map_from_resource_java_to_class(from_resource, to_resources, to_java_fqn_index):
    """
    Create a mapping relation for the ``from_resource``  to the "to" resources
    in ``to_resources`` query set using the ``to_java_fqn_index``.
    """
    match = pathmap.find_paths(from_resource.path, to_java_fqn_index)
    if not match:
        return

    for resource_id in match.resource_ids:
        to_resource = to_resources.get(id=resource_id)
        pipes.make_relation(
            from_resource=from_resource,
            to_resource=to_resource,
            map_type="java_to_class",
            # TODO: not sure what to make of this
            # extra_data={
            # "from_source_root": to_resource.path.replace(qualified_java, ""),
            # },
        )


def _resource_jar_to_source_map(jar_resource, to_resources, from_resources):
    jar_extracted_path = get_extracted_path(jar_resource)
    jar_extracted_files = to_resources.filter(path__startswith=jar_extracted_path)

    # Flag all META-INF/* file as ignored
    meta_inf_files = jar_extracted_files.filter(path__contains="META-INF/")
    meta_inf_files.no_status().update(status=flag.IGNORED_META_INF)

    dot_class_files = jar_extracted_files.filter(name__endswith=".class")
    # Do not continue if some .class files couldn't be mapped.
    if dot_class_files.has_no_relation().exists():
        return

    java_to_class_relations = CodebaseRelation.objects.filter(
        to_resource__in=dot_class_files, map_type="java_to_class"
    )
    from_source_roots = [
        relation.extra_data.get("from_source_root", "")
        for relation in java_to_class_relations
    ]
    if len(set(from_source_roots)) != 1:
        # Could not determine a common root directory for the java_to_class files
        return

    try:
        common_from_resource = from_resources.get(path=from_source_roots[0].rstrip("/"))
    except ObjectDoesNotExist:
        return

    pipes.make_relation(
        from_resource=common_from_resource,
        to_resource=jar_resource,
        map_type="jar_to_source",
    )


def jar_to_source_map(project, logger=None):
    project_files = project.codebaseresources.files()
    # Include the directories to map on the common source
    from_resources = project.codebaseresources.from_codebase()
    to_resources = project_files.to_codebase()
    to_jars = to_resources.filter(extension=".jar")

    to_jars_count = to_jars.count()
    if logger:
        logger(
            f"Mapping {to_jars_count:,d} .jar resources using jar_to_source_map "
            f"against from/ codebase"
        )

    for jar_resource in to_jars:
        _resource_jar_to_source_map(jar_resource, to_resources, from_resources)


def get_diff_ratio(to_resource, from_resource):
    if not (to_resource.is_text and from_resource.is_text):
        return

    try:
        to_lines = to_resource.location_path.read_text().splitlines()
        from_lines = from_resource.location_path.read_text().splitlines()
    except Exception:
        return

    matcher = difflib.SequenceMatcher(a=from_lines, b=to_lines)
    return matcher.quick_ratio()


def _resource_path_map(
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


def path_map(project, logger=None):
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
        _resource_path_map(to_resource, from_resources, from_resources_index)


def _resource_purldb_match(project, resource):
    if results := purldb.match_by_sha1(sha1=resource.sha1):
        package_data = results[0].copy()
        # Do not re-use uuid from PurlDB as DiscoveredPackage.uuid is unique and a
        # PurlDB match can be found in different projects.
        package_data.pop("uuid", None)
        package_data.pop("dependencies", None)
        extracted_resources = project.codebaseresources.to_codebase().filter(
            path__startswith=f"{resource.path}"
        )
        pipes.update_or_create_package(
            project=project,
            package_data=package_data,
            codebase_resources=extracted_resources,
        )
        # Override the status as "purldb match" as we can rely on the codebase relation
        # for the mapping information.
        extracted_resources.update(status=flag.MATCHED_TO_PURLDB)


def purldb_match(project, extensions, logger=None):
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
        _resource_purldb_match(project, to_resource)

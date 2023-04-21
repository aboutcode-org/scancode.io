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

from scanpipe import pipes
from scanpipe.models import CodebaseRelation
from scanpipe.pipes import purldb

FROM = "from/"
TO = "to/"

IGNORE_FILENAMES = ("packageinfo",)

IGNORE_EXTENSIONS = ()


def get_inputs(project):
    """Locate the `from` and `to` archives in project inputs directory."""
    from_file = list(project.inputs("from*"))
    to_file = list(project.inputs("to*"))

    if len(from_file) != 1:
        raise Exception("from* archive not found.")

    if len(to_file) != 1:
        raise Exception("to* archive not found.")

    return from_file[0], to_file[0]


def checksum_match(project, checksum_field, logger=None):
    """Match using checksum."""
    project_files = project.codebaseresources.files().no_status()
    from_resources = project_files.from_codebase().has_value(checksum_field)
    to_resources = (
        project_files.to_codebase().has_value(checksum_field).has_no_relation()
    )

    if logger:
        resource_count = to_resources.count()
        logger(
            f"Matching {resource_count:,d} to/ resources using {checksum_field} "
            f"against from/ codebase"
        )

    for to_resource in to_resources:
        checksum_value = getattr(to_resource, checksum_field)
        matches = from_resources.filter(**{checksum_field: checksum_value})
        for match in matches:
            pipes.make_relationship(
                from_resource=match,
                to_resource=to_resource,
                relationship=CodebaseRelation.Relationship.IDENTICAL,
                match_type=checksum_field,
            )


def java_to_class_match(project, logger=None):
    """Match a .java source to its compiled .class using fully qualified name."""
    from_extension = ".java"
    to_extension = ".class"

    project_files = project.codebaseresources.files().no_status()
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase().has_no_relation()

    to_resources_dot_class = to_resources.filter(name__endswith=to_extension)
    if logger:
        count = to_resources_dot_class.count()
        logger(f"Matching {count:,d} .class resources to .java")

    for to_resource in to_resources_dot_class:
        qualified_class = to_resource.path.split("-extract/")[-1]

        if "$" in to_resource.name:  # inner class
            path_parts = Path(qualified_class.lstrip("/")).parts
            parts_without_name = list(path_parts[:-1])
            from_name = to_resource.name.split("$")[0] + from_extension
            qualified_java = "/".join(parts_without_name + [from_name])
        else:
            qualified_java = qualified_class.replace(to_extension, from_extension)

        matches = from_resources.filter(path__endswith=qualified_java)
        for match in matches:
            pipes.make_relationship(
                from_resource=match,
                to_resource=to_resource,
                relationship=CodebaseRelation.Relationship.COMPILED,
                match_type="java_to_class",
            )


def path_match(project, logger=None):
    """Match using path similarities."""
    project_files = project.codebaseresources.files().no_status().only("path")
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase().has_no_relation()
    resource_count = to_resources.count()

    if logger:
        logger(
            f"Matching {resource_count:,d} to/ resources using path match "
            f"against from/ codebase"
        )

    resource_iterator = to_resources.iterator(chunk_size=2000)
    last_percent = 0
    for resource_index, to_resource in enumerate(resource_iterator):
        last_percent = pipes.log_progress(
            logger, resource_index, resource_count, last_percent, increment_percent=5
        )

        path_parts = Path(to_resource.path.lstrip("/")).parts
        path_parts_len = len(path_parts)

        for path_parts_index in range(1, path_parts_len):
            current_parts = path_parts[path_parts_index:]
            current_path = "/".join(current_parts)
            # The slash "/" prefix matters during the match as we do not want to
            # match on filenames sharing the same ending.
            # For example: Filter.java and FastFilter.java
            matches = from_resources.filter(path__endswith=f"/{current_path}")

            for match in matches:
                relation = CodebaseRelation.objects.filter(
                    from_resource=match,
                    to_resource=to_resource,
                    relationship=CodebaseRelation.Relationship.PATH_MATCH,
                )
                if not relation.exists():
                    pipes.make_relationship(
                        from_resource=match,
                        to_resource=to_resource,
                        relationship=CodebaseRelation.Relationship.PATH_MATCH,
                        match_type="path",
                        extra_data={
                            "path_score": f"{len(current_parts)}/{path_parts_len-1}",
                        },
                    )


def purldb_match(project, extensions, logger=None):
    to_resources = (
        project.codebaseresources.files()
        .to_codebase()
        .no_status()
        .has_value("sha1")
        .filter(extension__in=extensions)
    )

    if logger:
        resource_count = to_resources.count()
        extensions_str = ", ".join(extensions)
        logger(
            f"Matching {resource_count:,d} {extensions_str} resources against PurlDB"
        )

    for resource in to_resources:
        if results := purldb.match_by_sha1(sha1=resource.sha1):
            package_data = results[0]
            package_data.pop("dependencies")
            package = pipes.update_or_create_package(
                project=project,
                package_data=package_data,
                codebase_resource=resource,
            )
            extracted_resources = project.codebaseresources.to_codebase().filter(
                path__startswith=f"{resource.path}-extract"
            )
            package.add_resources(extracted_resources)
            extracted_resources.update(status="application-package")

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

FROM = "from/"
TO = "to/"


def checksum_match(project, checksum_field):
    """Match using checksum."""
    project_files = project.codebaseresources.files().has_no_relation().not_empty()

    from_resources = project_files.from_codebase().has_value(checksum_field)
    to_resources = project_files.to_codebase().has_value(checksum_field)

    for resource in from_resources:
        checksum_value = getattr(resource, checksum_field)
        matches = to_resources.filter(**{checksum_field: checksum_value})
        for match in matches:
            pipes.make_relationship(
                from_resource=resource,
                to_resource=match,
                relationship=CodebaseRelation.Relationship.IDENTICAL,
                match_type=checksum_field,
            )


def java_to_class_match(project):
    """Match a .java source to its compiled .class"""
    from_extension = ".java"
    to_extension = ".class"

    project_files = project.codebaseresources.files().has_no_relation()
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase()

    for resource in from_resources.filter(extension=from_extension):
        parts = resource.path[len(FROM) : -len(from_extension)]
        matches = to_resources.filter(path=f"{TO}{parts}{to_extension}")
        for match in matches:
            pipes.make_relationship(
                from_resource=resource,
                to_resource=match,
                relationship=CodebaseRelation.Relationship.COMPILED_TO,
                match_type="java_to_class",
            )


def java_to_inner_class_match(project):
    """Match a .java source to compiled $.class"""
    from_extension = ".java"
    to_extension = ".class"

    project_files = project.codebaseresources.files().has_no_relation()
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase()

    inner_classes = to_resources.filter(name__contains="$", extension=to_extension)
    for to_resource in inner_classes:
        parts = to_resource.path[len(TO) : -len(to_extension)]
        source_java = "/".join(parts.split("/")[:-1] + to_resource.name.split("$")[:1])
        matches = from_resources.filter(path=f"{FROM}{source_java}{from_extension}")
        for match in matches:
            pipes.make_relationship(
                from_resource=match,
                to_resource=to_resource,
                relationship=CodebaseRelation.Relationship.COMPILED_TO,
                match_type="java_to_class",
            )


def path_match(project):
    """Match using path similarities."""
    project_files = project.codebaseresources.files().has_no_relation()
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase()

    for resource in from_resources:
        path_parts = Path(resource.path.lstrip("/")).parts
        path_parts_len = len(path_parts)
        for index in range(1, path_parts_len):
            current_parts = path_parts[index:]
            current_path = "/".join(current_parts)
            # The slash "/" prefix matters during the match as we do not want to
            # match on filenames sharing the same ending.
            # For example: Filter.java and FastFilter.java
            matches = to_resources.filter(path__endswith=f"/{current_path}")

            for match in matches:
                relation = CodebaseRelation.objects.filter(
                    from_resource=resource,
                    to_resource=match,
                    relationship=CodebaseRelation.Relationship.PATH_MATCH,
                )
                if not relation.exists():
                    pipes.make_relationship(
                        from_resource=resource,
                        to_resource=match,
                        relationship=CodebaseRelation.Relationship.PATH_MATCH,
                        match_type="path",
                        extra_data={
                            "path_score": f"{len(current_parts)}/{path_parts_len-1}",
                        },
                    )

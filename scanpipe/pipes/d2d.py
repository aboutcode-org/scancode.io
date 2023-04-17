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

from collections import defaultdict
from pathlib import Path

from scanpipe import pipes
from scanpipe.models import CodebaseRelation

FROM = "from/"
TO = "to/"


def get_inputs(project):
    """Locate the `from` and `to` archives in project inputs directory."""
    from_file = list(project.inputs("from*"))
    to_file = list(project.inputs("to*"))

    if len(from_file) != 1:
        raise Exception("from* archive not found.")

    if len(to_file) != 1:
        raise Exception("to* archive not found.")

    return from_file[0], to_file[0]


def checksum_match(project, checksum_field):
    """Match using checksum."""
    project_files = project.codebaseresources.files().not_empty()
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


def count_similar_segments_reverse(path1, path2):
    """
    Count the number of similar path segments between two paths,
    starting from the rightmost segment.
    """
    segments1 = path1.split("/")
    segments2 = path2.split("/")
    count = 0

    while segments1 and segments2 and segments1[-1] == segments2[-1]:
        count += 1
        segments1.pop()
        segments2.pop()

    return count


def java_to_class_match(project):
    """Match a .java source to its compiled .class"""
    from_extension = ".java"
    to_extension = ".class"

    project_files = project.codebaseresources.files()
    from_resources = project_files.from_codebase().has_no_relation()
    to_resources = project_files.to_codebase()

    for resource in from_resources.filter(name__endswith=from_extension):
        to_name = resource.name.replace(from_extension, to_extension)
        name_matches = to_resources.filter(name=to_name)
        path_parts = Path(resource.path.lstrip("/")).parts

        match_by_similarity_count = defaultdict(list)
        for match in name_matches:
            path1 = "/".join(resource.path.split("/")[:-1])
            path2 = "/".join(match.path.split("/")[:-1])

            similarity_count = count_similar_segments_reverse(path1, path2)
            match_by_similarity_count[similarity_count].append(match)

        if not match_by_similarity_count:
            continue

        max_similarity_count = max(match_by_similarity_count.keys())
        best_matches = match_by_similarity_count[max_similarity_count]
        for match in best_matches:
            pipes.make_relationship(
                from_resource=resource,
                to_resource=match,
                relationship=CodebaseRelation.Relationship.COMPILED,
                match_type="java_to_class",
                extra_data={
                    "path_score": f"{max_similarity_count + 1}/{len(path_parts) - 1}",
                },
            )


# TODO: Remove duplication with java_to_class_match
def java_to_inner_class_match(project):
    """Match a .java source to its compiled inner $.class"""
    from_extension = ".java"
    to_extension = ".class"

    project_files = project.codebaseresources.files()
    from_resources = project_files.from_codebase()
    to_resources = project_files.to_codebase().has_no_relation()

    inner_classes = to_resources.filter(name__contains="$", name__endswith=to_extension)
    for resource in inner_classes:
        from_name = resource.name.split("$")[0] + from_extension
        name_matches = from_resources.filter(name=from_name)
        path_parts = Path(resource.path.lstrip("/")).parts

        match_by_similarity_count = defaultdict(list)
        for match in name_matches:
            path1 = "/".join(resource.path.split("/")[:-1])
            path2 = "/".join(match.path.split("/")[:-1])

            similarity_count = count_similar_segments_reverse(path1, path2)
            match_by_similarity_count[similarity_count].append(match)

        if not match_by_similarity_count:
            continue

        max_similarity_count = max(match_by_similarity_count.keys())
        best_matches = match_by_similarity_count[max_similarity_count]
        for match in best_matches:
            pipes.make_relationship(
                from_resource=match,
                to_resource=resource,
                relationship=CodebaseRelation.Relationship.COMPILED,
                match_type="java_to_class",
                extra_data={
                    "path_score": f"{max_similarity_count + 1}/{len(path_parts) - 1}",
                },
            )


def path_match(project):
    """Match using path similarities."""
    project_files = project.codebaseresources.files().only("path")
    from_resources = project_files.from_codebase().has_no_relation()
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

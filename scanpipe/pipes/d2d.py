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

from scanpipe import pipes
from scanpipe.models import CodebaseRelation


def checksum_match(project, checksum_field):
    """Match using checksum."""
    project_files = project.codebaseresources.files()

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
    prefix = "from/"
    extension = ".java"

    project_files = project.codebaseresources.files()
    from_resources = project_files.from_codebase().filter(path__endswith=extension)
    to_resources = project_files.to_codebase()

    for resource in from_resources:
        parts = resource.path[len(prefix) : -len(extension)]
        matches = to_resources.filter(path=f"to/{parts}.class")
        for match in matches:
            pipes.make_relationship(
                from_resource=resource,
                to_resource=match,
                relationship=CodebaseRelation.Relationship.COMPILED_TO,
                match_type="java_to_class",
            )

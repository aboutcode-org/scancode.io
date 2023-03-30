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

from django.db.models import Q

from scanpipe import pipes
from scanpipe.models import CodebaseRelation
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import scancode


def make_relationship(from_resource, to_resource, relationship, match_type):
    return CodebaseRelation.objects.create(
        project=from_resource.project,
        from_resource=from_resource,
        to_resource=to_resource,
        relationship=relationship,
        match_type=match_type,
    )


class DevelopToDeploy(Pipeline):
    """Relate develop and deploy code tree."""

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.extract_inputs_to_codebase_directory,
            cls.get_inputs,
            cls.collect_and_create_codebase_resources,
            cls.checksum_match,
            cls.java_to_class_match,
        )

    def get_inputs(self):
        """Locate the `from-` and `to-` archives."""
        from_file = list(self.project.inputs("from-*"))
        to_file = list(self.project.inputs("to-*"))

        if len(from_file) != 1:
            raise
        if len(to_file) != 1:
            raise

        self.from_file = from_file[0]
        self.to_file = to_file[0]

        self.from_path = self.project.codebase_path / "from"
        self.to_path = self.project.codebase_path / "to"

    def extract_inputs_to_codebase_directory(self):
        """Extract input files to the project's codebase/ directory."""
        errors = []
        errors += scancode.extract_archive(self.from_file, self.from_path)
        errors += scancode.extract_archive(self.to_file, self.to_path)

        if errors:
            self.add_error("\n".join(errors))

    def collect_and_create_codebase_resources(self):
        """Collect and create codebase resources."""
        for resource_path in self.project.walk_codebase_path():
            pipes.make_codebase_resource(
                project=self.project,
                location=str(resource_path),
            )

    def checksum_match(self):
        """Match using MD5 checksum."""
        project_resources = self.project.codebaseresources
        from_resources = project_resources.from_codebase().files().filter(~Q(md5=""))
        to_resources = project_resources.to_codebase()

        for resource in from_resources:
            matches = to_resources.filter(md5=resource.md5)
            for match in matches:
                make_relationship(
                    from_resource=resource,
                    to_resource=match,
                    relationship=CodebaseRelation.Relationship.IDENTICAL,
                    match_type="md5",
                )

    def java_to_class_match(self):
        """Match a .java source to its compiled .class"""
        prefix = "from/"
        extension = ".java"

        project_resources = self.project.codebaseresources
        from_resources = (
            project_resources.from_codebase().files().filter(path__endswith=extension)
        )
        to_resources = project_resources.to_codebase()

        for resource in from_resources:
            parts = resource.path[len(prefix) : -len(extension)]
            matches = to_resources.filter(path=f"to/{parts}.class")
            for match in matches:
                make_relationship(
                    from_resource=resource,
                    to_resource=match,
                    relationship=CodebaseRelation.Relationship.COMPILED_TO,
                    match_type="java_to_class",
                )

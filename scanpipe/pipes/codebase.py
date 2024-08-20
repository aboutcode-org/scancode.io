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

from commoncode.resource import VirtualCodebase

from scanpipe.models import Project


def sort_by_lower_name(resource):
    return resource["name"].lower()


def get_resource_fields(resource, fields):
    """Return a mapping of fields from `fields` and values from `resource`"""
    return {field: getattr(resource, field) for field in fields}


def get_resource_tree(resource, fields, codebase=None, seen_resources=set()):
    """
    Return a tree as a dictionary structure starting from the provided `resource`.

    The following classes are supported for the input `resource` object:
     - scanpipe.models.CodebaseResource
     - commoncode.resource.Resource

    The data included for each child is controlled with the `fields` argument.

    The `codebase` is only required in the context of a commoncode `Resource`
    input.

    `seen_resources` is used when get_resource_tree() is used in the context of
    get_codebase_tree(). We keep track of child Resources we visit in
    `seen_resources`, so we don't visit them again in get_codebase_tree().
    """
    resource_dict = get_resource_fields(resource, fields)

    if resource.is_dir:
        children = []
        for child in resource.children(codebase):
            seen_resources.add(child.path)
            children.append(get_resource_tree(child, fields, codebase, seen_resources))
        if children:
            resource_dict["children"] = sorted(children, key=sort_by_lower_name)

    return resource_dict


def get_codebase_tree(codebase, fields):
    """
    Return a tree as a dictionary structure starting from the root resources of
    the provided `codebase`.

    The following classes are supported for the input `codebase` object:
     - scanpipe.pipes.codebase.ProjectCodebase
     - commoncode.resource.Codebase
     - commoncode.resource.VirtualCodebase

    The data included for each child is controlled with the `fields` argument.
    """
    seen_resources = set()
    codebase_dict = dict(children=[])
    for resource in codebase.walk():
        path = resource.path
        if path in seen_resources:
            continue
        else:
            seen_resources.add(path)
        resource_dict = get_resource_fields(resource, fields)
        if resource.is_dir:
            children = []
            for child in resource.children(codebase):
                seen_resources.add(child.path)
                children.append(
                    get_resource_tree(child, fields, codebase, seen_resources)
                )
            if children:
                resource_dict["children"] = sorted(children, key=sort_by_lower_name)
        codebase_dict["children"].append(resource_dict)
    return codebase_dict


def get_basic_virtual_codebase(resources_qs):
    """
    Return a VirtualCodebase created from CodebaseResources in `resources_qs`.

    The only Resource fields that are populated are path, sha1, size, and
    is_file. This is intended for use with
    scanpipe.pipes.matchcode.fingerprint_codebase_directories
    """
    resources = [
        {"path": r.path, "sha1": r.sha1, "size": r.size, "is_file": r.is_file}
        for r in resources_qs
    ]
    return VirtualCodebase(location={"files": resources})


class ProjectCodebase:
    """
    Represents the codebase of a project stored in the database.
    A Codebase is a tree of Resources.
    """

    project = None

    def __init__(self, project):
        if not isinstance(project, Project):
            raise ValueError("Provided value for project is not a Project instance.")
        self.project = project

    @property
    def root_resources(self):
        return self.project.codebaseresources.exclude(path__contains="/")

    @property
    def resources(self):
        return self.project.codebaseresources.all()

    def walk(self, topdown=True):
        for root_resource in self.root_resources:
            if topdown:
                yield root_resource
            yield from root_resource.walk(topdown=topdown)
            if not topdown:
                yield root_resource

    def get_tree(self):
        return get_codebase_tree(self, fields=["name", "path"])

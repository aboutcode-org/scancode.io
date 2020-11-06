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

import packagedcode
from packageurl import PackageURL
from scancode.resource import VirtualCodebase

from scanpipe import pipes
from scanpipe.models import CodebaseResource


"""
Utilities to deal with ScanCode objects, in particular Codebase and Package.
"""


def get_virtual_codebase(project, input_location):
    """
    Return a ScanCode virtual codebase built from the JSON scan file at
    `input_location`.
    """
    temp_path = project.tmp_path / "scancode-temp-resource-cache"
    temp_path.mkdir(parents=True, exist_ok=True)

    return VirtualCodebase(
        location=input_location, temp_dir=str(temp_path), max_in_memory=0
    )


def create_codebase_resources(project, scanned_codebase):
    """
    Save the resources of a ScanCode `scanned_codebase`
    scancode.resource.Codebase object to the DB as CodebaseResource of
    `project`.
    """
    for scanned_resource in scanned_codebase.walk():
        path = scanned_resource.path
        resource_type = "FILE" if scanned_resource.is_file else "DIRECTORY"
        file_infos = dict(
            type=CodebaseResource.Type[resource_type],
            name=scanned_resource.name,
            extension=scanned_resource.extension,
            size=scanned_resource.size,
            sha1=getattr(scanned_resource, "sha1", None),
            md5=getattr(scanned_resource, "md5", None),
            mime_type=getattr(scanned_resource, "mime_type", None),
            file_type=getattr(scanned_resource, "file_type", None),
            programming_language=getattr(
                scanned_resource, "programming_language", None
            ),
        )
        # Skips empty value to avoid null vs. '' conflicts
        file_infos = {name: value for name, value in file_infos.items() if value}

        cbr = CodebaseResource(project=project, path=path, **file_infos)
        cbr.save()


def create_discovered_packages(project, scanned_codebase):
    """
    Save the packages of a ScanCode `scanned_codebase`
    scancode.resource.Codebase object to the DB as DiscoveredPackage of
    `project`. Relate package resources to CodebaseResource.
    """
    for scanned_resource in scanned_codebase.walk():
        cbr = CodebaseResource.objects.get(project=project, path=scanned_resource.path)

        scanned_packages = getattr(scanned_resource, "packages", []) or []

        for scan_data in scanned_packages:
            discovered_package = pipes.update_or_create_package(project, scan_data)

            # set the current resource as being for this package
            set_codebase_resource_for_package(
                codebase_resource=cbr, discovered_package=discovered_package
            )

            scanned_package = packagedcode.get_package_instance(scan_data)

            # also set all the resource attached to that package
            scanned_package_resources = scanned_package.get_package_resources(
                scanned_resource, scanned_codebase
            )

            for scanned_package_res in scanned_package_resources:
                package_cbr = CodebaseResource.objects.get(
                    project=project, path=scanned_package_res.path
                )

                set_codebase_resource_for_package(
                    codebase_resource=package_cbr, discovered_package=discovered_package
                )

            # also set dependencies as their own packages
            # TODO: we should instead relate these to the package
            # TODO: we likely need a status for DiscoveredPackage
            dependencies = scanned_package.dependencies or []
            for dependency in dependencies:
                # FIXME: we should get DependentPackage instances and not a mapping
                purl = getattr(dependency, "purl", None)
                if not purl:
                    # TODO: we should log that
                    continue
                purl = PackageURL.from_string(purl)
                dep = purl.to_dict()
                dependent_package = pipes.update_or_create_package(project, dep)

                # attached to the current resource (typically a manifest?)
                set_codebase_resource_for_package(
                    codebase_resource=cbr, discovered_package=dependent_package
                )


def set_codebase_resource_for_package(codebase_resource, discovered_package):
    codebase_resource.discovered_packages.add(discovered_package)
    codebase_resource.status = "application-package"
    codebase_resource.save()

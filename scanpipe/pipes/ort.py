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


from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

import saneyaml

"""
This module provides Python dataclass models for representing a package list
in a format compatible with the OSS Review Toolkit (ORT)
`CreateAnalyzerResultFromPackageListCommand`.

The models are simplified adaptations of the Kotlin classes from:
https://github.com/oss-review-toolkit/ort/blob/main/cli-helper/src/main/kotlin/commands/CreateAnalyzerResultFromPackageListCommand.kt

This module is intended for generating ORT-compatible YAML package lists from Python
objects, allowing integration with ORT's analyzer workflows or manual creation of
package metadata.
"""


# private data class SourceArtifact(
#     val url: String,
#     val hash: Hash? = null
# )
@dataclass
class SourceArtifact:
    url: str
    # Cannot coerce empty String ("") to `org.ossreviewtoolkit.model.Hash` value
    # hash: str = None


# private data class Vcs(
#     val type: String? = null,
#     val url: String? = null,
#     val revision: String? = null,
#     val path: String? = null
# )
@dataclass
class Vcs:
    type: str = None
    url: str = None
    revision: str = None
    path: str = None


# private data class Dependency(
#     val id: Identifier,
#     val purl: String? = null,
#     val vcs: Vcs? = null,
#     val sourceArtifact: SourceArtifact? = null,
#     val declaredLicenses: Set<String> = emptySet(),
#     val concludedLicense: SpdxExpression? = null,
#     val description: String? = null,
#     val homepageUrl: String? = null,
#     val authors: Set<String> = emptySet(),
#     val isExcluded: Boolean = false,
#     val isDynamicallyLinked: Boolean = false,
#     val labels: Map<String, String> = emptyMap()
# )
@dataclass
class Dependency:
    id: str
    purl: str = None
    vcs: Vcs = None
    sourceArtifact: SourceArtifact = None
    declaredLicenses: list = field(default_factory=set)
    # concludedLicense: str = None
    description: str = None
    homepageUrl: str = None
    authors: list = field(default_factory=set)
    # isExcluded: bool = False
    # isDynamicallyLinked: bool = False
    # labels: dict = field(default_factory=dict)


# private data class PackageList(
#     val projectName: String? = null,
#     val projectVcs: Vcs? = null,
#     val dependencies: List<Dependency> = emptyList()
# )
@dataclass
class PackageList:
    projectName: str
    projectVcs: Vcs = field(default_factory=Vcs)
    dependencies: list = field(default_factory=list)

    def to_yaml(self):
        """Dump the Project object back to a YAML string."""
        return saneyaml.dump(asdict(self))

    def to_file(self, filepath):
        """Write the Project object to a YAML file."""
        Path(filepath).write_text(self.to_yaml(), encoding="utf-8")


def get_ort_project_type(project):
    """
    Determine the ORT project type based on the project's input sources.

    Currently, this function checks whether any of the project's
    input download URLs start with "docker://".
    If at least one Docker URL is found, it returns "docker".
    """
    inputs_url = project.inputsources.values_list("download_url", flat=True)
    if any(url.startswith("docker://") for url in inputs_url):
        return "docker"


def sanitize_id_part(value):
    """
    Sanitize an identifier part by replacing colons with underscores.
    ORT uses colons as separators in the identifier string representation.
    """
    if value:
        return value.replace(":", "_")
    return value


def to_ort_package_list_yml(project):
    """Convert a project object into a YAML string in the ORT package list format."""
    project_type = get_ort_project_type(project)

    dependencies = []
    for package in project.discoveredpackages.all():
        type_ = sanitize_id_part(project_type or package.type)
        name = sanitize_id_part(package.name)
        version = sanitize_id_part(package.version)

        dependency = Dependency(
            id=f"{type_}::{name}:{version}",
            purl=package.purl,
            sourceArtifact=SourceArtifact(url=package.download_url),
            declaredLicenses=[package.get_declared_license_expression_spdx()],
            vcs=Vcs(url=package.vcs_url),
            description=package.description,
            homepageUrl=package.homepage_url,
            authors=package.get_author_names(),
        )
        dependencies.append(dependency)

    package_list = PackageList(
        projectName=project.name,
        dependencies=dependencies,
    )

    return package_list.to_yaml()

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

import yaml


@dataclass
class SourceArtifact:
    url: str


@dataclass
class VCS:
    type: str = ""
    url: str = ""
    revision: str = ""
    path: str = ""
    sourceArtifact: SourceArtifact | None = None


@dataclass
class Dependency:
    id: str
    purl: str
    sourceArtifact: SourceArtifact
    declaredLicenses: list[str] = field(default_factory=list)


@dataclass
class Project:
    projectName: str
    dependencies: list[Dependency] = field(default_factory=list)
    projectVcs: VCS = field(default_factory=VCS)

    @classmethod
    def from_yaml(cls, yaml_str: str):
        """Create a Project object from a YAML string."""
        data = yaml.safe_load(yaml_str)

        # Parse dependencies
        dependencies = [
            Dependency(
                id=dependency["id"],
                purl=dependency["purl"],
                sourceArtifact=SourceArtifact(**dependency["sourceArtifact"]),
                declaredLicenses=dependency.get("declaredLicenses", []),
            )
            for dependency in data.get("dependencies", [])
        ]

        # Optional projectVcs
        vcs_data = data.get("projectVcs", {})
        project_vcs = VCS(**vcs_data) if vcs_data else VCS()

        return cls(
            projectName=data["projectName"],
            dependencies=dependencies,
            projectVcs=project_vcs,
        )

    @classmethod
    def from_file(cls, filepath: str | Path):
        """Create a Project object by loading a YAML file."""
        return cls.from_yaml(Path(filepath).read_text(encoding="utf-8"))

    def to_yaml(self) -> str:
        """Dump the Project object back to a YAML string."""
        return yaml.safe_dump(asdict(self), sort_keys=False, allow_unicode=True)

    def to_file(self, filepath: str | Path):
        """Write the Project object to a YAML file."""
        Path(filepath).write_text(self.to_yaml(), encoding="utf-8")


def to_ort_package_list_yml(project):
    dependencies = []
    for package in project.discoveredpackages.all():
        dependency = Dependency(
            id=f"{package.type}::{package.name}:{package.version}",
            purl=package.purl,
            sourceArtifact=SourceArtifact(url=package.download_url),
            declaredLicenses=[package.get_declared_license_expression_spdx()],
        )
        dependencies.append(dependency)

    project = Project(
        projectName=project.name,
        dependencies=dependencies,
    )

    return project.to_yaml()

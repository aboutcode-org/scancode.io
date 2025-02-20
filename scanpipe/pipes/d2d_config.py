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


class EcosystemConfig:
    """
    Base class for ecosystem specific configurations to be defined
    for each ecosystems.
    """

    # This should be defined for each ecosystem which
    # are options in the pipelines
    ecosystem_option = None

    # These are extensions for packages of this ecosystem which
    # needs to be matched from purldb
    purldb_package_extensions = []

    # These are extensions for resources of this ecosystem which
    # needs to be macthed from purldb
    purldb_resource_extensions = []

    # Extensions for document files which do not require review
    doc_extensions = []

    # Paths in the deployed binaries/archives (on the to/ side) which
    # do not need review even if they are not matched to the source side
    deployed_resource_path_exclusions = []

    # Paths in the developement/source archive (on the from/ side) which
    # should not be considered even if unmapped to the deployed side when
    # assesing what to review on the deployed side
    devel_resource_path_exclusions = []

    # Symbols which are found in ecosystem specific standard libraries
    # which are not so useful in mapping
    standard_symbols_to_exclude = []


class DefaultEcosystemConfig(EcosystemConfig):
    """Configurations which are common across multiple ecosystems."""

    ecosystem_option = "Default"
    purldb_package_extensions = [".zip", ".tar.gz", ".tar.xz"]
    devel_resource_path_exclusions = ["*/tests/*"]
    doc_extensions = [
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".tex",
        ".odt",
        ".odp",
    ]


class JavaEcosystemConfig(EcosystemConfig):
    ecosystem_option = "Java"
    purldb_package_extensions = [".jar", ".war"]
    purldb_resource_extensions = [".class"]


class JavaScriptEcosystemConfig(EcosystemConfig):
    ecosystem_option = "JavaScript"
    purldb_resource_extensions = [
        ".map",
        ".js",
        ".mjs",
        ".ts",
        ".d.ts",
        ".jsx",
        ".tsx",
        ".css",
        ".scss",
        ".less",
        ".sass",
        ".soy",
    ]


class GoEcosystemConfig(EcosystemConfig):
    ecosystem_option = "Go"
    purldb_resource_extensions = [".go"]


class RustEcosystemConfig(EcosystemConfig):
    ecosystem_option = "Rust"
    purldb_resource_extensions = [".rs"]


class RubyEcosystemConfig(EcosystemConfig):
    ecosystem_option = "Ruby"
    purldb_package_extensions = [".gem"]
    purldb_resource_extensions = [".rb"]
    deployed_resource_path_exclusions = ["*checksums.yaml.gz*", "*metadata.gz*"]

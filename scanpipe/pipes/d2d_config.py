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


from dataclasses import dataclass
from dataclasses import field


@dataclass
class EcosystemConfig:
    """
    Base class for ecosystem-specific configurations to be defined
    for each ecosystem.
    """

    # This should be defined for each ecosystem which
    # are options in the pipelines
    ecosystem_option: str = "Default"

    # These are extensions for package archive files for this ecosystem
    # that are matchable against the purldb using matchcode
    matchable_package_extensions: list = field(default_factory=list)

    # These are extensions for file of this ecosystem that are
    # matchable against the purldb using matchcode
    matchable_resource_extensions: list = field(default_factory=list)

    # Extensions for document files which do not require review
    doc_extensions: list = field(default_factory=list)

    # Paths in the deployed binaries/archives (on the to/ side) which
    # do not need review even if they are not matched to the source side
    deployed_resource_path_exclusions: list = field(default_factory=list)

    # Paths in the development/source archive (on the from/ side) which
    # should not be considered even if unmapped to the deployed side when
    # assessing what to review on the deployed side
    devel_resource_path_exclusions: list = field(default_factory=list)

    # Symbols which are found in ecosystem-specific standard libraries
    # which are not so useful in mapping
    standard_symbols_to_exclude: list = field(default_factory=list)

    # File extesions which should be looked at for source symbol extraction
    # for mapping using symbols for a specific selected option/ecosystem
    source_symbol_extensions: list = field(default_factory=list)


# Dictionary of ecosystem configurations
ECOSYSTEM_CONFIGS = {
    "Default": EcosystemConfig(
        matchable_package_extensions=[".zip", ".tar.gz", ".tar.xz"],
        devel_resource_path_exclusions=["*/tests/*"],
        doc_extensions=[
            ".pdf",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".tex",
            ".odt",
            ".odp",
        ],
        deployed_resource_path_exclusions=["*.properties", "*.html"],
    ),
    "Java": EcosystemConfig(
        ecosystem_option="Java",
        matchable_package_extensions=[".jar", ".war"],
        matchable_resource_extensions=[".class"],
        deployed_resource_path_exclusions=[
            "*META-INF/*",
            "*/module-info.class",
            "*/OSGI-INF/*.xml",
            "*/OSGI-INF/*.json",
            "*spring-configuration-metadata.json",
        ],
    ),
    "Scala": EcosystemConfig(
        ecosystem_option="Scala",
        matchable_package_extensions=[".jar", ".war"],
        matchable_resource_extensions=[".class"],
        deployed_resource_path_exclusions=[
            "*META-INF/*",
        ],
    ),
    "Kotlin": EcosystemConfig(
        ecosystem_option="Kotlin",
        matchable_package_extensions=[".jar", ".war"],
        matchable_resource_extensions=[".class"],
        deployed_resource_path_exclusions=[
            "*META-INF/*",
            "*.knm",
            "*kotlin-project-structure-metadata.json",
        ],
    ),
    "Groovy": EcosystemConfig(
        ecosystem_option="Groovy",
        matchable_package_extensions=[".jar", ".war"],
        matchable_resource_extensions=[".class"],
        deployed_resource_path_exclusions=[
            "*META-INF/*",
        ],
    ),
    "JavaScript": EcosystemConfig(
        ecosystem_option="JavaScript",
        matchable_resource_extensions=[
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
        ],
        source_symbol_extensions=[".ts", ".js"],
    ),
    "Go": EcosystemConfig(
        ecosystem_option="Go",
        matchable_resource_extensions=[".go"],
        source_symbol_extensions=[".go"],
    ),
    "Rust": EcosystemConfig(
        ecosystem_option="Rust",
        matchable_resource_extensions=[".rs"],
        source_symbol_extensions=[".rs"],
    ),
    "Ruby": EcosystemConfig(
        ecosystem_option="Ruby",
        matchable_package_extensions=[".gem"],
        matchable_resource_extensions=[".rb"],
        deployed_resource_path_exclusions=[
            "*checksums.yaml.gz*",
            "*metadata.gz*",
            "*data.tar.gz.sig",
        ],
    ),
    "Elf": EcosystemConfig(
        ecosystem_option="Elf",
        source_symbol_extensions=[".c", ".cpp", ".h"],
    ),
    "MacOS": EcosystemConfig(
        ecosystem_option="MacOS",
        source_symbol_extensions=[".c", ".cpp", ".h", ".m", ".swift"],
    ),
    "Windows": EcosystemConfig(
        ecosystem_option="Windows",
        source_symbol_extensions=[".c", ".cpp", ".h", ".cs"],
    ),
    "Python": EcosystemConfig(
        ecosystem_option="Python",
        source_symbol_extensions=[".pyx", ".pxd", ".py", ".pyi"],
        matchable_resource_extensions=[".py", ".pyi"],
    ),
}


def get_ecosystem_config(ecosystem):
    """Return the ``ecosystem`` config."""
    return ECOSYSTEM_CONFIGS.get(ecosystem, ECOSYSTEM_CONFIGS["Default"])


def load_ecosystem_config(pipeline, options):
    """
    Add ecosystem specific configurations for each ecosystem selected
    as `options` to the `pipeline`. These configurations are used for:
    - which resource/package extensions to match to purldb
    - which source files to get source symbols from
    - which unmapped paths to ignore in deployed binaries
    """
    # Add default configurations which are common across ecosystems
    pipeline.ecosystem_config = ECOSYSTEM_CONFIGS.get("Default")

    # Add configurations for each selected ecosystem
    for selected_option in options:
        if selected_option not in ECOSYSTEM_CONFIGS:
            continue

        ecosystem_config = get_ecosystem_config(ecosystem=selected_option)
        add_ecosystem_config(
            pipeline_ecosystem_config=pipeline.ecosystem_config,
            ecosystem_config=ecosystem_config,
        )


def add_ecosystem_config(pipeline_ecosystem_config, ecosystem_config):
    """
    Set the `pipeline_ecosystem_config` values from an individual ecosystem
    based configuration defined in `ecosystem_config`.
    """
    d2d_pipeline_configs = [
        "matchable_package_extensions",
        "matchable_resource_extensions",
        "deployed_resource_path_exclusions",
    ]

    for config_name in d2d_pipeline_configs:
        config_value = getattr(ecosystem_config, config_name)
        pipeline_config_value = getattr(pipeline_ecosystem_config, config_name)
        if config_value:
            if not pipeline_config_value:
                new_config_value = config_value
            else:
                new_config_value = config_value + pipeline_config_value
            setattr(pipeline_ecosystem_config, config_name, new_config_value)

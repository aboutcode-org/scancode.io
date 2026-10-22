import json
import subprocess
from os import environ

from scanpipe.pipes import atom
from scanpipe.pipes import run_command_safely
from scanpipe.pipes.reachability_tools import ReachabilityPipeline
from scanpipe.pipes.reachability_tools import ReachabilityTool

ATOM_EXECUTABLE = environ.get("ATOM_EXECUTABLE")


class AtomTool(ReachabilityTool):
    tool_name = "atom"
    executable = ATOM_EXECUTABLE
    supported_languages = {
        "Java": "java",
        "Python": "python",
    }

    commands = ("usages", "reachables")

    @classmethod
    def get_availability(cls):
        if not cls.executable:
            return (
                "atom is not configured. Set the ATOM_EXECUTABLE environment variable."
            )

    @classmethod
    def get_atom_language(cls, project):
        """Return the atom ``-l`` value for ``project``."""
        package = project.discoveredpackages.first()
        if package and package.primary_language:
            language = cls.supported_languages.get(package.primary_language)
            if language:
                return language
        raise ValueError(f"Could not determine an atom language for {project.name!r}.")

    @classmethod
    def get_target_path(cls, project):
        target_path = project.codebase_path
        if target_path:
            return target_path

        resource = project.codebaseresources.filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=list(cls.supported_languages),
        ).first()

        if not resource:
            raise ValueError("No codebase resources found for this project.")
        return resource.location_path

    @classmethod
    def get_output_paths(cls, project, atom_language):
        """Return the output paths shared by the atom commands."""
        manifest_path = project.get_output_file_path("atom_reachability", "json")
        prefix = f"{manifest_path.stem}.{atom_language}"
        return {
            "atom": manifest_path.with_name(f"{prefix}.atom"),
            "usages": manifest_path.with_name(f"{prefix}.usages.slices.json"),
            "reachables": manifest_path.with_name(f"{prefix}.reachables.slices.json"),
        }

    @classmethod
    def run_command(
        cls, command, target_path, atom_language, output_paths, logger=None
    ):
        """Run a single atom command and return its slices file path or None."""
        command_args = [
            cls.executable,
            command,
            "-l",
            atom_language,
            "-o",
            str(output_paths["atom"]),
            "-s",
            str(output_paths[command]),
            str(target_path),
        ]

        logger(f"Running atom {command} on {target_path} ...")
        try:
            run_command_safely(command_args=command_args)
        except subprocess.SubprocessError as error:
            if logger:
                logger(f"atom {command} failed: {error!r}")
            return None
        return output_paths[command]

    @classmethod
    def run(cls, project, logger=None):
        """
        Run the atom ``usages`` and ``reachables`` commands.

        Return a mapping of command name to its slices file path (or ``None``
        when that command failed).
        """
        target_path = cls.get_target_path(project)
        atom_language = cls.get_atom_language(project)
        output_paths = cls.get_output_paths(project, atom_language)

        results = {}
        for command in cls.commands:
            results[command] = cls.run_command(
                command=command,
                target_path=target_path,
                atom_language=atom_language,
                output_paths=output_paths,
                logger=logger,
            )
        return results

    @classmethod
    def load_slices(cls, export_output_path, logger=None):
        """Load and return a single atom slices file."""
        if not export_output_path:
            return {}
        try:
            with open(export_output_path) as slice_file:
                return json.load(slice_file)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            if logger:
                logger(f"Skipping atom slices {export_output_path}: {error!r}")
            return {}

    @classmethod
    def parsed_output(cls, export_output_path, logger=None):
        """Load and return the atom slices keyed by command name."""
        if not export_output_path:
            return {}
        return {
            command: cls.load_slices(path, logger=logger)
            for command, path in export_output_path.items()
        }


class AtomReachability(ReachabilityPipeline):
    """
    Determine the reachability of vulnerabilities using the atom tool.

    Note: You must run the ``find_vulnerabilities`` pipeline before running
    this pipeline.

    atom is run twice against the project codebase:

    - ``usages`` writes a usages slice of the code.
    - ``reachables`` writes a reachables slice of the symbols
     that can actually be reached.

    The vulnerable and fixed symbols of each patch are matched against those
    slices:

    - REACHABLE: the symbol has a call site in the code
    - UNKNOWN: the symbol is defined in the code
    - NOT_REACHABLE: the symbol is absent

    Results are stored in the ``extra_data`` of the matching resources under
    the ``symbols_reachability`` key.
    """

    reachability_tool = AtomTool

    @classmethod
    def get_availability(cls):
        return cls.reachability_tool.get_availability()

    def get_candidate_resources(self):
        """Collect candidate resources for this pipeline."""
        self.candidate_resources = self.project.codebaseresources.files().filter(
            is_binary=False,
            is_archive=False,
            is_media=False,
            programming_language__in=list(self.reachability_tool.supported_languages),
        )

    def collect_resource_index(self):
        """Run the atom usages and reachables commands and load both slices."""
        self.resource_indexes_path = self.reachability_tool.run(
            project=self.project, logger=self.log
        )
        indexes = self.reachability_tool.parsed_output(
            export_output_path=self.resource_indexes_path, logger=self.log
        )
        self.resource_indexes_usages = indexes.get("usages") or {}
        self.resource_indexes_reachability = indexes.get("reachables") or {}

    def collect_and_match_resources(self):
        """Match patch symbols against the atom slices."""
        if not self.resource_indexes_usages and not self.resource_indexes_reachability:
            self.log("No atom usages or reachables slices available for matching.")
            return

        atom.collect_and_match_resources(
            tool_name=self.reachability_tool.tool_name,
            patches=self.patches,
            patch_symbols=self.patch_symbols,
            usages_slices=self.resource_indexes_usages,
            reachables_slices=self.resource_indexes_reachability,
            candidate_resources=self.candidate_resources,
            logger=self.log,
        )

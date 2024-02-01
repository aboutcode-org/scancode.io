from pathlib import Path

from elf_inspector.dwarf import get_dwarf_paths

from scanpipe.models import CodebaseResource
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import purldb
from scanpipe.pipes import scancode


class GetDwarfsFromElfs(Pipeline):
    """Get dwarfs from elfs."""

    download_inputs = False
    is_addon = True

    @classmethod
    def steps(cls):
        return (cls.get_dwarfs_from_elfs,)

    def get_dwarfs_from_elfs(self):
        """
        Update ``extra_data`` of project with
        dwarf data extracted from elf files.
        """
        for elf in self.project.codebaseresources.elfs():
            data = get_dwarf_paths(Path(self.project.codebase_path / elf.path))
            self.project.update_extra_data({elf.path: data})

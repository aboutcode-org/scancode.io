from scanpipe.pipelines import Pipeline
from scanpipe.pipes import output
from scanpipe.pipes import glc, scancode
from scanpipe.pipes.input import copy_inputs


class TestPipeline(Pipeline):
    """
    A pipeline to scan a codebase with GoLicense-Classifier for Copyright and License Detection
    """

    extractcode_options = [
        "--shallow",
        "--all-formats",
    ]

    def copy_inputs_to_codebase_directory(self):
        """
        Copy input files to the project codebase/ directory.
        The code can also be copied there prior to running the Pipeline.
        """
        copy_inputs(self.project.inputs(), self.project.codebase_path)

    def run_extractcode(self):
        """
        Extract with extractcode.
        """
        with self.save_errors(scancode.ScancodeError):
            scancode.run_extractcode(
                location=str(self.project.codebase_path),
                options=self.extractcode_options,
                raise_on_error=True,
            )

    def run_glc(self):
        """
        Scan extracted codebase/ content.
        """
        self.scan_output = self.project.get_output_file_path("scancode", "json")
        # print(self.scan_output)
        glc.run_glc(
            location=str(self.project.codebase_path),
            output_file=str(self.scan_output),
        )

        if not self.scan_output.exists():
            raise FileNotFoundError("GLC output not available.")

    def build_inventory_from_scan(self):
        """
        Process the JSON scan results to populate resources and packages.
        """
        project = self.project
        scan_data = glc.to_dict(str(self.scan_output))
        glc.create_codebase_resources(project, scan_data)

    def csv_output(self):
        """
        Generate csv outputs.
        """
        output.to_csv(self.project)

    steps = (
        copy_inputs_to_codebase_directory,
        run_extractcode,
        run_glc,
        build_inventory_from_scan,
        csv_output,
    )

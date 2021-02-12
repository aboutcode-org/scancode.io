// Release notes
// -------------

### v1.1.0 (unreleased)

- Implement Pipeline registration through distribution entry points
  Pipeline can now be installed as part of external libraries
  https://github.com/nexB/scancode.io/issues/91

- Add a "Run Pipeline" button in the Pipeline modal of the Project details view
  Pipelines can now be added from the Project details view
  https://github.com/nexB/scancode.io/issues/84

- Upgrade scancode-toolkit to version 21.2.9

- Allow to start the pipeline run immediately on addition in the `add_pipeline` action
  of the Project API endpoint
  https://github.com/nexB/scancode.io/issues/92

- Rename the pipes.outputs module to pipes.output for consistency

- Remove the dependency on Metaflow
  WARNING: The new Pipelines syntax is not backward compatible with v1.0.x
  https://github.com/nexB/scancode.io/issues/82

### v1.0.7 (2021-02-01)

- Add user interface to manage Projects from a web browser
  All the command-line features are available
  https://github.com/nexB/scancode.io/issues/24

- Log messages from Pipeline execution on a new Run instance `log` field
  https://github.com/nexB/scancode.io/issues/66

- Add support for scancode pipes and Project name with whitespaces

- Add a profile() method on the Run model for profiling pipeline execution
  https://github.com/nexB/scancode.io/issues/73

### v1.0.6 (2020-12-23)

- Add a management command to delete a Project and its related work directories
  https://github.com/nexB/scancode.io/issues/65

- Add CSV and XLSX support for the `output` management command
  https://github.com/nexB/scancode.io/issues/46

- Add a to_xlsx output pipe returning XLSX compatible content
  https://github.com/nexB/scancode.io/issues/46

- Add a "status" management command to display Project status information
  https://github.com/nexB/scancode.io/issues/66

- Fix the env_file location to run commands from outside the root dir
  https://github.com/nexB/scancode.io/issues/64

- Add utilities to save project error in the database during Pipeline execution
  https://github.com/nexB/scancode.io/issues/64

- Install psycopg2-binary instead of psycopg2 on non-Linux platforms
  https://github.com/nexB/scancode.io/issues/64

### v1.0.5 (2020-12-07)

- Add minimal license list and text views
  https://github.com/nexB/scancode.io/issues/32

- Add admin actions to export selected objects to CSV and JSON
  The output content, such as included fields, can be configured for CSV format
  https://github.com/nexB/scancode.io/issues/48
  https://github.com/nexB/scancode.io/issues/49

- Add --list option to the graph management command.
  Multiple graphs can now be generated at once.

- Add ProjectCodebase to help walk and navigate Project CodebaseResource
  loaded from the Database
  Add also a get_tree function compatible with scanpipe.CodebaseResource and
  commoncode.Resource
  https://github.com/nexB/scancode.io/issues/52

- Add support for running ScanCode.io as a Docker image
  https://github.com/nexB/scancode.io/issues/9

- Add support for Python 3.7, 3.8, and 3.9
  https://github.com/nexB/scancode.io/issues/54

### v1.0.4 (2020-11-17)

- Add a to_json output pipe returning ScanCode compatible content
  https://github.com/nexB/scancode.io/issues/45

- Improve Admin UI for efficient review:
  display, navigation, filters, and ability to view file content
  https://github.com/nexB/scancode.io/issues/36

- Add Pipelines and Pipes documentation using Sphinx autodoc
  Fix for https://github.com/nexB/scancode.io/issues/38

- Add new ScanCodebase pipeline for codebase scan
  Fix for https://github.com/nexB/scancode.io/issues/37

- Upgrade Django, Metaflow, and ScanCode-toolkit to latest versions

### v1.0.3 (2020-09-24)

- Add ability to resume a failed pipeline from the run management command
  Fix for https://github.com/nexB/scancode.io/issues/22

- Use project name as argument to run a pipeline
  Fix for https://github.com/nexB/scancode.io/issues/18

- Add support for "failed" task_output in Run.get_run_id method
  Fix for https://github.com/nexB/scancode.io/issues/17

### v1.0.2 (2020-09-18)

- Add documentation and tutorial
  For https://github.com/nexB/scancode.io/issues/8

- Add a create-project, add-input, add-pipeline, run, output
  management commands to expose ScanPipe features through the command line
  Fix for https://github.com/nexB/scancode.io/issues/13

- Always return the Pipeline subclass/implementation from the module inspection
  Fix for https://github.com/nexB/scancode.io/issues/11

### v1.0.1 (2020-09-12)

- Do not fail when collecting system packages in Ubuntu docker images for
  layers that do not install packages by updating to a newer version of
  ScanCode Toolkit
  Fix for https://github.com/nexB/scancode.io/issues/1

### v1.0.0 (2020-09-09)

- Initial release
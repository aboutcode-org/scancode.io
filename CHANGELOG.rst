// Release notes
// -------------

### Unreleased

- Upgrade ScanCode-toolkit to version 30.1.0

- Replace the task queue system, from Celery to RQ.
  https://github.com/nexB/scancode.io/issues/176

- Add ability to delete "not started" and "queued" pipeline tasks.
  https://github.com/nexB/scancode.io/issues/176

- Add ability to stop "running" pipeline tasks.
  https://github.com/nexB/scancode.io/issues/176

- Refactor the "execute" management command and add support for --async mode.
  https://github.com/nexB/scancode.io/issues/130

- Include codebase resource data in the details of package creation project errors.
  https://github.com/nexB/scancode.io/issues/208

- Add a SCANCODEIO_REST_API_PAGE_SIZE setting to control the number of objects
  returned per page in the REST API.
  https://github.com/nexB/scancode.io/issues/328

- Provide an "add input" action on the Project endpoint of the REST API.
  https://github.com/nexB/scancode.io/issues/318

### v21.9.6

- Add ability to "archive" projects, from the Web UI, API and command line interface.
  Data cleanup of the project's input, codebase, and output directories is available
  during the archive operation.
  Archived projects cannot be modified anymore and are hidden by default from the
  project list.
  A project cannot be archived if one of its related run is queued or already running.
  https://github.com/nexB/scancode.io/issues/312

- Remove the run_extractcode pipe in favor of extractcode API.
  https://github.com/nexB/scancode.io/issues/312

- The `scancode.run_scancode` pipe now uses an optimal number of available CPUs for
  multiprocessing by default.
  The exact number of parallel processes available to ScanCode.io can be defined
  using the SCANCODEIO_PROCESSES setting.
  https://github.com/nexB/scancode.io/issues/302

- Renamed the SCANCODE_DEFAULT_OPTIONS setting to SCANCODE_TOOLKIT_CLI_OPTIONS.
  https://github.com/nexB/scancode.io/issues/302

- Log the outputs of run_scancode as progress indication.
  https://github.com/nexB/scancode.io/issues/300

### v21.8.2

- Upgrade ScanCode-toolkit to version 21.7.30

- Add new documentation chapters and tutorials on the usage of the Web User Interface.
  https://github.com/nexB/scancode.io/issues/241

- Add ability to register custom pipelines through a new SCANCODEIO_PIPELINES_DIRS
  setting.
  https://github.com/nexB/scancode.io/issues/237

- Add a pipeline `scan_package.ScanPackage` to scan a single package archive with
  ScanCode-toolkit.
  https://github.com/nexB/scancode.io/issues/25

- Detected Package dependencies are not created as Package instance anymore but stored
  on the Package model itself in a new `dependencies` field.
  https://github.com/nexB/scancode.io/issues/228

- Add the extra_data field on the DiscoveredPackage model.
  https://github.com/nexB/scancode.io/issues/191

- Improve XLSX creation. We now check that the content is correctly added before
  calling XlsxWriter and report and error if the truncated can be truncated.
  https://github.com/nexB/scancode.io/issues/206

- Add support for VMWare Photon-based Docker images and rootfs. This is an RPM-based
  Linux distribution

### v21.6.10

- Add support for VM image formats extraction such as VMDK, VDI and QCOW.
  See https://github.com/nexB/extractcode#archive-format-kind-file_system for the full
  list of supported extensions.
  The new extraction feature requires the installation of `libguestfs-tools`,
  see https://github.com/nexB/extractcode#adding-support-for-vm-images-extraction for
  installation details.
  https://github.com/nexB/scancode.io/issues/132

- Add the ability to disable multiprocessing and threading entirely through the
  SCANCODEIO_PROCESSES setting. Use 0 to disable multiprocessing and use -1 to also
  disable threading.
  https://github.com/nexB/scancode.io/issues/185

- Missing project workspace are restored on reports (xlsx, json) creation. This allow
  to download reports even if the project workspace (input, codebase) was deleted.
  https://github.com/nexB/scancode.io/issues/154

- Add ability to search on all list views.
  https://github.com/nexB/scancode.io/issues/184

- Add the is_binary, is_text, and is_archive fields to the CodebaseResource model.
  https://github.com/nexB/scancode.io/issues/75

### v21.5.12

- Adds a new way to fetch docker images using skopeo provided as a
  plugin using docker:// reference URL-like pointers to a docker image.
  The syntax is docker://<docker image> where <docker image> is the string
  that would be used in a "docker pull <docker image>" command.
  Also rename scanpipe.pipes.fetch.download() to fetch_http()
  https://github.com/nexB/scancode.io/issues/174

- Pipeline status modals are now loaded asynchronously and available from the
  project list view.

- Fix an issue accessing codebase resource content using the scan_codebase and
  load_inventory pipelines.
  https://github.com/nexB/scancode.io/issues/147

### v21.4.28

- The installation local timezone can be configured using the TIME_ZONE setting.
  The current timezone in now included in the dates representation in the web UI.
  https://github.com/nexB/scancode.io/issues/142

- Fix pipeline failure issue related to the assignment of un-saved (not valid) packages.
  https://github.com/nexB/scancode.io/issues/162

- Add a new QUEUED status to differentiate a pipeline that is in the queue for execution
  from a pipeline execution not requested yet.
  https://github.com/nexB/scancode.io/issues/130

- Refactor the multiprocessing code for file and package scanning.
  All database related operation are now executed in the main process as forking the
  existing database connection in sub-processes is a source of issues.
  Add progress logging for scan_for_files and scan_for_application_packages pipes.
  https://github.com/nexB/scancode.io/issues/145

- Links from the charts to the resources list are now also filtered by
  in_package/not_in_package if enabled on the project details view.
  https://github.com/nexB/scancode.io/issues/124

- Add ability to filter on codebase resource detected values such as licenses,
  copyrights, holders, authors, emails, and urls.
  https://github.com/nexB/scancode.io/issues/153

- Filtered list views from a click on chart sections can now be opened in a new tab
  using ctrl/meta + click.
  https://github.com/nexB/scancode.io/issues/125

- Add links to codebase resource and to discovered packages in list views.

### v21.4.14

- Implement timeout on the scan functions, default to 120 seconds per resources.
  https://github.com/nexB/scancode.io/issues/135

- Fix issue with closing modal buttons in the web UI.
  https://github.com/nexB/scancode.io/issues/116
  https://github.com/nexB/scancode.io/issues/141

### v21.4.5

- Add support for Docker and VM images using RPMs such as Fedora, CentOS, RHEL,
  and openSUSE linux distributions.
  https://github.com/nexB/scancode.io/issues/6

- Add a compliance alert system based on license policies provided through a
  policies.yml file. The compliance alerts are computed from the license_expression and
  stored on the codebase resource. When the policy feature is enabled, the compliance
  alert values are displayed in the UI and returned in all the downloadable results.
  The enable and setup the policy feature, refer to
  https://scancodeio.readthedocs.io/en/latest/scancodeio-settings.html#scancode-io-settings
  https://github.com/nexB/scancode.io/issues/90

- Add a new codebase resource detail view including the file content.
  Detected value can be displayed as annotation in the file source.
  https://github.com/nexB/scancode.io/issues/102

- Download URLs can be provided as inputs on the project form.
  Each URL is fetched and added to the project input directory.
  https://github.com/nexB/scancode.io/issues/100

- Run celery worker with the "threads" pool implementation.
  Implement parallelization with ProcessPoolExecutor for file and package scans.
  Add a SCANCODEIO_PROCESSES settings to control the multiprocessing CPUs count.
  https://github.com/nexB/scancode.io/issues/70

- Optimize "tag" type pipes using the update() API in place of save() on the QuerySet
  iteration.
  https://github.com/nexB/scancode.io/issues/70

- Use the extractcode API for the Docker pipeline.
  This change helps with performance and results consistency between pipelines.
  https://github.com/nexB/scancode.io/issues/70

- Implement cache to prevent scanning multiple times a duplicated codebase resource.
  https://github.com/nexB/scancode.io/issues/70

- Create the virtualenv using the virtualenv.pyz app in place of the bundled "venv".
  https://github.com/nexB/scancode.io/issues/104

- Consistent ordering for the pipelines, now sorted alphabetically.

### v1.1.0 (2021-02-16)

- Display project extra data in the project details view.
  https://github.com/nexB/scancode.io/issues/88

- Add a @profile decorator for profiling pipeline step execution.
  https://github.com/nexB/scancode.io/issues/73

- Support inputs as tarballs in root_filesystem pipelines.
  The input archives are now extracted with extractcode to the codebase/ directory.
  https://github.com/nexB/scancode.io/issues/96

- Improve support for unknown distros in docker and root_filesystem pipelines.
  The pipeline logs the distro errors on the project instead of failing.
  https://github.com/nexB/scancode.io/issues/97

- Implement Pipeline registration through distribution entry points.
  Pipeline can now be installed as part of external libraries.
  With this change pipelines are no longer referenced by the
  Python script path, but by their registered name.
  This is a breaking command line API change.
  https://github.com/nexB/scancode.io/issues/91

- Add a "Run Pipeline" button in the Pipeline modal of the Project details view.
  Pipelines can now be added from the Project details view.
  https://github.com/nexB/scancode.io/issues/84

- Upgrade scancode-toolkit to version 21.2.9

- Allow to start the pipeline run immediately on addition in the `add_pipeline` action
  of the Project API endpoint.
  https://github.com/nexB/scancode.io/issues/92

- Rename the pipes.outputs module to pipes.output for consistency.

- Remove the dependency on Metaflow.
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

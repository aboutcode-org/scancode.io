Changelog
=========

v32.2.0 (2023-04-25)
--------------------

- Enhance the ``update_or_create_package`` pipe and add the ability to assign multiple
  codebase resources at once.
  https://github.com/nexB/scancode.io/issues/681

- Add new command line option to create-project and add-input management commands to
  copy the content of a local source directory to the project codebase work directory.
  https://github.com/nexB/scancode.io/pull/672

- Include the ScanCode-toolkit version in the output headers.
  https://github.com/nexB/scancode.io/pull/670

- Enhance the ``output`` management command to support providing multiple formats at
  once.
  https://github.com/nexB/scancode.io/issues/646

- Improve the resolution of CycloneDX BOM and SPDX document when the file extension is
  simply ``.json``.
  https://github.com/nexB/scancode.io/pull/688

- Add support for manifest types using ScanCode-toolkit handlers.
  https://github.com/nexB/scancode.io/issues/658

- Enhance the Resource details view to use the tabset system and display all
  available data including the content viewer.
  https://github.com/nexB/scancode.io/issues/215

- Add a "layers" data sheet in the xlsx output for docker pipeline run.
  https://github.com/nexB/scancode.io/issues/578

- Move the ``cyclonedx`` and ``spdx`` root modules into the ``pipes`` module.
  https://github.com/nexB/scancode.io/issues/657

- Remove the admin app and views.
  https://github.com/nexB/scancode.io/issues/645

- Enhance the ``resolve_about_packages`` pipe to handle filename and checksum values.

- Split the pipes unit tests into their own related submodule.

- Upgrade ScanCode Toolkit to v31.2.6
  https://github.com/nexB/scancode.io/issues/693

v32.1.0 (2023-03-23)
--------------------

- Add support for ScanCode.io results in the "load_inventory" pipeline.
  https://github.com/nexB/scancode.io/issues/609

- Add support for CycloneDX 1.4 to the "inspect-manifest" pipeline to import SBOM into
  a Project.
  https://github.com/nexB/scancode.io/issues/583

- Add fields in CycloneDX BOM output using the component properties.
  See registered properties at https://github.com/nexB/aboutcode-cyclonedx-taxonomy
  https://github.com/nexB/scancode.io/issues/637

- Upgrade to Python 3.11 in the Dockerfile.
  https://github.com/nexB/scancode.io/pull/611

- Refine the "Command Line Interface" documentation about the ``scanpipe`` command
  usages in the Docker context.
  Add the /app workdir in the "PYTHONPATH" env of the Docker file to make the
  ``scanpipe`` entry point available while running ``docker compose`` commands.
  https://github.com/nexB/scancode.io/issues/616

- Add new tutorial about the "find vulnerabilities" pipeline and the vulnerablecode
  integration in the documentation.
  https://github.com/nexB/scancode.io/issues/600

- Rewrite the CLI tutorials for a Docker-based installation.
  https://github.com/nexB/scancode.io/issues/440

- Use CodebaseResource ``path`` instead of ``id`` as slug_field in URL navigation.
  https://github.com/nexB/scancode.io/issues/242

- Remove dead code related to the project_tree view
  https://github.com/nexB/scancode.io/issues/623

- Update ``scanpipe.pipes.ProjectCodebase`` and related code to work properly
  with current Project/CodebaseResource path scheme.
  https://github.com/nexB/scancode.io/pull/624

- Add ``SCANCODEIO_PAGINATE_BY`` setting to customize the number of items displayed per
  page for each object type.
  https://github.com/nexB/scancode.io/issues/563

- Add setting for per-file timeout. The maximum time allowed for a file to be
  analyzed when scanning a codebase is configurable with SCANCODEIO_SCAN_FILE_TIMEOUT
  while the maximum time allowed for a pipeline to complete can be defined using
  SCANCODEIO_TASK_TIMEOUT.
  https://github.com/nexB/scancode.io/issues/593

v32.0.1 (2023-02-20)
--------------------

- Upgrade ScanCode-toolkit and related dependencies to solve installation issues.
  https://github.com/nexB/scancode.io/pull/586

- Add support for Python 3.11
  https://github.com/nexB/scancode.io/pull/611

- Populate ``documentDescribes`` field with Package and Dependency SPDX IDs in
  SPDX BOM output.
  https://github.com/nexB/scancode.io/issues/564

v32.0.0 (2022-11-29)
--------------------

- Add a new "find vulnerabilities" pipeline to lookup vulnerabilities in the
  VulnerableCode database for all project discovered packages.
  Vulnerability data is stored in the extra_data field of each package.
  More details about VulnerableCode at https://github.com/nexB/vulnerablecode/
  https://github.com/nexB/scancode.io/issues/101

- Add a new "inspect manifest" pipeline to resolve packages from manifest, lockfile,
  and SBOM. The resolved packages are created as discovered packages.
  Support PyPI "requirements.txt" files, SPDX document as JSON ".spdx.json",
  and AboutCode ".ABOUT" files.
  https://github.com/nexB/scancode.io/issues/284

- Generate SBOM (Software Bill of Materials) compliant with the SPDX 2.3 specification
  as a new downloadable output.
  https://github.com/nexB/scancode.io/issues/389

- Generate CycloneDX SBOM (Software Bill of Materials) as a new downloadable output.
  https://github.com/nexB/scancode.io/issues/389

- Display Webhook status in the Run modal.
  The WebhookSubscription model was refined to capture delivery data.
  https://github.com/nexB/scancode.io/issues/389

- Display the current active step of a running pipeline in the "Pipeline" section of
  the project details view, inside the run status tag.
  https://github.com/nexB/scancode.io/issues/300

- Add proper pagination for API actions: resources, packages, dependencies, and errors.

- Refine the fields ordering in API Serializers based on the toolkit order.
  https://github.com/nexB/scancode.io/issues/546

- Keep the current filters state when submitting a search in list views.
  https://github.com/nexB/scancode.io/issues/541

- Improve the performances of the project details view to load faster by deferring the
  the charts rendering. This is especially noticeable on projects with a large amount
  of codebase resources and discovered packages.
  https://github.com/nexB/scancode.io/issues/193

- Add support for filtering by "Other" values when filtering from the charts in the
  Project details view.
  https://github.com/nexB/scancode.io/issues/526

- ``CodebaseResource.for_packages`` now returns a list of
  ``DiscoveredPackage.package_uid`` or ``DiscoveredPackage.package_url`` if
  ``DiscoveredPackage.package_uid`` is not present. This is done to reflect the
  how scancode-toolkit's JSON output returns ``package_uid``s in the
  ``for_packages`` field for Resources.

- Add the model DiscoveredDependency. This represents Package dependencies
  discovered in a Project. The ``scan_codebase`` and ``scan_packages`` pipelines
  have been updated to create DiscoveredDepdendency objects. The Project API has
  been updated with new fields:

  - ``dependency_count``
    - The number of DiscoveredDependencies associated with the project.

  - ``discovered_dependencies_summary``
    - A mapping that contains following fields:

      - ``total``
        - The number of DiscoveredDependencies associated with the project.
      - ``is_runtime``
        - The number of runtime dependencies.
      - ``is_optional``
        - The number of optional dependencies.
      - ``is_resolved``
        - The number of resolved dependencies.

  These values are also available on the Project view.
  https://github.com/nexB/scancode.io/issues/447

- The ``dependencies`` field has been removed from the DiscoveredPackage model.

- Create directory CodebaseResources in the rootfs pipeline.
  https://github.com/nexB/scancode.io/issues/515

- Add ProjectErrors when the DiscoveredPackage could not be fetched using the
  provided `package_uid` during the `assemble_package` step instead of failing the whole
  pipeline.
  https://github.com/nexB/scancode.io/issues/525

- Escape paths before using them in regular expressions in ``CodebaseResource.walk()``.
  https://github.com/nexB/scancode.io/issues/525

- Disable multiprocessing and threading by default on macOS ("spawn" start method).
  https://github.com/nexB/scancode.io/issues/522

v31.0.0 (2022-08-25)
--------------------

- WARNING: Drop support for Python 3.6 and 3.7. Add support for Python 3.10.
  Upgrade Django to version 4.1 series.

- Upgrade ScanCode-toolkit to version 31.0.x.
  See https://github.com/nexB/scancode-toolkit/blob/develop/CHANGELOG.rst for an
  overview of the changes in the v31 compared to v30.

- Implement run status auto-refresh using the htmx JavaScript library.
  The statuses of queued and running pipeline are now automatically refreshed
  in the project list and project details views every 10 seconds.
  A new "toast" type of notification is displayed along the status update.
  https://github.com/nexB/scancode.io/issues/390

- Ensure the worker service waits for migrations completion before starting.
  To solve this issue we install the wait-for-it script available in
  Debian by @vishnubob and as suggested in the Docker documentation.
  In the docker-compose.yml, we let the worker wait for the web processing
  to be complete when gunicorn exposes port 8000 and web container is available.
  Reference: https://docs.docker.com/compose/startup-order/
  Reference: https://github.com/vishnubob/wait-for-it
  Reference: https://tracker.debian.org/pkg/wait-for-it
  https://github.com/nexB/scancode.io/issues/387

- Add a "create-user" management command to create new user with its API key.
  https://github.com/nexB/scancode.io/issues/458

- Add a "tag" field on the CodebaseResource model.
  The layer details are stored in this field in the "docker" pipeline.
  https://github.com/nexB/scancode.io/issues/443

- Add support for multiple inputs in the LoadInventory pipeline.
  https://github.com/nexB/scancode.io/issues/451

- Add new SCANCODEIO_REDIS_PASSWORD environment variable and setting
  to optionally set Redis instance password.

- Ensure a project cannot be deleted through the API while a pipeline is running.
  https://github.com/nexB/scancode.io/issues/402

- Display "License clarity" and "Scan summary" values as new panel in the project
  details view. The summary is generated during the `scan_package` pipeline.
  https://github.com/nexB/scancode.io/issues/411

- Enhance Project list view page:

  - 20 projects are now displayed per page
  - Creation date displayed under the project name
  - Add ability to sort by date and name
  - Add ability to filter by pipeline type
  - Add ability to filter by run status

  https://github.com/nexB/scancode.io/issues/413

- Correctly extract symlinks in docker images. We now use the latest
  container-inspector to fix symlinks extraction in docker image tarballs.
  In particular broken symlinks are not treated as an error anymore
  and symlinks are extracted correctly.
  https://github.com/nexB/scancode.io/issues/471
  https://github.com/nexB/scancode.io/issues/407

- Add a Package details view including all model fields and resources.
  Display only 5 resources per package in the list view.
  https://github.com/nexB/scancode.io/issues/164
  https://github.com/nexB/scancode.io/issues/464

- Add the ability to filter by empty and none values providing the
  "EMPTY" magic value to any filters.
  https://github.com/nexB/scancode.io/issues/296

- CodebaseResource.name now contains both the bare file name with extension, as
  opposed to just the bare file name without extension.
  Using a name stripped from its extension was something that was not used in
  other AboutCode project or tools.
  https://github.com/nexB/scancode.io/issues/467

- Export current results as XLSX for resource, packages, and errors list views.
  https://github.com/nexB/scancode.io/issues/48

- Add support for .tgz extension for input files in Docker pipeline
  https://github.com/nexB/scancode.io/issues/499

- Add support for resource missing file content in details view.
  Refine the annotation using the new className instead of type.
  https://github.com/nexB/scancode.io/issues/495

- Change the worksheet names in XLSX output, using the
  "PACKAGES", "RESOURCES", "DEPENDENCIES", and "ERRORS" names.
  https://github.com/nexB/scancode.io/issues/511

- Update application Package scanning step to reflect the updates in
  scancode-toolkit package scanning.

  - Package data detected from a file are now stored on the
    CodebaseResource.package_data field.
  - A second processing step is now done after scanning for Package data, where
    Package Resources are determined and DiscoveredPackages and
    DiscoveredDependencies are created.

  https://github.com/nexB/scancode.io/issues/444

v30.2.0 (2021-12-17)
--------------------

- Add authentication for the Web UI views and REST API endpoint.
  The autentication is disabled by default and can be enabled using the
  SCANCODEIO_REQUIRE_AUTHENTICATION settings.
  When enabled, users have to authenticate through a login form in the Web UI, or using
  their API Key in the REST API.
  The API Key can be viewed in the Web UI "Profile settings" view ince logged-in.
  Users can be created using the Django "createsuperuser" management command.
  https://github.com/nexB/scancode.io/issues/359

- Include project errors in XLSX results output.
  https://github.com/nexB/scancode.io/issues/364

- Add input_sources used to fetch inputs to JSON results output.
  https://github.com/nexB/scancode.io/issues/351

- Refactor the update_or_create_package pipe to support the ProjectError system
  and fix a database transaction error.
  https://github.com/nexB/scancode.io/issues/381

- Add webhook subscription available when creating project from REST API.
  https://github.com/nexB/scancode.io/issues/98

- Add the project "reset" feature in the UI, CLI, and REST API.
  https://github.com/nexB/scancode.io/issues/375

- Add a new GitHub action that build the docker-compose images and run the test suite.
  This ensure that the app is properly working and tested when running with Docker.
  https://github.com/nexB/scancode.io/issues/367

- Add --no-install-recommends in the Dockerfile apt-get install and add the
  `linux-image-amd64` package. This packages makes available the kernels
  required by extractcode and libguestfs for proper VM images extraction.
  https://github.com/nexB/scancode.io/issues/367

- Add a new `list-project` CLI command to list projects.
  https://github.com/nexB/scancode.io/issues/365

v30.1.1 (2021-11-23)
--------------------

- Remove the --no-install-recommends in the Dockerfile apt-get install to include
  required dependencies for proper VM extraction.
  https://github.com/nexB/scancode.io/issues/367

v30.1.0 (2021-11-22)
--------------------

- Synchronize QUEUED and RUNNING pipeline runs with their related worker jobs during
  worker maintenance tasks scheduled every 10 minutes.
  If a container was taken down while a pipeline was running, or if pipeline process
  was killed unexpectedly, that pipeline run status will be updated to a FAILED state
  during the next maintenance tasks.
  QUEUED pipeline will be restored in the queue as the worker redis cache backend data
  is now persistent and reloaded on starting the image.
  Note that internaly, a running job emits a "heartbeat" every 60 seconds to let all the
  workers know that it is properly running.
  After 90 seconds without any heartbeats, a worker will determine that the job is not
  active anymore and that job will be moved to the failed registry during the worker
  maintenance tasks. The pipeline run will be updated as well to reflect this failure
  in the Web UI, the REST API, and the command line interface.
  https://github.com/nexB/scancode.io/issues/130

- Enable redis data persistence using the "Append Only File" with the default policy of
  fsync every second in the docker-compose.
  https://github.com/nexB/scancode.io/issues/130

- Add a new tutorial chapter about license policies and compliance alerts.
  https://github.com/nexB/scancode.io/issues/337

- Include layers in docker image data.
  https://github.com/nexB/scancode.io/issues/175

- Fix a server error on resource details view when the compliance alert is "missing".
  https://github.com/nexB/scancode.io/issues/344

- Migrate the ScanCodebase pipeline from `scancode.run_scancode` subprocess to
  `scancode.scan_for_application_packages` and `scancode.scan_for_files`.
  https://github.com/nexB/scancode.io/issues/340

v30.0.1 (2021-10-11)
--------------------

- Fix a build failure related to dependency conflict.
  https://github.com/nexB/scancode.io/issues/342

v30.0.0 (2021-10-8)
-------------------

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

v21.9.6
-------

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

v21.8.2
-------

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

v21.6.10
--------

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

v21.5.12
--------

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

v21.4.28
--------

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

v21.4.14
--------

- Implement timeout on the scan functions, default to 120 seconds per resources.
  https://github.com/nexB/scancode.io/issues/135

- Fix issue with closing modal buttons in the web UI.
  https://github.com/nexB/scancode.io/issues/116
  https://github.com/nexB/scancode.io/issues/141

v21.4.5
-------

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

v1.1.0 (2021-02-16)
-------------------

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

v1.0.7 (2021-02-01)
-------------------

- Add user interface to manage Projects from a web browser
  All the command-line features are available
  https://github.com/nexB/scancode.io/issues/24

- Log messages from Pipeline execution on a new Run instance `log` field
  https://github.com/nexB/scancode.io/issues/66

- Add support for scancode pipes and Project name with whitespaces

- Add a profile() method on the Run model for profiling pipeline execution
  https://github.com/nexB/scancode.io/issues/73

v1.0.6 (2020-12-23)
-------------------

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

v1.0.5 (2020-12-07)
-------------------

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

v1.0.4 (2020-11-17)
-------------------

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

v1.0.3 (2020-09-24)
-------------------

- Add ability to resume a failed pipeline from the run management command
  Fix for https://github.com/nexB/scancode.io/issues/22

- Use project name as argument to run a pipeline
  Fix for https://github.com/nexB/scancode.io/issues/18

- Add support for "failed" task_output in Run.get_run_id method
  Fix for https://github.com/nexB/scancode.io/issues/17

v1.0.2 (2020-09-18)
-------------------

- Add documentation and tutorial
  For https://github.com/nexB/scancode.io/issues/8

- Add a create-project, add-input, add-pipeline, run, output
  management commands to expose ScanPipe features through the command line
  Fix for https://github.com/nexB/scancode.io/issues/13

- Always return the Pipeline subclass/implementation from the module inspection
  Fix for https://github.com/nexB/scancode.io/issues/11

v1.0.1 (2020-09-12)
-------------------

- Do not fail when collecting system packages in Ubuntu docker images for
  layers that do not install packages by updating to a newer version of
  ScanCode Toolkit
  Fix for https://github.com/nexB/scancode.io/issues/1

v1.0.0 (2020-09-09)
-------------------

- Initial release

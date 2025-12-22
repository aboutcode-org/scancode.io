.. _command_line_interface:

Command Line Interface
======================

The ``scanpipe`` command can be executed using the Docker Compose command line interface.

If the Docker Compose stack is already running, you can execute the command as follows:

.. code-block:: shell

    docker compose exec -it web scanpipe COMMAND

If the ScanCode.io services are not currently running, you can use the following command:

.. code-block:: shell

    docker compose run --rm web scanpipe COMMAND

Additionally, you can start a new Docker container and execute multiple
``scanpipe`` commands within a ``bash`` session:

.. code-block:: shell

    docker compose run web bash
    scanpipe COMMAND
    scanpipe COMMAND
    ...

.. warning::
    In order to add local input files to a project using the Command Line Interface,
    extra arguments need to be passed to the ``docker compose`` command.

    For instance ``--volume /path/on/host:/target/path/in/container:ro``
    will mount and make available the host path inside the container (``:ro`` stands
    for read only).

    .. code-block:: bash

        docker compose run --volume /home/sources:/sources:ro \
            web scanpipe create-project my_project --input-file="/sources/image.tar"

.. note::
    In a local development installation, the ``scanpipe`` command is directly
    available as an entry point in your virtualenv and is located at
    ``<scancode.io_root_dir>/bin/scanpipe``.

`$ scanpipe --help`
-------------------

Lists all sub-commands available, including Django built-in commands.
ScanPipe's own commands are listed under the ``[scanpipe]`` section::

    $ scanpipe --help
    ...
    [scanpipe]
      add-input
      add-pipeline
      add-webhook
      analyze-kubernetes
      archive-project
      batch-create
      check-compliance
      create-project
      create-user
      delete-project
      execute
      flush-projects
      list-pipelines
      list-project
      output
      purldb-scan-worker
      report
      reset-project
      run
      show-pipeline
      status


`$ scanpipe <subcommand> --help`
--------------------------------

Displays help for the provided sub-command.

For example::

    $ scanpipe create-project --help
    usage: scanpipe create-project [--input-file INPUTS_FILES]
        [--input-url INPUT_URLS] [--copy-codebase SOURCE_DIRECTORY]
        [--pipeline PIPELINES] [--label LABELS] [--notes NOTES]
        [--execute] [--async]
        name

    Create a ScanPipe project.

    positional arguments:
      name                  Project name.


`$ scanpipe create-project <name>`
----------------------------------

Creates a ScanPipe project using ``<name>`` as a Project name. The project name
must be unique.

Optional arguments:

- ``--pipeline PIPELINES`` Pipelines names to add on the project.

.. warning::
    Pipelines are added and are executed in order.

.. tip::
    Use the "pipeline_name:option1,option2" syntax to select optional steps:

    ``--pipeline map_deploy_to_develop:Java,JavaScript``

- ``--input-file INPUTS_FILES`` Input file locations to copy in the :guilabel:`input/`
  work directory.

  .. tip::
    Use the "filename:tag" syntax to **tag** input files:
    ``--input-file path/filename:tag``

- ``--input-url INPUT_URLS`` Input URLs to download in the :guilabel:`input/` work
  directory.

  .. tip::
    Use the "url#tag" syntax to tag downloaded files:
    ``--input-url https://url.com/filename#tag``

- ``--copy-codebase SOURCE_DIRECTORY`` Copy the content of the provided source directory
  into the :guilabel:`codebase/` work directory.

- ``--notes NOTES`` Optional notes about the project.

- ``--label LABELS`` Optional labels for the project.

- ``--execute`` Execute the pipelines right after project creation.

- ``--async`` Add the pipeline run to the tasks queue for execution by a worker instead
  of running in the current thread.
  Applies only when ``--execute`` is provided.

- ``--no-global-webhook`` Skip the creation of the global webhook. This option is
  only useful if a global webhook is defined in the settings.


.. _cli_batch_create:

`$ scanpipe batch-create [--input-directory INPUT_DIRECTORY] [--input-list FILENAME.csv]`
-----------------------------------------------------------------------------------------

Processes files from the specified ``INPUT_DIRECTORY`` or rows from ``FILENAME.csv``,
creating a project for each file or row.

- Use ``--input-directory`` to specify a local directory. Each file in the directory
  will result in a project, uniquely named using the filename and a timestamp.

- Use ``--input-list`` to specify a ``FILENAME.csv``. Each row in the CSV will be used
  to create a project based on the data provided.

Supports specifying pipelines and asynchronous execution.

Required arguments (one of):

- ``input-directory`` The path to the directory containing the input files to process.
  Ensure the directory exists and contains the files you want to use.

- ``input-list`` Path to a CSV file with project names and input URLs.
  The first column must contain project names, and the second column should list
  comma-separated input URLs (e.g., Download URL, PURL, or Docker reference).

  **CSV content example**:

  +----------------+---------------------------------+
  | project_name   | input_urls                      |
  +================+=================================+
  | project-1      | https://url.com/file.ext        |
  +----------------+---------------------------------+
  | project-2      | pkg:deb/debian/curl@7.50.3      |
  +----------------+---------------------------------+

.. tip::
    In place of a local path, a download URL to the CSV file is supported for the
    ``--input-list`` argument.

Optional arguments:

- ``--project-name-suffix`` Optional custom suffix to append to project names.
  If not provided, a timestamp (in the format [YYMMDD_HHMMSS]) will be used.

- ``--pipeline PIPELINES`` Pipelines names to add on the project.

- ``--notes NOTES`` Optional notes about the project.

- ``--label LABELS`` Optional labels for the project.

- ``--execute`` Execute the pipelines right after project creation.

- ``--async`` Add the pipeline run to the tasks queue for execution by a worker instead
  of running in the current thread.
  Applies only when ``--execute`` is provided.

- ``--create-global-webhook`` Create the global webhook for each project, if enabled in
  the settings. If not provided, the global webhook subscriptions are not created.

Example: Processing Multiple Docker Images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose you have multiple Docker images stored in a directory named ``local-data/`` on
the host machine.
To process these images using the ``analyze_docker_image`` pipeline with asynchronous
execution, you can use this command::

    $ docker compose run --rm \
        --volume local-data/:/input-data/:ro \
        web scanpipe batch-create
            --input-directory /input-data/ \
            --pipeline analyze_docker_image \
            --label "Docker" \
            --execute --async

**Explanation**:

- ``local-data/``: A directory on the host machine containing the Docker images to
  process.
- ``/input-data/``: The directory inside the container where ``local-data/`` is
  mounted (read-only).
- ``--pipeline analyze_docker_image``: Specifies the ``analyze_docker_image``
  pipeline for processing each Docker image.
- ``--label "Docker"``: Tagging all the projects with the "Docker" label to enable
  easy search and filtering.
- ``--execute``: Runs the pipeline immediately after creating a project for each
  image.
- ``--async``: Adds the pipeline run to the worker queue for asynchronous execution.

Each Docker image in the ``local-data/`` directory will result in the creation of a
project with the specified pipeline (``analyze_docker_image``) executed by worker
services.

Example: Processing Multiple Develop to Deploy Mapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To process an input list CSV file with the ``map_deploy_to_develop`` pipeline using
asynchronous execution::

    $ docker compose run --rm \
        web scanpipe batch-create \
            --input-list https://url/input_list.csv \
            --pipeline map_deploy_to_develop \
            --label "d2d_mapping" \
            --execute --async

`$ scanpipe list-pipeline [--verbosity {0,1,2,3}]`
--------------------------------------------------

Displays a list of available pipelines.
Use ``--verbosity=2`` to include details of each pipeline's steps."

Optional arguments:

- ``--verbosity {0,1,2}`` Verbosity level.


`$ scanpipe list-project [--search SEARCH] [--include-archived]`
----------------------------------------------------------------

Lists ScanPipe projects.

Optional arguments:

- ``--search SEARCH`` Limit the projects list to this search results.

- ``--include-archived`` Include archived projects.

.. tip::
    Only the project names are listed by default. You can display more details
    about each project by providing the ``--verbosity 2`` or ``--verbosity 3``
    options.


`$ scanpipe add-input --project PROJECT [--input-file FILES] [--input-url URLS]`
--------------------------------------------------------------------------------

Adds input files in the project's work directory.

- ``--input-file INPUTS_FILES`` Input file locations to copy in the :guilabel:`input/`
  work directory.

  .. tip::
    Use the "filename:tag" syntax to **tag** input files:
    ``--input-file path/filename:tag``

- ``--input-url INPUT_URLS`` Input URLs to download in the :guilabel:`input/` work
  directory.

  .. tip::
    Use the "url#tag" syntax to tag downloaded files:
    ``--input-url https://url.com/filename#tag``

- ``--copy-codebase SOURCE_DIRECTORY`` Copy the content of the provided source directory
  into the :guilabel:`codebase/` work directory.

For example, assuming you have created beforehand a project named "foo", this will
copy ``~/docker/alpine-base.tar`` to the foo project :guilabel:`input/` directory::

    $ scanpipe add-input --project foo --input-file ~/docker/alpine-base.tar

.. warning::
    Make sure to mount your local sources volume in the Docker setup:

    ``--volume /host/sources:/sources:ro --input-file /sources/image.tar``

You can also provide URLs of files to be downloaded to the foo project
:guilabel:`input/` directory::

    $ scanpipe add-input --project foo --input-url https://github.com/aboutcode-org/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar

.. note:: Docker images can be provided as input using their Docker reference
    with the ``docker://docker-reference`` syntax. For example::

    $ [...] --input-url docker://redis
    $ [...] --input-url docker://postgres:13
    $ [...] --input-url docker://docker.elastic.co/elasticsearch/elasticsearch-oss:7.10.2

    See https://docs.docker.com/engine/reference/builder/ for more details about
    references.

.. note:: Git repositories are supported as input using their Git clone URL in the
    ``https://<host>[:<port>]/<path-to-git-repo>.git`` syntax. For example::

    $ [...] --input-url https://github.com/aboutcode-org/scancode.io.git


`$ scanpipe add-pipeline --project PROJECT PIPELINE_NAME [PIPELINE_NAME ...]`
-----------------------------------------------------------------------------

Adds the ``PIPELINE_NAME`` to a given ``PROJECT``.
You can use more than one ``PIPELINE_NAME`` to add multiple pipelines at once.

.. warning::
    Pipelines are added and are executed in order.

For example, assuming you have created beforehand a project named "foo", this will
add the docker pipeline to your project::

    $ scanpipe add-pipeline --project foo analyze_docker_image

.. tip::
    Use the "pipeline_name:option1,option2" syntax to select optional steps:

    ``--pipeline map_deploy_to_develop:Java,JavaScript``


.. _cli_add_webhook:

`$ scanpipe add-webhook --project PROJECT TARGET_URL`
-----------------------------------------------------

Adds a webhook subscription to a project.

Required arguments:

- ``target-url``
  The target URL to which the webhook should send POST requests.

Optional arguments:

- ``--trigger-on-each-run``
  Trigger the webhook after each individual pipeline run.

- ``--include-summary``
  Include summary data in the payload.

- ``--include-results``
  Include results data in the payload.

- ``--inactive``
  Create the webhook but set it as inactive.

Example usage:

1. Add an active webhook that triggers after each pipeline run::

   $ scanpipe add-webhook my_project https://example.com/webhook --trigger-on-each-run

2. Add a webhook that includes summary and results data::

   $ scanpipe add-webhook my_project https://example.com/webhook --include-summary --include-results

3. Add an inactive webhook::

   $ scanpipe add-webhook my_project https://example.com/webhook --inactive


.. _cli_analyze_kubernetes:

`$ scanpipe analyze-kubernetes <name>`
--------------------------------------

Analyzes all Docker images from a Kubernetes cluster by extracting image references
using ``kubectl`` and creating projects to scan them.

This command connects to your Kubernetes cluster, retrieves all container images
(including init containers) from running pods, and creates projects to analyze each
image for packages, dependencies, and optionally vulnerabilities.

Required arguments:

- ``name`` Project name or prefix for the created projects.

Optional arguments:

- ``--multi`` Create multiple projects (one per image) instead of a single project
  containing all images. When used, each project is named ``<name>: <image-reference>``.

- ``--find-vulnerabilities`` Run the ``find_vulnerabilities`` pipeline during the
  analysis to detect known security vulnerabilities in discovered packages.

- ``--execute`` Execute the pipelines right after project creation.

- ``--async`` Add the pipeline run to the tasks queue for execution by a worker instead
  of running in the current thread.
  Applies only when ``--execute`` is provided.

- ``--namespace NAMESPACE`` Limit the image extraction to a specific Kubernetes
  namespace. If not provided, images from all namespaces are collected.

- ``--context CONTEXT`` Use a specific Kubernetes context. If not provided, the
  current context is used.

- ``--notes NOTES`` Optional notes about the project(s).

- ``--label LABELS`` Optional labels for the project(s). Multiple labels can be
  provided by using this argument multiple times.

- ``--dry-run`` Do not create any projects; just print the images and projects that
  would be created.

- ``--no-global-webhook`` Skip the creation of the global webhook. This option is
  only useful if a global webhook is defined in the settings.

.. note::
    This command requires ``kubectl`` to be installed and configured with access to
    your Kubernetes cluster.

Example: Analyze All Cluster Images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To analyze all images from all namespaces in your current Kubernetes cluster::

    $ scanpipe analyze-kubernetes cluster-audit --multi --execute

This creates separate projects for each unique image found in the cluster.

Example: Analyze Production Namespace with Vulnerability Scanning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To scan all images in the ``production`` namespace and check for vulnerabilities::

    $ scanpipe analyze-kubernetes prod-security-scan \
        --namespace production \
        --find-vulnerabilities \
        --multi \
        --label "production" \
        --label "security-audit" \
        --execute

Example: Dry Run Before Creating Projects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To preview which images would be analyzed without creating any projects::

    $ scanpipe analyze-kubernetes cluster-preview \
        --namespace default \
        --dry-run

This displays all images that would be scanned, allowing you to verify the scope
before running the actual analysis.

Example: Analyze Specific Cluster Context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To analyze images from a specific Kubernetes cluster when you have multiple contexts
configured::

    $ scanpipe analyze-kubernetes staging-audit \
        --context staging-cluster \
        --namespace default \
        --multi \
        --execute --async

Example: Single Project for All Images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To create one project containing all images from the cluster::

    $ scanpipe analyze-kubernetes full-cluster-scan \
        --find-vulnerabilities \
        --execute

This creates a single project named ``full-cluster-scan`` that analyzes all discovered
images together.

.. tip::
    Use ``--multi`` when analyzing large clusters to create separate projects per image,
    making it easier to track and review results for individual container images.

`$ scanpipe execute --project PROJECT`
--------------------------------------

Executes the next pipeline of the ``PROJECT`` project queue.

Optional arguments:

- ``--async`` Add the pipeline run to the tasks queue for execution by a worker instead
  of running in the current thread.


`$ scanpipe show-pipeline --project PROJECT`
--------------------------------------------

Lists all the pipelines added to the ``PROJECT`` project.


`$ scanpipe status --project PROJECT`
-------------------------------------

Displays status information about the ``PROJECT`` project.

.. note::
    The full logs of each pipeline execution are displayed by default.
    This can be disabled providing the ``--verbosity 0`` option.


.. _cli_output:

`$ scanpipe output --project PROJECT --format {json,csv,xlsx,spdx,cyclonedx,attribution,...}`
---------------------------------------------------------------------------------------------

Outputs the ``PROJECT`` results as JSON, XLSX, CSV, SPDX, CycloneDX,
ORT package-list.yml, and Attribution.
The output files are created in the ``PROJECT`` :guilabel:`output/` directory.

Multiple formats can be provided at once::

    $ scanpipe output --project foo --format json xlsx spdx cyclonedx attribution

Optional arguments:

- ``--print`` Print the output to stdout instead of creating a file. This is not
  compatible with the XLSX and CSV formats.
  It cannot be used when multiple formats are provided.

Refer to :ref:`Mount projects workspace <mount_projects_workspace_volume>` to access
your outputs on the host machine when running with Docker.

.. tip:: To specify a CycloneDX spec version (default to latest), use the syntax
  ``cyclonedx:VERSION`` as format value. For example: ``--format cyclonedx:1.5``.


.. _cli_report:

`$ scanpipe report --model MODEL`
---------------------------------

Generates an XLSX report of selected projects based on the provided criteria.

Required arguments:

- ``--model {package,dependency,resource,relation,message,todo}``
  Specifies the model to include in the XLSX report. Available choices are based on
  predefined object types.

Optional arguments:

- ``--output-directory OUTPUT_DIRECTORY``
  The path to the directory where the report file will be created. If not provided,
  the report file will be created in the current working directory.

- ``--search SEARCH``
  Filter projects by searching for the provided string in their name.

- ``--label LABELS``
  Filter projects by the provided label(s). Multiple labels can be provided by using
  this argument multiple times.

.. note::
    Either ``--label`` or ``--search`` must be provided to select projects.

Example usage:

1. Generate a report for all projects tagged with "d2d" and include the **TODOS**
worksheet::

   $ scanpipe report --model todo --label d2d

2. Generate a report for projects whose names contain the word "audit" and include the
**PACKAGES** worksheet::

   $ scanpipe report --model package --search audit


.. _cli_check_compliance:

`$ scanpipe check-compliance --project PROJECT`
-----------------------------------------------

Check for compliance issues in Project.
Exit with a non-zero status if compliance issues are present in the project.
The compliance alert indicates how the license expression complies with provided
policies.

Optional arguments:

- ``--fail-level {ERROR,WARNING,MISSING}`` Compliance alert level that will cause the
  command to exit with a non-zero status. Default is ERROR.

- ``--fail-on-vulnerabilities`` Exit with a non-zero status if known vulnerabilities
  are detected in discovered packages and dependencies.
  Requires the ``find_vulnerabilities`` pipeline to be executed beforehand.

`$ scanpipe archive-project --project PROJECT`
----------------------------------------------

Archives a project and remove selected work directories.

Optional arguments:

- ``--remove-input`` Remove the :guilabel:`input/` directory.
- ``--remove-codebase`` Remove the :guilabel:`codebase/` directory.
- ``--remove-output`` Remove the :guilabel:`output/` directory.
- ``--no-input`` Does not prompt the user for input of any kind.


.. _cli_reset_project:

`$ scanpipe reset-project --project PROJECT`
--------------------------------------------

Resets a project removing all database entries and all data on disks except for
the :guilabel:`input/` directory.

Optional arguments:

- ``--remove-input`` Remove the :guilabel:`input/` directory and input sources when
  resetting the project.
- ``--remove-webhook`` Remove webhook subscriptions when resetting the project.
- ``--restore-pipelines`` Restore all pipelines that were previously existing on the
  project.
- ``--execute-now`` Execute the restored pipelines immediately after restoration.
  Applies only when ``--restore-pipelines`` is provided.
- ``--no-input`` Does not prompt the user for input of any kind.

Example usage:

1. Reset a project while preserving input files and webhooks (default behavior)::

   $ scanpipe reset-project --project foo

2. Reset a project and remove all data including input files::

   $ scanpipe reset-project --project foo --remove-input

3. Reset a project and restore its original pipelines for re-execution::

   $ scanpipe reset-project --project foo --restore-pipelines --execute-now


.. _cli_delete_project:

`$ scanpipe delete-project --project PROJECT`
---------------------------------------------

Deletes a project and its related work directories.

Optional arguments:

- ``--no-input`` Does not prompt the user for input of any kind.


.. _cli_flush_projects:

`$ scanpipe flush-projects`
---------------------------

Delete all project data and their related work directories created more than a
specified number of days ago.

Optional arguments:

- ``---retain-days RETAIN_DAYS`` Specify the number of days to retain data.
  All data older than this number of days will be deleted.
  **Defaults to 0 (delete all data)**.

  For example, to delete all projects created more than one week ago::

    scanpipe flush-projects --retain-days 7

- ``--dry-run`` Do not delete any projects; just print the ones that would be flushed.

- ``--label LABELS`` Filter projects by the provided label.
  Multiple labels can be provided by using this argument multiple times.

- ``--pipeline PIPELINES`` Filter projects by the provided pipeline name.
  Multiple pipeline name can be provided by using this argument multiple times.

- ``--no-input`` Does not prompt the user for input of any kind.


.. _cli_create_user:

`$ scanpipe create-user <username>`
-----------------------------------

.. note:: This command is to be used when ScanCode.io's authentication system
  :ref:`scancodeio_settings_require_authentication` is enabled.

Creates a user and generates an API key for authentication.

You will be prompted for a password. After you enter one, the user will be created
immediately.

The API key for the new user account will be displayed on the terminal output.

.. code-block:: console

    User <username> created with API key: abcdef123456

The API key can also be retrieved from the :guilabel:`Profile settings` menu in the UI.

.. warning::
    Your API key is like a password and should be treated with the same care.

By default, this command will prompt for a password for the new user account.
When run non-interactively with the ``--no-input`` option, no password will be set,
and the user account will only be able to authenticate with the REST API using its
API key.

Optional arguments:

- ``--no-input`` Does not prompt the user for input of any kind.
- ``--admin`` Specifies that the user should be created as an admin user.
- ``--super`` Specifies that the user should be created as a superuser.


.. _cli_run:

`$ run PIPELINE_NAME [PIPELINE_NAME ...] input_location`
--------------------------------------------------------

A ``run`` command is available for executing pipelines and printing the results
without providing any configuration. This can be useful for running a pipeline to get
the results without the need to persist the data in the database or access the UI to
review the results.

.. tip:: You can run multiple pipelines by providing their names, space-separated,
  such as `pipeline1 pipeline2`.

Optional arguments:

- ``--project PROJECT_NAME``: Provide a project name; otherwise, a random value is
  generated.
- ``--format {json,spdx,cyclonedx,attribution}``: Specify the output format.
  **The default format is JSON**.

For example, running the ``inspect_packages`` pipeline on a manifest file:

.. code-block:: bash

    $ run inspect_packages path/to/package.json > results.json

.. tip:: Use the "pipeline_name:option1,option2" syntax to select optional steps::

    $ run inspect_packages:StaticResolver package.json > results.json

In the following example, running the ``scan_codebase`` followed by the
``find_vulnerabilities`` pipelines on a codebase directory:

.. code-block:: bash

    $ run scan_codebase find_vulnerabilities path/to/codebase/ > results.json

Using a URL as input is also supported:

.. code-block:: bash

    $ run scan_single_package https://url.com/package.zip > results.json
    $ run analyze_docker_image docker://postgres:16 > results.json

In the last example, the ``--format`` option is used to generate a CycloneDX SBOM
instead of the default JSON output.

.. code-block:: bash

    $ run scan_codebase codebase/ --format cyclonedx > bom.json

See the :ref:`cli_output` for more information about supported output formats.

`$ scanpipe verify-project --project PROJECT`
---------------------------------------------

Verifies the analysis results of a project against expected package and dependency
counts.
This command is designed to ensure that a project's scan results meet specific
expectations — for example, that a minimum number of packages or dependencies were
discovered, or that vulnerability counts match expected baselines.

Optional arguments:

- ``--packages`` Expected number of discovered packages.

- ``--vulnerable-packages`` Expected number of vulnerable packages.

- ``--dependencies`` Expected number of discovered dependencies.

- ``--vulnerable-dependencies`` Expected number of vulnerable dependencies.

- ``--vulnerabilities`` Expected number of unique vulnerabilities.
  Combines vulnerabilities from both packages and dependencies.

- ``--strict`` Assert on strict count equality instead of minimum threshold.
  When not provided, the command checks that actual counts are at least the expected
  values (greater than or equal). With ``--strict``, actual counts must match expected
  values exactly.

By default, the command verifies that actual counts meet or exceed the expected values.
Only the metrics explicitly provided via command-line arguments are validated.

If any expectations are not met, the command exits with a non-zero status and prints
a summary of all issues found.

Example usage:

1. Verify minimum thresholds (default behavior)::

   $ scanpipe verify-project --project my_project --packages 100 --dependencies 50

2. Verify exact counts with strict mode::

   $ scanpipe verify-project --project my_project --vulnerabilities 14 --strict

3. Verify only specific metrics::

   $ scanpipe verify-project --project my_project --vulnerable-packages 5

.. tip::
    This command is particularly useful for **CI/CD pipelines** that need to validate
    SBOM or vulnerability scan results against known baselines. Use non-strict mode
    to ensure minimum quality thresholds, or strict mode to detect unexpected changes
    in scan results.

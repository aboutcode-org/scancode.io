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
        archive-project
        create-project
        delete-project
        execute
        list-project
        output
        show-pipeline
        status


`$ scanpipe <subcommand> --help`
--------------------------------

Displays help for the provided sub-command.

For example::

    $ scanpipe create-project --help
    usage: scanpipe create-project [--input-file INPUTS_FILES]
        [--input-url INPUT_URLS] [--copy-codebase SOURCE_DIRECTORY]
        [--pipeline PIPELINES] [--execute] [--async]
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

.. tip::
    Use the "pipeline_name:group1,group2" syntax to select steps groups:

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

- ``--execute`` Execute the pipelines right after project creation.

- ``--async`` Add the pipeline run to the tasks queue for execution by a worker instead
  of running in the current thread.
  Applies only when ``--execute`` is provided.

.. warning::
    Pipelines are added and are executed in order.


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

    $ scanpipe add-input --project foo --input-url https://github.com/nexB/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar

.. note:: Docker images can be provided as input using their Docker reference
    with the ``docker://docker-reference`` syntax. For example::

    $ [...] --input-url docker://redis
    $ [...] --input-url docker://postgres:13
    $ [...] --input-url docker://docker.elastic.co/elasticsearch/elasticsearch-oss:7.10.2

    See https://docs.docker.com/engine/reference/builder/ for more details about
    references.

.. note:: Git repositories are supported as input using their Git clone URL in the
    ``https://<host>[:<port>]/<path-to-git-repo>.git`` syntax. For example::

    $ [...] --input-url https://github.com/nexB/scancode.io.git


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
    Use the "pipeline_name:group1,group2" syntax to select steps groups:

    ``--pipeline map_deploy_to_develop:Java,JavaScript``


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

`$ scanpipe output --project PROJECT --format {json,csv,xlsx,spdx,cyclonedx,attribution}`
-----------------------------------------------------------------------------------------

Outputs the ``PROJECT`` results as JSON, XLSX, CSV, SPDX, CycloneDX, and Attribution.
The output files are created in the ``PROJECT`` :guilabel:`output/` directory.

Multiple formats can be provided at once::

    $ scanpipe output --project foo --format json xlsx spdx cyclonedx attribution

Optional arguments:

- ``--print`` Print the output to stdout instead of creating a file. This is not
  compatible with the XLSX and CSV formats.
  It cannot be used when multiple formats are provided.

Refer to :ref:`Mount projects workspace <mount_projects_workspace_volume>` to access
your outputs on the host machine when running with Docker.

`$ scanpipe archive-project --project PROJECT`
----------------------------------------------

Archives a project and remove selected work directories.

Optional arguments:

- ``--remove-input`` Remove the :guilabel:`input/` directory.
- ``--remove-codebase`` Remove the :guilabel:`codebase/` directory.
- ``--remove-output`` Remove the :guilabel:`output/` directory.
- ``--no-input`` Does not prompt the user for input of any kind.


`$ scanpipe reset-project --project PROJECT`
--------------------------------------------

Resets a project removing all database entrie and all data on disks except for
the input/ directory.

Optional arguments:

- ``--no-input`` Does not prompt the user for input of any kind.


`$ scanpipe delete-project --project PROJECT`
---------------------------------------------

Deletes a project and its related work directories.

Optional arguments:

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

.. _cli_run:

`$ run PIPELINE_NAME INPUT_LOCATION`
------------------------------------

A ``run`` command is available for executing pipelines and printing the results
without providing any configuration. This can be useful for running a pipeline to get
the results without the need to persist the data in the database or access the UI to
review the results.

.. tip:: You can run multiple pipelines by providing their names, comma-separated,
  such as `pipeline1,pipeline2`.

Optional arguments:

- ``--project PROJECT_NAME``: Provide a project name; otherwise, a random value is
  generated.
- ``--format {json,spdx,cyclonedx,attribution}``: Specify the output format.
  **The default format is JSON**.

For example, running the ``inspect_packages`` pipeline on a manifest file:

.. code-block:: bash

    $ run inspect_packages path/to/package.json > results.json

In the following example, running the ``scan_codebase`` followed by the
``find_vulnerabilities`` pipelines on a codebase directory:

.. code-block:: bash

    $ run scan_codebase,find_vulnerabilities path/to/codebase/ > results.json

Using a URL as input is also supported:

.. code-block:: bash

    $ run scan_single_package https://url.com/package.zip > results.json
    $ run analyze_docker_image docker://postgres:16 > results.json

In the last example, the ``--format`` option is used to generate a CycloneDX SBOM
instead of the default JSON output.

.. code-block:: bash

    $ run scan_codebase codebase/ --format cyclonedx > bom.json

See the :ref:`cli_output` for more information about supported output formats.

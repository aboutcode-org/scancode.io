.. _command_line_interface:

Command Line Interface
======================

A ``scanpipe`` command can be executed through the ``docker compose`` command line
interface with::

    docker compose exec -it web scanpipe COMMAND

Alternatively, you can start a ``bash`` session in a new Docker container to execute
multiple ``scanpipe`` commands::

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
        graph
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

- ``--input-file INPUTS_FILES`` Input file locations to copy in the :guilabel:`input/`
  work directory.

- ``--input-url INPUT_URLS`` Input URLs to download in the :guilabel:`input/` work
  directory.

- ``--copy-codebase SOURCE_DIRECTORY`` Copy the content of the provided source directory
  into the :guilabel:`codebase/` work directory.

- ``--execute`` Execute the pipelines right after project creation.

- ``--async`` Add the pipeline run to the tasks queue for execution by a worker instead
  of running in the current thread.
  Applies only when --execute is provided.

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

- ``--input-url INPUT_URLS`` Input URLs to download in the :guilabel:`input/` work
  directory.

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


`$ scanpipe add-pipeline --project PROJECT PIPELINE_NAME [PIPELINE_NAME ...]`
-----------------------------------------------------------------------------

Adds the ``PIPELINE_NAME`` to a given ``PROJECT``.
You can use more than one ``PIPELINE_NAME`` to add multiple pipelines at once.

.. warning::
    Pipelines are added and are executed in order.

For example, assuming you have created beforehand a project named "foo", this will
add the docker pipeline to your project::

    $ scanpipe add-pipeline --project foo docker


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


`$ scanpipe output --project PROJECT --format {json,csv,xlsx,spdx,cyclonedx}`
-----------------------------------------------------------------------------

Outputs the ``PROJECT`` results as JSON, XLSX, CSV, SPDX, and CycloneDX.
The output files are created in the ``PROJECT`` :guilabel:`output/` directory.

Multiple formats can be provided at once::

    $ scanpipe output --project foo --format json xlsx spdx cyclonedx

Optional arguments:

- ``--print`` Print the output to stdout instead of creating a file. This is not
  compatible with the XLSX and CSV formats.
  It cannot be used when multiple formats are provided.

`$ scanpipe graph [PIPELINE_NAME ...]`
--------------------------------------

Generates one or more pipeline graph image as PNG using
`Graphviz <https://graphviz.org/>`_.
The output images are named using the pipeline name with a ``.png`` extension.

Optional arguments:

- ``--list`` Displays a list of all available pipelines.

- ``--output OUTPUT`` Specifies the directory to which the output is written.

.. note::
    By default, output files are created in the current working directory.


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

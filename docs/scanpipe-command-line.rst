.. _scanpipe_command_line:

Management Commands
===================

The main entry point is the :guilabel:`scanpipe` command which is available
directly when you are in the activated virtualenv or at this path:
``<scancode.io_root_dir>/bin/scanpipe``


`$ scanpipe --help`
-------------------

List all the sub-commands available (including Django built-in commands).
ScanPipe's own commands are listed under the ``[scanpipe]`` section::

    $ scanpipe --help
    ...
    [scanpipe]
        add-input
        add-pipeline
        create-project
        graph
        output
        execute
        show-pipeline


`$ scanpipe <subcommand> --help`
--------------------------------

Display help for the provided subcommand.

For example::

    $ scanpipe create-project --help
    usage: scanpipe create-project [--input-file INPUTS_FILES]
        [--input-url INPUT_URLS] [--pipeline PIPELINES] [--execute] name

    Create a ScanPipe project.

    positional arguments:
      name                  Project name.


`$ scanpipe create-project <name>`
----------------------------------

Create a ScanPipe project using ``<name>`` as a Project name. The name must
be unique.

Optional arguments:

- ``--pipeline PIPELINES`` Pipelines names to add on the project.

- ``--input-file INPUTS_FILES`` Input file locations to copy in the :guilabel:`input/`
  work directory.

- ``--input-url INPUT_URLS`` Input URLs to download in the :guilabel:`input/` work
  directory.

- ``--execute`` Execute the pipelines right after project creation.

.. warning::
    The pipelines are added and will be executed in the order of the provided options.


`$ scanpipe add-input --project PROJECT [--input-file FILES] [--input-url URLS]`
--------------------------------------------------------------------------------

Add input files in a project work directory.

- ``--input-file INPUTS_FILES`` Input file locations to copy in the :guilabel:`input/`
  work directory.

- ``--input-url INPUT_URLS`` Input URLs to download in the :guilabel:`input/` work
  directory.

For example, assuming you have created beforehand a project named "foo", this will
copy ``~/docker/alpine-base.tar`` to the foo project :guilabel:`input/` directory::

    $ scanpipe add-input --project foo --input-file ~/docker/alpine-base.tar

You can also provide URLs of files to be downloaded to foo project :guilabel:`input/`
directory::

    $ scanpipe add-input --project foo --input-url https://github.com/nexB/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar

.. note:: Docker images can be provided as input using their Docker reference with the
  ``docker://docker-reference`` syntax. For example::

    $ [...] --input-url docker://redis
    $ [...] --input-url docker://postgres:13
    $ [...] --input-url docker://docker.elastic.co/elasticsearch/elasticsearch-oss:7.10.2

See https://docs.docker.com/engine/reference/builder/ for more details about references.


`$ scanpipe add-pipeline --project PROJECT PIPELINE_NAME [PIPELINE_NAME ...]`
-----------------------------------------------------------------------------

Add the ``PIPELINE_NAME`` to the provided ``PROJECT``.
You can use more than one ``PIPELINE_NAME`` to add multiple pipelines at once.

.. warning::
    The pipelines are added and will be executed in the order of the provided options.

For example, assuming you have created beforehand a project named "foo", this will
add the docker pipeline to your project::

    $ scanpipe add-pipeline --project foo docker


`$ scanpipe execute --project PROJECT`
--------------------------------------

Execute the next pipeline of the project named ``PROJECT`` queue.


`$ scanpipe show-pipeline --project PROJECT`
--------------------------------------------

List all the pipelines added of the project named ``PROJECT``.


`$ scanpipe status --project PROJECT`
-------------------------------------

Display status information about the provided ``PROJECT``.

.. note::
    The full logs of each pipeline execution are displayed by default.
    This can be disabled providing the ``--verbosity 0`` option.


`$ scanpipe output --project PROJECT --format {json,csv,xlsx}`
--------------------------------------------------------------

Output the ``PROJECT`` results as JSON, CSV or XLSX.
The output files are created in the ``PROJECT`` :guilabel:`output/` directory.


`$ scanpipe graph [PIPELINE_NAME ...]`
--------------------------------------

Generate one or more pipeline graph image as PNG
(using `Graphviz <https://graphviz.org/>`_).
The output files are named using the pipeline name with a ``.png`` extension.

Optional arguments:

- ``--list`` Display a list of all available pipelines.

- ``--output OUTPUT`` Specifies directory to which the output is written.

.. note::
    By default, the output files are created in the current working directory.


`$ scanpipe delete-project --project PROJECT`
---------------------------------------------

Delete a project and its related work directory.

Optional arguments:

- ``--no-input`` Do not prompt the user for input of any kind.
